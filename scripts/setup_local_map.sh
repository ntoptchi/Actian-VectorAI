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

PBF_URL="https://download.geofabrik.de/north-america/us/florida-latest.osm.pbf"
PBF_FILE="florida-latest.osm.pbf"

OSRM_IMAGE="ghcr.io/project-osrm/osrm-backend"
OSRM_PLATFORM="--platform linux/amd64"

mkdir -p "$OSRM_DATA" "$TILES_DATA"

# ── 1. Download Florida OSM extract ─────────────────────────────────

if [ -f "$OSRM_DATA/$PBF_FILE" ]; then
  echo "✓ Florida PBF already downloaded."
else
  echo "↓ Downloading Florida OSM extract (~300 MB)..."
  curl -L --progress-bar -o "$OSRM_DATA/$PBF_FILE" "$PBF_URL"
  echo "✓ Download complete."
fi

# ── 2. OSRM preprocessing (extract → partition → customize) ─────────

OSRM_BASE="florida-latest.osrm"
if [ -f "$OSRM_DATA/$OSRM_BASE" ]; then
  echo "✓ OSRM data already preprocessed."
else
  echo "⚙ OSRM extract (this takes a few minutes)..."
  docker run --rm -t $OSRM_PLATFORM -v "$OSRM_DATA:/data" "$OSRM_IMAGE" \
    osrm-extract -p /opt/car.lua "/data/$PBF_FILE"

  echo "⚙ OSRM partition..."
  docker run --rm -t $OSRM_PLATFORM -v "$OSRM_DATA:/data" "$OSRM_IMAGE" \
    osrm-partition "/data/$OSRM_BASE"

  echo "⚙ OSRM customize..."
  docker run --rm -t $OSRM_PLATFORM -v "$OSRM_DATA:/data" "$OSRM_IMAGE" \
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
  echo "↓ Extracting Florida region from Protomaps planet tiles..."

  # Ensure pmtiles is on PATH (may be in ~/bin from manual install)
  export PATH="$HOME/bin:$PATH"

  if ! command -v pmtiles &>/dev/null; then
    echo ""
    echo "  The pmtiles CLI is required. Install it:"
    echo "    • Download from https://github.com/protomaps/go-pmtiles/releases"
    echo "    • Place the binary in ~/bin/ or /usr/local/bin/"
    echo "  Then re-run this script."
    exit 1
  fi

  # Use yesterday's build (today's may not be ready yet)
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
