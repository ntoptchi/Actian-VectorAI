"""Create RigSense collections and load the seed data.

Idempotent: re-running drops and recreates everything.

Usage::

    python scripts/bootstrap.py                 # default: pump CSV seed
    python scripts/bootstrap.py --source=hand   # original hand-written incidents
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import get_settings
from backend.db.chunks import upsert_manual_chunks
from backend.db.client import get_client
from backend.db.collections import bootstrap_collections
from backend.db.incidents import upsert_incidents
from backend.db.manuals import upsert_manuals
from backend.seed.sample_incidents import PAST_INCIDENTS as HAND_PAST_INCIDENTS
from backend.seed.sample_manuals import REPAIR_MANUALS


def _load_incidents(source: str):
    if source == "hand":
        return HAND_PAST_INCIDENTS
    if source == "pump":
        from backend.seed.pump_dataset import build_incidents

        return build_incidents()
    raise SystemExit(f"Unknown --source={source!r}. Expected 'pump' or 'hand'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap the RigSense VectorAI DB.")
    parser.add_argument(
        "--source",
        choices=("pump", "hand"),
        default="pump",
        help="Where past_incidents come from. 'pump' synthesises from the "
             "industrial-pump CSV, 'hand' uses the original hand-written set.",
    )
    args = parser.parse_args()

    cfg = get_settings()
    print(f"Connecting to VectorAI DB at {cfg.vectorai_host} ...")

    incidents = _load_incidents(args.source)

    with get_client() as client:
        info = client.health_check()
        print(f"  connected: {info['title']} v{info['version']}")

        print("Creating collections ...")
        names = bootstrap_collections(client, cfg)
        for n in names:
            print(f"  created  {n}")

        print(f"Seeding {len(incidents)} past incidents (source={args.source}) ...")
        n_inc = upsert_incidents(client, incidents)
        print(f"  upserted {n_inc} incidents")

        print(f"Seeding {len(REPAIR_MANUALS)} repair manuals ...")
        n_man = upsert_manuals(client, REPAIR_MANUALS)
        n_chunks = upsert_manual_chunks(client, REPAIR_MANUALS)
        print(f"  upserted {n_man} manuals, {n_chunks} chunks")

    print("Bootstrap complete.")


if __name__ == "__main__":
    main()
