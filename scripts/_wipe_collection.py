"""One-shot helper: drop and recreate the routewise_crashes collection.

Used after fixing the normalize.py midnight-time bug so we re-embed
the corpus from a clean slate (the previous corpus had ~12% of rows
fake-timestamped to 00:00 from missing CRASH_TIME values).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings  # noqa: E402
from backend.vdb import ensure_collection, get_client  # noqa: E402


def main() -> int:
    name = get_settings().vdb_collection
    client = get_client()
    if client.collections.exists(name):
        print(f"dropping collection {name}")
        client.collections.delete(name)
    ensure_collection()
    print(f"collection {name} recreated, ready for re-ingest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
