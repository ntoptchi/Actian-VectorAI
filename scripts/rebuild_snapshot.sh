#!/usr/bin/env bash
# Re-embed the small + fast-changing corpora (news + LLM coaching lessons) and
# dump the VDB snapshot tarball for publishing as a GitHub Release asset. Runs
# from the repo root.
#
# By default this keeps the 140K routewise_crashes embeddings untouched â€” they
# take ~15 min to rebuild on CPU and never change outside FDOT dataset bumps.
# To do a full-corpus rebuild (wipe + re-embed crashes, news, and lessons),
# export ``REBUILD_CRASHES=1`` before running.
#
# Usage::
#
#   scripts/rebuild_snapshot.sh               # fast: news + lessons only (~2-3 min)
#   REBUILD_CRASHES=1 scripts/rebuild_snapshot.sh   # full rebuild (~20 min)

set -euo pipefail

cd "$(dirname "$0")/.."

if [ -x ".venv/Scripts/python.exe" ]; then
  PY=".venv/Scripts/python.exe"
else
  PY=".venv/bin/python"
fi

REBUILD_CRASHES="${REBUILD_CRASHES:-0}"

section() { printf "\n\033[36m=== %s ===\033[0m\n" "$1"; }

section "Booting VDB"
docker compose -f vectorai-db-beta/docker-compose.yml up -d
"$PY" scripts/wait_vdb.py --timeout 90

if [ "$REBUILD_CRASHES" = "1" ]; then
  section "Wiping routewise_crashes collection (REBUILD_CRASHES=1)"
  "$PY" scripts/_wipe_collection.py

  section "Ingesting full FDOT corpus (~140K rows, ~15 min)"
  "$PY" scripts/ingest_fdot_crash.py
else
  section "Skipping routewise_crashes rebuild (set REBUILD_CRASHES=1 to force)"
fi

section "Re-ingesting news articles (upsert â€” safe over existing points)"
"$PY" scripts/ingest_news.py

section "Wiping + re-ingesting routewise_coaching collection"
"$PY" -c "from backend.config import get_settings; from backend.vdb import get_client; n=get_settings().vdb_coaching_collection; c=get_client(); (c.collections.delete(n) if c.collections.exists(n) else None); print(f'wiped {n}')"
"$PY" scripts/ingest_coaching.py

section "Verifying point counts"
"$PY" scripts/vdb_count.py

section "Stopping VDB (required for clean tarball)"
docker compose -f vectorai-db-beta/docker-compose.yml stop

section "Dumping snapshot tarball"
"$PY" scripts/dump_vdb_snapshot.py

section "Restarting VDB"
docker compose -f vectorai-db-beta/docker-compose.yml up -d

section "Refreshing ingest marker"
mkdir -p data/processed
# Bump this suffix whenever you bump `ingest_version` in vdb_snapshot.manifest.json
: > data/processed/.fdot_ingest_v5

echo
echo "Done. vdb_snapshot.tar.gz is in the repo root â€” upload it to the"
echo "GitHub Release and paste the url/sha256/bytes into vdb_snapshot.manifest.json."
