############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""UUID Point IDs — using string UUIDs as point identifiers.

Demonstrates:
  - Creating points with UUID string IDs
  - Upserting, getting, searching with UUID IDs
  - Filtering by UUID with ``has_id``
  - Mixed ID types (UUID + integer in same collection)

Usage::

    python examples/28_uuid_point_ids.py
"""

from __future__ import annotations

import random
import uuid

from actian_vectorai import (
    Distance,
    FilterBuilder,
    PointStruct,
    VectorAIClient,
    VectorParams,
    has_id,
)

SERVER = "localhost:50051"
COLLECTION = "uuid_demo"
DIM = 32


def make_vector() -> list[float]:
    return [random.gauss(0, 1) for _ in range(DIM)]


def main() -> None:
    random.seed(42)

    with VectorAIClient(SERVER) as client:
        # Setup
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)
        client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )

        # ── Batch upsert with UUID IDs ──────────────────────
        print("=== Batch upsert with UUID IDs ===")
        point_ids = [str(uuid.uuid4()) for _ in range(20)]
        points = [
            PointStruct(
                id=pid,
                vector=make_vector(),
                payload={
                    "category": ["electronics", "books", "clothing"][i % 3],
                    "price": round(random.uniform(5, 200), 2),
                },
            )
            for i, pid in enumerate(point_ids)
        ]
        client.points.upsert(COLLECTION, points)
        print(f"  ✓ Upserted {len(points)} points with UUID IDs")
        print(f"  Sample IDs: {point_ids[:3]}")

        # ── Upsert single with UUID ─────────────────────────
        print("\n=== Upsert single with UUID ===")
        single_id = str(uuid.uuid4())
        client.points.upsert_single(
            COLLECTION,
            id=single_id,
            vector=make_vector(),
            payload={"category": "special", "price": 99.99},
        )
        print(f"  ✓ Upserted single point: {single_id}")

        # ── Get by UUID IDs ─────────────────────────────────
        print("\n=== Get by UUID IDs ===")
        target_ids = point_ids[:3]
        results = client.points.get(COLLECTION, ids=target_ids, with_payload=True)
        print(f"  Retrieved {len(results)} points:")
        for r in results:
            print(f"    id={r.id}  payload={r.payload}")

        # ── Search returns UUID IDs ──────────────────────────
        print("\n=== Search (results have UUID IDs) ===")
        query = make_vector()
        results = client.points.search(COLLECTION, vector=query, limit=5)
        print(f"  Top {len(results)} results:")
        for r in results:
            print(f"    id={r.id}  score={r.score:.4f}")

        # ── Filter by specific UUID IDs using has_id ────────
        print("\n=== Filter by UUID IDs (has_id) ===")
        subset = point_ids[:5]
        id_filter = FilterBuilder().must(has_id(subset)).build()
        results = client.points.search(
            COLLECTION,
            vector=query,
            filter=id_filter,
            limit=10,
        )
        print(f"  Searched with has_id filter for {len(subset)} IDs: {len(results)} results")
        for r in results:
            print(f"    id={r.id}  score={r.score:.4f}")

        # ── Payload operations with UUID IDs ─────────────────
        print("\n=== Payload ops with UUID IDs ===")
        client.points.set_payload(
            COLLECTION,
            payload={"featured": True},
            ids=[point_ids[0], point_ids[1]],
        )
        results = client.points.get(
            COLLECTION,
            ids=[point_ids[0]],
            with_payload=True,
        )
        print(f"  After set_payload: {results[0].payload}")

        client.points.delete_payload(
            COLLECTION,
            keys=["featured"],
            ids=[point_ids[0]],
            strict=True,
        )
        results = client.points.get(
            COLLECTION,
            ids=[point_ids[0]],
            with_payload=True,
        )
        print(f"  After delete_payload: {results[0].payload}")

        # ── Delete by UUID IDs ───────────────────────────────
        print("\n=== Delete by UUID IDs ===")
        before = client.points.count(COLLECTION)
        client.points.delete_by_ids(COLLECTION, [point_ids[-1], point_ids[-2]], strict=True)
        after = client.points.count(COLLECTION)
        print(f"  Before: {before}, After: {after} (deleted 2)")

        # ── Mixed integer + UUID IDs ─────────────────────────
        print("\n=== Mixed ID types ===")
        mixed_points = [
            PointStruct(id=99001, vector=make_vector(), payload={"type": "int_id"}),
            PointStruct(
                id=str(uuid.uuid4()),
                vector=make_vector(),
                payload={"type": "uuid_id"},
            ),
        ]
        client.points.upsert(COLLECTION, mixed_points)
        retrieved = client.points.get(
            COLLECTION,
            ids=[99001],
            with_payload=True,
        )
        print(f"  Int ID point: id={retrieved[0].id}  payload={retrieved[0].payload}")
        retrieved = client.points.get(
            COLLECTION,
            ids=[mixed_points[1].id],
            with_payload=True,
        )
        print(f"  UUID point:   id={retrieved[0].id}  payload={retrieved[0].payload}")

        count = client.points.count(COLLECTION)
        print(f"\n  Total points: {count}")

        # Cleanup
        client.collections.delete(COLLECTION)
        print(f"\n✓ Cleaned up collection '{COLLECTION}'")


if __name__ == "__main__":
    main()
