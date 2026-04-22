#!/usr/bin/env bash
# Full-corpus reembed + snapshot dump for publishing a new VDB release asset.
# Run from the repo root. Takes ~15 min on CPU (embedding) + ~2 min (tarball).
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -x ".venv/Scripts/python.exe" ]; then
  PY=".venv/Scripts/python.exe"
else
  PY=".venv/bin/python"
fi

section() { printf "\n\033[36m=== %s ===\033[0m\n" "$1"; }

section "Booting VDB"
docker compose -f vectorai-db-beta/docker-compose.yml up -d
"$PY" scripts/wait_vdb.py --timeout 90

section "Wiping routewise_crashes collection"
"$PY" scripts/_wipe_collection.py

section "Ingesting full FDOT corpus (~140K rows, ~15 min)"
"$PY" scripts/ingest_fdot_crash.py

section "Ingesting news articles"
"$PY" scripts/ingest_news.py

section "Verifying point count"
"$PY" scripts/vdb_count.py

section "Stopping VDB (required for clean tarball)"
docker compose -f vectorai-db-beta/docker-compose.yml stop

section "Dumping snapshot tarball"
"$PY" scripts/dump_vdb_snapshot.py

section "Restarting VDB"
docker compose -f vectorai-db-beta/docker-compose.yml up -d

section "Refreshing ingest marker"
mkdir -p data/processed
: > data/processed/.fdot_ingest_v4

echo
echo "Done. vdb_snapshot.tar.gz is in the repo root — upload it to the"
echo "GitHub Release and paste the url/sha256/bytes into vdb_snapshot.manifest.json."