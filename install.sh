#!/usr/bin/env bash
# Install prerequisites for RigSense:
#   - vectorai-db-beta Docker image
#   - backend Python venv + dependencies
#   - dashboard npm dependencies
#
# Idempotent: re-running only does the work that's actually needed.
#
# Usage:  ./install.sh

set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"

log() { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }
die() { printf '\n\033[1;31m!!\033[0m %s\n' "$*" >&2; exit 1; }

require() {
    command -v "$1" >/dev/null 2>&1 || die "'$1' not found on PATH. $2"
}

log "Checking prerequisites"
require docker  "Install Docker Desktop: https://docs.docker.com/get-docker/"
require node    "Install Node.js 18+: https://nodejs.org/"
require npm     "Install Node.js 18+: https://nodejs.org/"

# Pick a Python >=3.10. Prefer python3 on macOS/Linux, python on Windows.
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    die "Python 3.10+ not found. https://www.python.org/downloads/"
fi

PY_VERSION=$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log "Using Python $PY_VERSION ($PYTHON)"

log "Pulling Actian VectorAI DB image"
(cd "$ROOT/vectorai-db-beta" && docker compose pull)

log "Creating backend venv"
VENV="$ROOT/backend/.venv"
if [ ! -d "$VENV" ]; then
    "$PYTHON" -m venv "$VENV"
else
    echo "  venv already exists at $VENV"
fi

# Cross-platform venv python path (Windows uses Scripts/, *nix uses bin/).
if [ -x "$VENV/Scripts/python.exe" ]; then
    VENV_PY="$VENV/Scripts/python.exe"
else
    VENV_PY="$VENV/bin/python"
fi

log "Installing backend dependencies"
"$VENV_PY" -m pip install --upgrade pip --quiet
# Run pip from backend/ so the relative ../vectorai-db-beta/*.whl path in
# requirements.txt resolves correctly (pip resolves relative paths against CWD).
(cd "$ROOT/backend" && "$VENV_PY" -m pip install -r requirements.txt)

log "Pre-downloading embedding model (all-MiniLM-L6-v2, ~90 MB)"
# Cached under ~/.cache/huggingface after this; subsequent runs are instant.
# Skipped when USE_MOCK_EMBEDDINGS=true is set in the environment.
"$VENV_PY" - <<'PY'
import os
if os.environ.get("USE_MOCK_EMBEDDINGS", "").lower() in {"1", "true", "yes"}:
    print("  USE_MOCK_EMBEDDINGS set, skipping model download")
    raise SystemExit(0)
from sentence_transformers import SentenceTransformer
model_name = os.environ.get(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
print(f"  downloading {model_name} ...")
m = SentenceTransformer(model_name)
v = m.encode(["rigsense install-time warmup"], normalize_embeddings=True)
print(f"  ok: dim={v.shape[1]}")
PY

log "Installing dashboard dependencies"
(cd "$ROOT" && npm install)

log "Seeding backend/.env if missing"
if [ ! -f "$ROOT/backend/.env" ]; then
    cp "$ROOT/backend/.env.example" "$ROOT/backend/.env"
    echo "  created backend/.env from .env.example"
else
    echo "  backend/.env already exists (untouched)"
fi

log "Install complete. Next: ./start.sh"
