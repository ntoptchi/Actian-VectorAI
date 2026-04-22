############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Point CRUD — upsert, get, update, delete points.

Demonstrates the full point lifecycle:
  - Upsert single and batch points
  - Get points by ID
  - Update vectors
  - Delete by IDs and by filter
  - Count points
  - Convenience methods: upsert_single, delete_by_ids

Usage::

    python examples/04_point_crud.py
"""

from __future__ import annotations

import random
import uuid

from actian_vectorai import (
    Distance,
    Field,
    FilterBuilder,
    PointStruct,
    VectorAIClient,
    VectorParams,
)

SERVER = "localhost:50051"
COLLECTION = "point_crud_demo"
DIM = 32
fmt = "\n=== {:50} ==="


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

        # ── Upsert (batch) with UUID IDs ────────────────────
        print(fmt.format("Batch upsert (UUID IDs)"))
        point_ids = [str(uuid.uuid4()) for _ in range(20)]
        points = [
            PointStruct(
                id=pid,
                vector=make_vector(),
                payload={"category": ["A", "B", "C"][i % 3], "value": i * 10},
            )
            for i, pid in enumerate(point_ids)
        ]
        result = client.points.upsert(COLLECTION, points)
        print(f"  ✓ Upserted 20 points (status={result.status})")

        # ── Upsert single (convenience) ─────────────────────
        print(fmt.format("Upsert single (UUID)"))
        single_id = str(uuid.uuid4())
        result = client.points.upsert_single(
            COLLECTION,
            id=single_id,
            vector=make_vector(),
            payload={"category": "special"},
        )
        print(f"  ✓ Upserted point {single_id[:8]}… (status={result.status})")

        # ── Get by IDs ──────────────────────────────────────
        print(fmt.format("Get points by UUID"))
        target_ids = [point_ids[0], point_ids[4], point_ids[9], single_id]
        retrieved = client.points.get(COLLECTION, ids=target_ids)
        for p in retrieved:
            print(f"  id={p.id}  payload={p.payload}")

        # ── Count ───────────────────────────────────────────
        print(fmt.format("Count points"))
        count = client.points.count(COLLECTION)
        print(f"  Total points: {count}")

        f = FilterBuilder().must(Field("category").eq("A")).build()
        count_a = client.points.count(
            COLLECTION,
            filter=f,
        )
        print(f"  Category A:   {count_a}")

        # ── Update vectors ──────────────────────────────────
        print(fmt.format("Update vectors"))
        new_vec = make_vector()
        result = client.points.update_vectors(
            COLLECTION,
            points=[{"id": point_ids[0], "vectors": new_vec}],
        )
        print(f"  ✓ Updated vector for point {point_ids[0][:8]}… (status={result.status})")

        # ── Delete by IDs ───────────────────────────────────
        print(fmt.format("Delete by UUID IDs"))
        result = client.points.delete_by_ids(COLLECTION, ids=[single_id], strict=True)
        print(f"  ✓ Deleted point {single_id[:8]}… (status={result.status})")

        count = client.points.count(COLLECTION)
        print(f"  Remaining: {count}")

        # ── Delete by filter ────────────────────────────────
        print(fmt.format("Delete by filter"))
        f = FilterBuilder().must(Field("category").eq("C")).build()
        result = client.points.delete(
            COLLECTION,
            filter=f,
        )
        print(f"  ✓ Deleted category C points (status={result.status})")

        count = client.points.count(COLLECTION)
        print(f"  Remaining: {count}")

        # ── Cleanup ─────────────────────────────────────────
        client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
