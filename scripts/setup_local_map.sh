#!/usr/bin/env bash
#
# One-time setup for the fully-local map stack.
#
# Downloads the Florida OSM extract, preprocesses OSRM routing data,
# and generates MBTiles for the local tile server. After this script
# completes, run `docker compose up` from the project root to start
# VectorAI DB + OSRM + tileserver-gl.
#
# Requirements: Docker, curl, ~2 GB free disk, ~10 min on first run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

OSRM_DATA="$PROJECT_ROOT/osrm-data"
TILES_DATA="$PROJECT_ROOT/tiles-data"
BIN_DIR="$PROJECT_ROOT/.bin"

PBF_URL="https://download.geofabrik.de/north-america/us/florida-latest.osm.pbf"
PBF_FILE="florida-latest.osm.pbf"

OSRM_IMAGE="ghcr.io/project-osrm/osrm-backend"
OSRM_PLATFORM="--platform linux/amd64"

# Pinned so re-runs are reproducible. Bump when upstream releases a
# fix we care about; any 1.x release speaks the same CLI surface.
PMTILES_VERSION="1.22.3"

# ── Git Bash / MSYS path-mangling control ───────────────────────────
# Under Git Bash on Windows, MSYS auto-rewrites any argument that
# looks like a unix absolute path (anything starting with /) into a
# Windows path by prefixing Git's install dir. That turns
#   osrm-extract -p /opt/car.lua
# into
#   osrm-extract -p 'C:/Program Files/Git/opt/car.lua'
# which OSRM (running inside the linux container) can't resolve, and
# the install bails out with:
#   "the argument ('C:/Program Files/Git/opt/car.lua') for option
#   '--profile' is invalid".
#
# We want conversion OFF for the `docker run` lines (so /opt/car.lua
# and /data/... reach the container verbatim) but ON everywhere else
# — Windows curl/tar/unzip need the normal /tmp → C:/Program Files/Git/tmp
# rewrite or they can't find the mktemp dir. So we scope the opt-out
# per-docker-invocation via the `docker_run` wrapper below instead of
# exporting the vars globally. On macOS/Linux these env vars are
# inert, so the wrapper is a straight passthrough there.
docker_run() {
  MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker run "$@"
}

mkdir -p "$OSRM_DATA" "$TILES_DATA" "$BIN_DIR"

# Repo-local bin is first on PATH so our managed pmtiles beats any
# system install (which may be stale or wrong arch under WSL/Rosetta).
export PATH="$BIN_DIR:$PATH"

# ── Ensure the pmtiles CLI is available ─────────────────────────────
#
# go-pmtiles ships static binaries for every platform we support
# (Darwin/Linux/Windows × x86_64/arm64). We download the right archive
# into $BIN_DIR on first run. Kept inside this script so install.sh
# can drive the whole local-map setup with a single invocation — no
# out-of-band "go download this binary" step in the README.

install_pmtiles_cli() {
  local exe="pmtiles"
  local archive_ext="tar.gz"
  local os_name arch_name

  case "$(uname -s)" in
    Darwin)                     os_name="Darwin" ;;
    Linux)                      os_name="Linux" ;;
    MINGW*|MSYS*|CYGWIN*)
      os_name="Windows"
      exe="pmtiles.exe"
      archive_ext="zip"
      ;;
    *)
      echo "  Unsupported OS $(uname -s) for automatic pmtiles install." >&2
      echo "  Install manually from https://github.com/protomaps/go-pmtiles/releases and re-run." >&2
      exit 1
      ;;
  esac

  case "$(uname -m)" in
    x86_64|amd64)    arch_name="x86_64" ;;
    arm64|aarch64)   arch_name="arm64" ;;
    *)
      echo "  Unsupported arch $(uname -m) for automatic pmtiles install." >&2
      exit 1
      ;;
  esac

  if [ -x "$BIN_DIR/$exe" ]; then
    return 0
  fi

  local archive="go-pmtiles_${PMTILES_VERSION}_${os_name}_${arch_name}.${archive_ext}"
  local url="https://github.com/protomaps/go-pmtiles/releases/download/v${PMTILES_VERSION}/${archive}"
  local tmpdir
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' RETURN

  echo "↓ Installing pmtiles CLI ${PMTILES_VERSION} (${os_name}/${arch_name}) → $BIN_DIR/$exe"
  curl -fL --progress-bar -o "$tmpdir/$archive" "$url" \
    || { echo "  pmtiles download failed: $url" >&2; exit 1; }

  if [ "$archive_ext" = "zip" ]; then
    if command -v unzip >/dev/null 2>&1; then
      unzip -q "$tmpdir/$archive" -d "$tmpdir"
    else
      # Git Bash ships without unzip; Python is guaranteed by install.sh.
      python3 -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" \
        "$tmpdir/$archive" "$tmpdir"
    fi
  else
    tar -xzf "$tmpdir/$archive" -C "$tmpdir"
  fi

  if [ ! -f "$tmpdir/$exe" ]; then
    echo "  pmtiles binary not found in archive ($archive)." >&2
    exit 1
  fi
  mv "$tmpdir/$exe" "$BIN_DIR/$exe"
  chmod +x "$BIN_DIR/$exe" 2>/dev/null || true
  echo "✓ pmtiles CLI installed."
}

