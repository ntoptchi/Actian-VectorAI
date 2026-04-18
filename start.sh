#!/usr/bin/env bash
# Start all four RigSense services:
#   1. Actian VectorAI DB  (docker, detached)
#   2. Backend API         (uvicorn, localhost:8000)
#   3. Feed replay         (uvicorn, localhost:8100)
#   4. Dashboard           (vite,    localhost:5173)
#
# Press Ctrl-C to stop everything cleanly.
#
# Flags:
#   --no-bootstrap    Skip the collection bootstrap / re-seed step.
#   --keep-db         Don't stop the VectorAI container on exit.
#   --no-feed         Skip the live-feed replay server.
#
# Usage:  ./start.sh [--no-bootstrap] [--keep-db] [--no-feed]

set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"

BOOTSTRAP=1
KEEP_DB=0
START_FEED=1
for arg in "$@"; do
    case "$arg" in
        --no-bootstrap) BOOTSTRAP=0 ;;
        --keep-db)      KEEP_DB=1 ;;
        --no-feed)      START_FEED=0 ;;
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
FEED_PID=""
DASH_PID=""

cleanup() {
    log "Shutting down"
    [ -n "$DASH_PID"    ] && kill "$DASH_PID"    2>/dev/null || true
    [ -n "$FEED_PID"    ] && kill "$FEED_PID"    2>/dev/null || true
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
    if [ "$KEEP_DB" -eq 0 ]; then
        (cd "$ROOT/vectorai-db-beta" && docker compose down) || true
    else
        echo "  VectorAI container left running (--keep-db)."
    fi
}
trap cleanup EXIT INT TERM

wait_for_http() {
    # wait_for_http <url> <label> <timeout_s>
    local url="$1"; local label="$2"; local timeout="${3:-30}"
    for i in $(seq 1 "$timeout"); do
        if "$VENV_PY" - <<PY 2>/dev/null
import sys, urllib.request
try:
    with urllib.request.urlopen("$url", timeout=1.0) as r:
        sys.exit(0 if r.status < 500 else 1)
except Exception:
    sys.exit(1)
PY
        then
            echo "  $label up after ${i}s"
            return 0
        fi
        sleep 1
    done
    die "$label did not come up at $url within ${timeout}s"
}

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
    log "Bootstrapping collections and seed data (source=pump)"
    (cd "$ROOT/backend" && "$VENV_PY" scripts/bootstrap.py --source=pump)
else
    echo "  (skipping bootstrap, --no-bootstrap)"
fi

log "Starting backend API on http://localhost:8000"
(cd "$ROOT/backend" && "$VENV_PY" -m uvicorn backend.server:app \
    --host 0.0.0.0 --port 8000 --log-level info) &
BACKEND_PID=$!

wait_for_http "http://localhost:8000/health" "Backend" 30

if [ "$START_FEED" -eq 1 ]; then
    log "Installing feed dependencies (one-shot)"
    (cd "$ROOT/feed" && "$VENV_PY" -m pip install --quiet -r requirements.txt)

    log "Starting live feed on http://localhost:8100"
    (cd "$ROOT/feed" && "$VENV_PY" -m uvicorn feed.server:app \
        --host 0.0.0.0 --port 8100 --log-level info) &
    FEED_PID=$!

    wait_for_http "http://localhost:8100/health" "Feed" 20
fi

log "Starting dashboard on http://localhost:5173"
npm run dev -- --host 0.0.0.0 &
DASH_PID=$!

log "All services up. Ctrl-C to stop."
echo "    VectorAI DB : localhost:50051"
echo "    Backend API : http://localhost:8000  (docs at /docs)"
if [ "$START_FEED" -eq 1 ]; then
    echo "    Feed Replay : http://localhost:8100  (/status)"
fi
echo "    Dashboard   : http://localhost:5173"

if [ "$START_FEED" -eq 1 ]; then
    wait "$BACKEND_PID" "$FEED_PID" "$DASH_PID"
else
    wait "$BACKEND_PID" "$DASH_PID"
fi
