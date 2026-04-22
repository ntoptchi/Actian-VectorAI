############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Collection Management — create, list, info, update, delete.

Demonstrates the full collection lifecycle including:
  - Create with various configurations
  - List all collections
  - Get detailed collection info
  - Update collection parameters
  - Check existence
  - Delete collection
  - Recreate and get_or_create convenience methods

Usage::

    python examples/03_collection_management.py
"""

from __future__ import annotations

from actian_vectorai import (
    Distance,
    HnswConfigDiff,
    IndexType,
    OptimizersConfigDiff,
    VectorAIClient,
    VectorParams,
)

SERVER = "localhost:50051"
fmt = "\n=== {:50} ==="


def main() -> None:
    with VectorAIClient(SERVER) as client:
        # ── Create ──────────────────────────────────────────
        print(fmt.format("Create collections"))

        # Basic collection
        client.collections.create(
            "col_basic",
            vectors_config=VectorParams(size=128, distance=Distance.Cosine),
        )
        print("  ✓ col_basic (128d, cosine)")

        # Collection with custom HNSW config
        client.collections.create(
            "col_hnsw",
            vectors_config=VectorParams(size=256, distance=Distance.Euclid),
            hnsw_config=HnswConfigDiff(m=32, ef_construct=200),
        )
        print("  ✓ col_hnsw (256d, euclid, m=32)")

        # Collection with FLAT index
        client.collections.create(
            "col_flat",
            vectors_config=VectorParams(size=64, distance=Distance.Dot),
            index_type=IndexType.INDEX_TYPE_FLAT,
        )
        print("  ✓ col_flat (64d, dot, flat index)")

        # ── List ────────────────────────────────────────────
        print(fmt.format("List collections"))
        names = client.collections.list()
        for name in names:
            print(f"  • {name}")

        # ── Info ────────────────────────────────────────────
        print(fmt.format("Collection info"))
        info = client.collections.get_info("col_basic")
        print(f"  name:   {info.config.params.collection_name if info.config else 'col_basic'}")
        print(f"  status: {info.status}")
        print(f"  points: {info.points_count}")

        # ── Exists ──────────────────────────────────────────
        print(fmt.format("Check existence"))
        print(f"  col_basic exists: {client.collections.exists('col_basic')}")
        print(f"  col_none exists:  {client.collections.exists('col_none')}")

        # ── Update ──────────────────────────────────────────
        print(fmt.format("Update collection"))
        client.collections.update(
            "col_hnsw",
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=50_000,
            ),
        )
        print("  ✓ Updated optimizers on col_hnsw")

        # ── Recreate (delete + create) ──────────────────────
        print(fmt.format("Recreate collection"))
        client.collections.recreate(
            "col_basic",
            vectors_config=VectorParams(size=64, distance=Distance.Cosine),
        )
        print("  ✓ Recreated col_basic as 64d")

        # ── Get or create ───────────────────────────────────
        print(fmt.format("Get or create"))
        info = client.collections.get_or_create(
            "col_basic",
            vectors_config=VectorParams(size=64, distance=Distance.Cosine),
        )
        print(f"  ✓ Got existing col_basic (status={info.status})")

        info = client.collections.get_or_create(
            "col_new",
            vectors_config=VectorParams(size=32, distance=Distance.Cosine),
        )
        print(f"  ✓ Created new col_new (status={info.status})")

        # ── Cleanup ─────────────────────────────────────────
        print(fmt.format("Cleanup"))
        for name in ["col_basic", "col_hnsw", "col_flat", "col_new"]:
            if client.collections.exists(name):
                client.collections.delete(name)
                print(f"  ✓ Deleted {name}")


if __name__ == "__main__":
    main()
