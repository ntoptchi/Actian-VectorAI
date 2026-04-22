#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# Ingest scraped news articles into the Actian VectorAI database.
#
# Usage:
#   ./ingest_news.sh                          # ingest all news JSON files
#   ./ingest_news.sh --file data/raw/semantic_crashes.json   # specific file
#   ./ingest_news.sh --limit 50               # first 50 articles only
#
# After ingesting, RESTART the backend so the in-memory cache reloads.
# ──────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv if present
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

echo "==> Starting news article ingestion into VectorAI DB..."
python scripts/ingest_news.py "$@"
echo ""
echo "==> Done! Remember to restart the backend so the crash cache reloads."
echo "    Kill uvicorn, then re-run: ./start.sh"
