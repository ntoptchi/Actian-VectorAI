############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""VDE Operations — Vector Database Engine lifecycle + maintenance.

Demonstrates:
  - open / close collection (VDE lifecycle)
  - get_state, get_vector_count, get_stats
  - flush, rebuild_index, optimize
  - save/load snapshots
  - get_optimizations + list_rebuild_tasks

VDE is Actian's proprietary extension layer providing engine-level
control not found in other vector databases.

Usage::

    python examples/16_vde_operations.py
"""

from __future__ import annotations

import random

from actian_vectorai import (
    Distance,
    PointStruct,
    VectorAIClient,
    VectorParams,
)

SERVER = "localhost:50051"
COLLECTION = "vde_demo"
DIM = 16
fmt = "\n=== {:50} ==="


def main() -> None:
    random.seed(42)

    with VectorAIClient(SERVER) as client:
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)
        client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )

        # Insert data
        points = [
            PointStruct(
                id=i,
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={"batch": i // 10},
            )
            for i in range(1, 101)
        ]
        client.points.upsert(COLLECTION, points)
        print(f"✓ Inserted {len(points)} points")

        # ── Open collection ─────────────────────────────────
        print(fmt.format("vde.open_collection()"))
        ok = client.vde.open_collection(COLLECTION)
        print(f"  Opened: {ok}")

        # ── Get state ───────────────────────────────────────
        print(fmt.format("vde.get_state()"))
        state = client.vde.get_state(COLLECTION)
        print(f"  State: {state}")

        # ── Get vector count ────────────────────────────────
        print(fmt.format("vde.get_vector_count()"))
        count = client.vde.get_vector_count(COLLECTION)
        print(f"  Vectors: {count}")

        # ── Get stats ───────────────────────────────────────
        print(fmt.format("vde.get_stats()"))
        stats = client.vde.get_stats(COLLECTION)
        print(f"  Stats: {stats}")

        # ── Flush ───────────────────────────────────────────
        print(fmt.format("vde.flush()"))
        ok = client.vde.flush(COLLECTION)
        print(f"  Flushed: {ok}")

        # ── Rebuild index ───────────────────────────────────
        print(fmt.format("vde.rebuild_index()"))
        ok = client.vde.rebuild_index(COLLECTION)
        print(f"  Rebuilt: {ok}")

        # ── Optimize ────────────────────────────────────────
        print(fmt.format("vde.optimize()"))
        ok = client.vde.optimize(COLLECTION)
        print(f"  Optimized: {ok}")

        # ── Save / Load snapshot ────────────────────────────
        print(fmt.format("vde.save_snapshot()"))
        ok = client.vde.save_snapshot(COLLECTION)
        print(f"  Snapshot saved: {ok}")

        print(fmt.format("vde.load_snapshot()"))
        ok = client.vde.load_snapshot(COLLECTION)
        print(f"  Snapshot loaded: {ok}")

        # ── Get optimizations ───────────────────────────────
        print(fmt.format("vde.get_optimizations()"))
        opt = client.vde.get_optimizations(COLLECTION, include_completed=True)
        print(f"  Optimizations: {opt}")

        # ── List rebuild tasks ──────────────────────────────
        print(fmt.format("vde.list_rebuild_tasks()"))
        tasks, total = client.vde.list_rebuild_tasks(collection_name=COLLECTION)
        print(f"  Tasks: {len(tasks)} (total: {total})")

        # ── Close collection ────────────────────────────────
        print(fmt.format("vde.close_collection()"))
        ok = client.vde.close_collection(COLLECTION)
        print(f"  Closed: {ok}")

        # Cleanup
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
