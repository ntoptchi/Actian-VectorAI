#!/usr/bin/env bash
# RouteWise install script (bash / Git Bash / WSL).
# Idempotent first-time setup. Re-run any time.
set -euo pipefail

cd "$(dirname "$0")"

section() { printf "\n\033[36m=== %s ===\033[0m\n" "$1"; }
need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf "\033[31m[install] missing dependency: %s\033[0m\n" "$1"
    printf "\033[33m          %s\033[0m\n" "$2"
    exit 1
  fi
}

section "Checking prerequisites"
need python  "Install Python 3.11+ (https://www.python.org/downloads/)"
need docker  "Install Docker Desktop (https://www.docker.com/products/docker-desktop/)"
need node    "Install Node.js 20+ (https://nodejs.org/)"
need npm     "Comes with Node.js"

section "Python venv (.venv)"
if [ ! -d ".venv" ]; then
  python -m venv .venv
  echo "[install] created .venv"
else
  echo "[install] .venv already exists"
fi

# Pick the right venv python depending on platform
if [ -x ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
else
  VENV_PY=".venv/bin/python"
fi

"$VENV_PY" -m pip install --upgrade pip wheel
"$VENV_PY" -m pip install -r requirements.txt

section "Actian VectorAI DB python client"
WHEEL="$(ls vectorai-db-beta/actian_vectorai-*.whl 2>/dev/null | head -n1 || true)"
if [ -n "$WHEEL" ]; then
  "$VENV_PY" -m pip install --upgrade "$WHEEL"
else
  echo "[install] no actian_vectorai wheel found in vectorai-db-beta/, skipping"
fi

section "Embedding model (all-MiniLM-L6-v2)"
"$VENV_PY" scripts/download_model.py

section "Pulling Actian VectorAI DB Docker image"
docker pull williamimoh/actian-vectorai-db:latest

section "Frontend (routewise/)"
( cd routewise && npm install )

section "Done"
echo "Run ./start.sh to bring everything up."
