#!/usr/bin/env bash
# RouteWise start script (bash / Git Bash / WSL).
# Brings up VectorAI DB (docker), backend (if present), and the frontend dev server.
set -euo pipefail

cd "$(dirname "$0")"

section() { printf "\n\033[36m=== %s ===\033[0m\n" "$1"; }

section "Starting Actian VectorAI DB"
docker compose -f vectorai-db-beta/docker-compose.yml up -d

if [ -x ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
else
  VENV_PY=".venv/bin/python"
fi

BACKEND_PID=""
cleanup() {
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "[start] stopping backend (pid $BACKEND_PID)"
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [ -f "backend/main.py" ]; then
  section "Starting FastAPI backend on :8000"
  if [ ! -x "$VENV_PY" ]; then
    echo "[start] .venv missing — run ./install.sh first" >&2
    exit 1
  fi
  "$VENV_PY" -m uvicorn backend.main:app --reload --port 8000 &
  BACKEND_PID=$!
  echo "[start] backend pid=$BACKEND_PID"
else
  echo "[start] backend/main.py not found yet — skipping API boot"
fi

section "Starting frontend (routewise/)"
( cd routewise && npm run dev )
