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
  warn ".env missing — copy .env.example or create one. Required keys: OPEN_ROUTE_SERVICE_API_KEY"
  warn "                continuing anyway; routing will fall back to OSRM."
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
section "Seeding VectorAI DB"
# ---------------------------------------------------------------------------
# Skip the expensive ingest if the collection is already populated. This
# keeps re-running install.sh cheap (~5s) instead of re-embedding 50K
# rows on every iteration during dev.
if "$VENV_PY" scripts/vdb_count.py --min 1000 >/dev/null 2>&1; then
  EXISTING="$("$VENV_PY" scripts/vdb_count.py)"
  info "VDB already populated ($EXISTING points) — skipping reseed. Delete the docker volume to force a re-ingest."
else
  info "Seeding ~500 synthetic anchor crashes (covers demo corridors even with no real data)..."
  "$VENV_PY" scripts/seed_synthetic.py --n 500

  CRASH_FILES="$(ls data/raw/crash*.json 2>/dev/null | wc -l | tr -d ' ')"
  if [ "$CRASH_FILES" -gt 0 ]; then
    info "Seeding $CRASH_FILES FDOT crash chunks (~50K rows; ~3-5 min on first run)..."
    "$VENV_PY" scripts/ingest_fdot_crash.py
  else
    warn "no data/raw/crash*.json files found — skipping FDOT ingest."
    warn "fetch them with: bash data/raw/fetch_crashes.sh"
  fi

  FINAL="$("$VENV_PY" scripts/vdb_count.py)"
  info "VDB now contains $FINAL points."
fi

# ---------------------------------------------------------------------------
section "Done"
# ---------------------------------------------------------------------------
echo "Run ./start.sh to bring everything up."
