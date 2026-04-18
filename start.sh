#!/usr/bin/env bash
# Start all three RigSense services:
#   1. Actian VectorAI DB  (docker, detached)
#   2. Backend API         (uvicorn, localhost:8000)
#   3. Dashboard           (vite, localhost:5173)
#
# Press Ctrl-C to stop everything cleanly (backend + vite killed, docker
# container stopped via `docker compose down`).
#
# Flags:
#   --no-bootstrap    Skip the collection bootstrap / re-seed step.
#   --keep-db         Don't stop the VectorAI container on exit.
#
# Usage:  ./start.sh [--no-bootstrap] [--keep-db]

set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"

BOOTSTRAP=1
KEEP_DB=0
for arg in "$@"; do
    case "$arg" in
        --no-bootstrap) BOOTSTRAP=0 ;;
        --keep-db)      KEEP_DB=1 ;;
        *)              printf 'Unknown flag: %s\n' "$arg" >&2; exit 2 ;;
    esac
done

log() { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }
die() { printf '\n\033[1;31m!!\033[0m %s\n' "$*" >&2; exit 1; }

[ -d "$ROOT/backend/.venv" ] || die "backend/.venv missing. Run ./install.sh first."
[ -d "$ROOT/node_modules"  ] || die "node_modules missing. Run ./install.sh first."

if [ -x "$ROOT/backend/.venv/Scripts/python.exe" ]; then
    VENV_PY="$ROOT/backend/.venv/Scripts/python.exe"
else
    VENV_PY="$ROOT/backend/.venv/bin/python"
fi

BACKEND_PID=""
DASH_PID=""

cleanup() {
    log "Shutting down"
    [ -n "$DASH_PID"    ] && kill "$DASH_PID"    2>/dev/null || true
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
    if [ "$KEEP_DB" -eq 0 ]; then
        (cd "$ROOT/vectorai-db-beta" && docker compose down) || true
    else
        echo "  VectorAI container left running (--keep-db)."
    fi
}
trap cleanup EXIT INT TERM

log "Starting Actian VectorAI DB"
(cd "$ROOT/vectorai-db-beta" && docker compose up -d)

log "Waiting for VectorAI DB on localhost:50051"
for i in $(seq 1 40); do
    if "$VENV_PY" - <<'PY' 2>/dev/null
import socket, sys
s = socket.socket()
s.settimeout(1.0)
try:
    s.connect(("localhost", 50051))
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
    then
        echo "  up after ${i}s"
        break
    fi
    sleep 1
    if [ "$i" -eq 40 ]; then
        die "VectorAI DB did not come up on :50051 within 40s"
    fi
done

if [ "$BOOTSTRAP" -eq 1 ]; then
    log "Bootstrapping collections and seed data"
    (cd "$ROOT/backend" && "$VENV_PY" scripts/bootstrap.py)
else
    echo "  (skipping bootstrap, --no-bootstrap)"
fi

log "Starting backend API on http://localhost:8000"
(cd "$ROOT/backend" && "$VENV_PY" -m uvicorn backend.server:app \
    --host 0.0.0.0 --port 8000 --log-level info) &
BACKEND_PID=$!

log "Starting dashboard on http://localhost:5173"
npm run dev -- --host 0.0.0.0 &
DASH_PID=$!

log "All services up. Ctrl-C to stop."
echo "    VectorAI DB : localhost:50051"
echo "    Backend API : http://localhost:8000  (docs at /docs)"
echo "    Dashboard   : http://localhost:5173"

wait "$BACKEND_PID" "$DASH_PID"
