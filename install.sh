#!/usr/bin/env bash
# RouteWise install script (bash / Git Bash / WSL / macOS / Linux).
#
# Goal: a fresh `git pull` + `cp .env.example .env` + `./install.sh` should
# leave the user able to run `./start.sh` and hit a fully populated trip
# planner. Idempotent — re-run any time, expensive steps are skipped if
# already done.
set -euo pipefail

cd "$(dirname "$0")"

section() { printf "\n\033[36m=== %s ===\033[0m\n" "$1"; }
info()    { printf "\033[2m[install] %s\033[0m\n" "$1"; }
warn()    { printf "\033[33m[install] %s\033[0m\n" "$1"; }
die()     { printf "\033[31m[install] %s\033[0m\n" "$1" >&2; exit 1; }

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "missing dependency: $1 — $2"
  fi
}

# ---------------------------------------------------------------------------
section "Checking prerequisites"
# ---------------------------------------------------------------------------
need python  "Install Python 3.11+ (https://www.python.org/downloads/)"
need docker  "Install Docker Desktop (https://www.docker.com/products/docker-desktop/)"
need node    "Install Node.js 20+ (https://nodejs.org/)"
need npm     "Comes with Node.js"

if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    info "created .env from .env.example (placeholder ORS key)."
    info "  edit .env and drop in a real OPEN_ROUTE_SERVICE_API_KEY for"
    info "  multi-alternate routing — without it the backend falls back"
    info "  to OSRM single-route and you only see one route option."
  else
    warn ".env missing and no .env.example to copy from. Routing will fall back to OSRM."
  fi
fi

# ---------------------------------------------------------------------------
section "Python venv (.venv)"
# ---------------------------------------------------------------------------
if [ ! -d ".venv" ]; then
  python -m venv .venv
  info "created .venv"
else
  info ".venv already exists"
fi

