#!/usr/bin/env bash
# RouteWise start script.
#
# Boots: Actian VectorAI DB (docker), FastAPI backend (:8000), Next.js dev
# server (:3000). Ctrl-C cleanly stops the backend; the VDB container is
# left running so the next start is instant.
set -euo pipefail

cd "$(dirname "$0")"

section() { printf "\n\033[36m=== %s ===\033[0m\n" "$1"; }
info()    { printf "\033[2m[start] %s\033[0m\n" "$1"; }
warn()    { printf "\033[33m[start] %s\033[0m\n" "$1"; }
die()     { printf "\033[31m[start] %s\033[0m\n" "$1" >&2; exit 1; }

# Pick the right venv python depending on platform.
if [ -x ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
  VENV_PY=".venv/bin/python"
else
  die ".venv missing — run ./install.sh first."
fi

# ---------------------------------------------------------------------------
section "Starting Actian VectorAI DB"
# ---------------------------------------------------------------------------
docker compose -f vectorai-db-beta/docker-compose.yml up -d
"$VENV_PY" scripts/wait_vdb.py --timeout 60 \
  || die "VectorAI DB never came up. Check 'docker compose -f vectorai-db-beta/docker-compose.yml logs'."

# Sanity check: warn loudly if the collection is empty. Most "the trip
# page is broken" reports trace back to nobody having run install.sh.
COUNT="$("$VENV_PY" scripts/vdb_count.py 2>/dev/null || echo 0)"
if [ "${COUNT:-0}" -lt 100 ]; then
  warn "VDB is empty (only $COUNT points). The frontend will load but every"
  warn "      hotspot/segment will read as zero risk. Run ./install.sh to seed."
else
  info "VDB has $COUNT crash records."
fi

# ---------------------------------------------------------------------------
section "Starting FastAPI backend on :8000"
# ---------------------------------------------------------------------------
BACKEND_PID=""
cleanup() {
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    info "stopping backend (pid $BACKEND_PID)"
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

[ -f "backend/main.py" ] || die "backend/main.py not found"
"$VENV_PY" -m uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!
info "backend pid=$BACKEND_PID"

# Give uvicorn a moment to bind so the frontend doesn't error on its
# first server-side fetch during page render.
sleep 2

# ---------------------------------------------------------------------------
section "Starting frontend (routewise/) on :3000"
# ---------------------------------------------------------------------------
( cd routewise && npm run dev )
