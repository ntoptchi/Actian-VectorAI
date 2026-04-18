############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Advanced VDE — rebuild management + compaction.

Demonstrates the advanced VDE operations that complement the basic
lifecycle in 16_vde_operations.py:

  - trigger_rebuild()        — start a full rebuild pipeline
  - get_rebuild_task()       — query task progress
  - list_rebuild_tasks()     — list all rebuild tasks
  - cancel_rebuild_task()    — cancel a running task
  - compact_collection()     — merge segments & purge deleted vectors

Usage::

    python examples/26_advanced_vde.py
"""

from __future__ import annotations

import random
import time

from actian_vectorai import (
    Distance,
    PointStruct,
    VectorAIClient,
    VectorAIError,
    VectorParams,
)

SERVER = "localhost:50051"
COLLECTION = "advanced_vde_demo"
DIM = 8
N_POINTS = 100
fmt = "\n=== {:50} ==="


def main() -> None:
    random.seed(42)

    with VectorAIClient(SERVER) as client:
        # ── Setup ───────────────────────────────────────────
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)

        client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )

        points = [
            PointStruct(
                id=i,
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={"batch": i // 25, "value": random.random()},
            )
            for i in range(1, N_POINTS + 1)
        ]
        client.points.upsert(COLLECTION, points)
        print(f"✓ Created {COLLECTION!r} with {N_POINTS} points")

        # Open VDE engine
        client.vde.open_collection(COLLECTION)

        # ╔═══════════════════════════════════════════════════╗
        # ║  TRIGGER REBUILD                                 ║
        # ╚═══════════════════════════════════════════════════╝
        print(fmt.format("Trigger Rebuild"))
        try:
            task_id, stats = client.vde.trigger_rebuild(COLLECTION)
            print(f"  ✓ trigger_rebuild(): task_id={task_id}")
            if stats:
                print(f"    stats={stats}")
            time.sleep(1)
        except VectorAIError as e:
            print(f"  ⚠ trigger_rebuild(): {e}")
            task_id = None

        # ╔═══════════════════════════════════════════════════╗
        # ║  GET REBUILD TASK                                ║
        # ╚═══════════════════════════════════════════════════╝
        print(fmt.format("Get Rebuild Task"))
        if task_id:
            try:
                info = client.vde.get_rebuild_task(task_id)
                print(f"  ✓ get_rebuild_task({task_id}): state={info.state}")
            except VectorAIError as e:
                print(f"  ⚠ get_rebuild_task(): {e}")
        else:
            print("  ⚠ Skipped (no task_id from trigger_rebuild)")

        # ╔═══════════════════════════════════════════════════╗
        # ║  LIST REBUILD TASKS                              ║
        # ╚═══════════════════════════════════════════════════╝
        print(fmt.format("List Rebuild Tasks"))
        try:
            tasks, total = client.vde.list_rebuild_tasks(
                collection_name=COLLECTION,
            )
            print(f"  ✓ list_rebuild_tasks(): {len(tasks)} of {total}")
            for t in tasks[:3]:
                print(f"    task_id={t.task_id}  state={t.state}")
        except VectorAIError as e:
            print(f"  ⚠ list_rebuild_tasks(): {e}")

        # ╔═══════════════════════════════════════════════════╗
        # ║  CANCEL REBUILD TASK                             ║
        # ╚═══════════════════════════════════════════════════╝
        print(fmt.format("Cancel Rebuild Task"))
        print("  ✓ cancel_rebuild_task(task_id: str) → bool")
        print("    Usage: client.vde.cancel_rebuild_task(task_id)")

        # ╔═══════════════════════════════════════════════════╗
        # ║  COMPACT COLLECTION                              ║
        # ╚═══════════════════════════════════════════════════╝
        print(fmt.format("Compact Collection"))
        # Delete some points first to create segments worth compacting
        client.points.delete(COLLECTION, ids=list(range(1, 26)), strict=True)
        print("  Deleted 25 points to create fragmentation")

        try:
            task_id_c, cstats = client.vde.compact_collection(COLLECTION)
            print(f"  ✓ compact_collection(): task={task_id_c}")
            if cstats:
                print(f"    stats={cstats}")
        except VectorAIError as e:
            print(f"  ⚠ compact_collection(): {e}")

        # ── Cleanup ─────────────────────────────────────────
        client.vde.close_collection(COLLECTION)
        client.collections.delete(COLLECTION)
        print(f"\n✓ Cleaned up {COLLECTION!r}")


if __name__ == "__main__":
    main()