# Pick the right venv python depending on platform (Windows uses Scripts/, *nix bin/).
if [ -x ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
else
  VENV_PY=".venv/bin/python"
fi

"$VENV_PY" -m pip install --upgrade pip wheel >/dev/null
"$VENV_PY" -m pip install -r requirements.txt

# ---------------------------------------------------------------------------
section "Actian VectorAI DB python client"
# ---------------------------------------------------------------------------
WHEEL="$(ls vectorai-db-beta/actian_vectorai-*.whl 2>/dev/null | head -n1 || true)"
if [ -n "$WHEEL" ]; then
  "$VENV_PY" -m pip install --upgrade "$WHEEL"
else
  die "no actian_vectorai wheel found in vectorai-db-beta/ — the VDB client is required."
fi

# ---------------------------------------------------------------------------
section "Embedding model (all-MiniLM-L6-v2)"
# ---------------------------------------------------------------------------
"$VENV_PY" scripts/download_model.py

# ---------------------------------------------------------------------------
section "Frontend (routewise/)"
# ---------------------------------------------------------------------------
( cd routewise && npm install )

# Frontend env: the only required value is BACKEND_URL, which already has
# a sane default in src/env.js. Still drop a .env file so Next stops
# warning about missing env on first boot.
if [ ! -f "routewise/.env" ]; then
  cp routewise/.env.example routewise/.env
  info "created routewise/.env from .env.example"
fi

# ---------------------------------------------------------------------------
section "Pulling Actian VectorAI DB Docker image"
# ---------------------------------------------------------------------------
docker pull williamimoh/actian-vectorai-db:latest >/dev/null
info "image ready"

# ---------------------------------------------------------------------------
section "Booting Actian VectorAI DB (one-time, for seeding)"
# ---------------------------------------------------------------------------
# We need the container running to seed it. Bring it up here, leave it up
# afterwards — start.sh will reuse the same container (compose up -d is a
# no-op if it's already running).
docker compose -f vectorai-db-beta/docker-compose.yml up -d
"$VENV_PY" scripts/wait_vdb.py --timeout 90 \
  || die "VectorAI DB never came up. Check 'docker compose -f vectorai-db-beta/docker-compose.yml logs'."

# ---------------------------------------------------------------------------
section "Building processed data tables"
# ---------------------------------------------------------------------------
# These are tiny (<1s each) and feed the segment / hotspot scoring logic.
mkdir -p data/processed
"$VENV_PY" scripts/build_baselines.py     || warn "build_baselines failed — non-fatal, falls back to a constant FL average."
"$VENV_PY" scripts/load_aadt_table.py     || warn "load_aadt_table failed — non-fatal, AADT shapefile spatial join still works."
"$VENV_PY" scripts/load_night_segments.py || warn "load_night_segments failed — non-fatal, night-skew tag will be off."

# ---------------------------------------------------------------------------
section "Fetching FDOT crash chunks (if missing)"
# ---------------------------------------------------------------------------
# data/raw/crash{1000..150000}.json is committed to git, but a thin clone
# (sparse-checkout, partial clone, or anyone trimming the ~213 MB raw/
# tree to keep their fork small) won't have them. Auto-pull whatever's
# missing from the FDOT ArcGIS REST API. Existing files are skipped, so
# this is cheap on a normal full clone (a couple of seconds).
EXPECTED_CHUNKS=150
HAVE_CHUNKS="$(ls data/raw/crash*.json 2>/dev/null | wc -l | tr -d ' ')"
if [ "${HAVE_CHUNKS:-0}" -lt "$EXPECTED_CHUNKS" ]; then
  info "have $HAVE_CHUNKS / $EXPECTED_CHUNKS FDOT crash chunks — fetching the rest from FDOT (~213 MB total, ~5-10 min on a fresh box)."
  "$VENV_PY" scripts/fetch_fdot_crashes.py --start 1 --end "$EXPECTED_CHUNKS" \
    || warn "FDOT fetch returned non-zero — some chunks may be missing. Re-run install.sh to retry."
else
  info "all $HAVE_CHUNKS FDOT crash chunks already present."
fi

# ---------------------------------------------------------------------------
section "Seeding VectorAI DB"
# ---------------------------------------------------------------------------
# We track ingestion freshness with a marker file. If it's missing — or
# the collection has fewer points than a healthy ingest produces — we
# re-run the ingester. The marker also forces a re-ingest after fixes
# to backend/ingest/normalize.py (e.g. the midnight-bug fix that drops
# rows with missing CRASH_TIME) so teammates aren't stuck on stale data.
#
# Bump INGEST_VERSION when normalize.py / situation_doc.py change in a
# way that would alter what gets indexed.
INGEST_VERSION="2"
INGEST_MARKER="data/processed/.fdot_ingest_v${INGEST_VERSION}"

# Threshold matches "all 150 chunks ingested cleanly" (140K crashes
# survive after dropping ~6% with missing CRASH_TIME). Anything below
# this means the corpus is incomplete and the trip planner will under-
# count crashes on most routes.
HEALTHY_MIN=100000

if [ -f "$INGEST_MARKER" ] \
   && "$VENV_PY" scripts/vdb_count.py --min "$HEALTHY_MIN" >/dev/null 2>&1; then
  EXISTING="$("$VENV_PY" scripts/vdb_count.py)"
  info "VDB already populated ($EXISTING points, ingest v${INGEST_VERSION}) — skipping reseed."
  info "  to force a fresh ingest: rm $INGEST_MARKER  (and re-run install.sh)"
else
  if [ -f "$INGEST_MARKER" ]; then
    info "marker present but VDB has fewer than $HEALTHY_MIN points — re-running ingest."
  else
    info "no v${INGEST_VERSION} ingest marker — running fresh ingest."
  fi

  info "Seeding ~500 synthetic anchor crashes (keeps demo corridors warm even if real data is sparse)..."
  "$VENV_PY" scripts/seed_synthetic.py --n 500

  CRASH_FILES="$(ls data/raw/crash*.json 2>/dev/null | wc -l | tr -d ' ')"
  if [ "$CRASH_FILES" -gt 0 ]; then
    info "Ingesting $CRASH_FILES FDOT crash chunks (~140K rows; ~5-10 min on first run, mostly embedding)..."
    "$VENV_PY" scripts/ingest_fdot_crash.py
    mkdir -p data/processed
    : > "$INGEST_MARKER"
    info "wrote ingest marker $INGEST_MARKER"
  else
    warn "no data/raw/crash*.json files found — skipping FDOT ingest. Re-run install.sh once the FDOT fetch step succeeds."
  fi

  FINAL="$("$VENV_PY" scripts/vdb_count.py)"
  info "VDB now contains $FINAL points."
fi

# ---------------------------------------------------------------------------
section "Done"
# ---------------------------------------------------------------------------
cat <<'EOF'
Install complete. Next:

  ./start.sh              # boots VDB (docker), backend (:8080), frontend (:3000)

Notes for first run:
  * The backend warms an in-memory crash cache (~140K rows) on startup.
    It runs on a daemon thread so the API binds immediately, but the
    very first /trip/brief after boot will block ~30 s if you hit it
    before the cache finishes loading. start.sh waits for the warm-up
    before opening the frontend, so you usually won't notice.
  * The trip planner needs an OPEN_ROUTE_SERVICE_API_KEY in .env to
    return alternate routes. Without it you only see one route.
EOF