# ── 1. Download Florida OSM extract ─────────────────────────────────

if [ -f "$OSRM_DATA/$PBF_FILE" ]; then
  echo "✓ Florida PBF already downloaded."
else
  echo "↓ Downloading Florida OSM extract (~300 MB)..."
  curl -L --progress-bar -o "$OSRM_DATA/$PBF_FILE" "$PBF_URL"
  echo "✓ Download complete."
fi

# ── 2. OSRM preprocessing (extract → partition → customize) ─────────
#
# OSRM's "data" is a *basename* (florida-latest.osrm) with a sidecar
# file for each stage — .ebg / .geometry / .nbg_nodes from extract,
# .partition / .cells from partition, .cell_metrics / .mldgr from
# customize. There is no bare `florida-latest.osrm` file, so we use
# `.cell_metrics` as the sentinel — it's only written once customize
# finishes, so its presence means *all three* stages ran to completion.

OSRM_BASE="florida-latest.osrm"
OSRM_SENTINEL="$OSRM_DATA/$OSRM_BASE.cell_metrics"
if [ -s "$OSRM_SENTINEL" ]; then
  echo "✓ OSRM data already preprocessed."
else
  echo "⚙ OSRM extract (this takes a few minutes)..."
  docker_run --rm -t $OSRM_PLATFORM -v "$OSRM_DATA:/data" "$OSRM_IMAGE" \
    osrm-extract -p /opt/car.lua "/data/$PBF_FILE"

  echo "⚙ OSRM partition..."
  docker_run --rm -t $OSRM_PLATFORM -v "$OSRM_DATA:/data" "$OSRM_IMAGE" \
    osrm-partition "/data/$OSRM_BASE"

  echo "⚙ OSRM customize..."
  docker_run --rm -t $OSRM_PLATFORM -v "$OSRM_DATA:/data" "$OSRM_IMAGE" \
    osrm-customize "/data/$OSRM_BASE"

  echo "✓ OSRM preprocessing complete."

  # PBF is no longer needed — OSRM only reads the .osrm index files.
  rm -f "$OSRM_DATA/$PBF_FILE"
  echo "✓ Cleaned up source PBF to save disk space."
fi

# ── 3. Download PMTiles for local map rendering ──────────────────────

PMTILES_FILE="$TILES_DATA/florida.pmtiles"
if [ -f "$PMTILES_FILE" ]; then
  echo "✓ PMTiles already downloaded."
else
  install_pmtiles_cli

  echo "↓ Extracting Florida region from Protomaps planet tiles (~2-3 min, ~100 MB)..."

  # Protomaps publishes a dated snapshot every day. Today's build may
  # not exist yet (build runs ~midnight UTC), so step back one day.
  BUILD_DATE=$(date -v-1d +%Y%m%d 2>/dev/null || date -d "yesterday" +%Y%m%d)
  pmtiles extract \
    "https://build.protomaps.com/${BUILD_DATE}.pmtiles" \
    "$PMTILES_FILE" \
    --bbox="-87.63,24.39,-79.97,31.10"

  echo "✓ PMTiles download complete."
fi

# ── Done ─────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════════"
echo "  Local map stack is ready!"
echo ""
echo "  OSRM data:   $OSRM_DATA"
echo "  PMTiles:     $PMTILES_FILE"
echo ""
echo "  Start Docker services with:"
echo "    cd $PROJECT_ROOT && docker compose up -d"
echo ""
echo "  Services:"
echo "    VectorAI DB   → localhost:50051"
echo "    OSRM Router   → localhost:5000"
echo ""
echo "  Map tiles are served as a static PMTiles file by"
echo "  the FastAPI backend — no separate tile server needed."
echo "════════════════════════════════════════════════════════"
