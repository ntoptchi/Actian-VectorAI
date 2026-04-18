############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Delete Operations — comprehensive point deletion patterns.

Demonstrates every delete variant:
  - delete_by_ids()  — delete specific points by integer/UUID IDs
  - delete(ids=...)  — delete by ID list
  - delete(filter=.) — delete by filter condition
  - delete(strict=True) — strict mode: fail if any ID not found
  - Combined delete + verify with count/get

Usage::

    python examples/23_delete_operations.py
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
from actian_vectorai.exceptions import PointNotFoundError

SERVER = "localhost:50051"
COLLECTION = "delete_demo"
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

        # Insert 50 points with integer IDs
        points = [
            PointStruct(
                id=i,
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={
                    "category": ["tech", "science", "art"][i % 3],
                    "value": random.randint(1, 100),
                },
            )
            for i in range(1, 51)
        ]
        client.points.upsert(COLLECTION, points)
        count = client.points.count(COLLECTION)
        print(f"✓ Inserted 50 points (count={count})")

        # ── 1. delete_by_ids — convenience method ────────────
        print(fmt.format("delete_by_ids([1, 2, 3])"))
        result = client.points.delete_by_ids(COLLECTION, ids=[1, 2, 3], strict=True)
        count = client.points.count(COLLECTION)
        print(f"  Result: {result.status}  Count after: {count}")

        # ── 2. delete(ids=...) — standard delete by IDs ─────
        print(fmt.format("delete(ids=[4, 5, 6])"))
        result = client.points.delete(COLLECTION, ids=[4, 5, 6], strict=True)
        count = client.points.count(COLLECTION)
        print(f"  Result: {result.status}  Count after: {count}")

        # ── 3. delete(filter=...) — delete by filter ─────────
        print(fmt.format("delete(filter=category=='art')"))
        f = FilterBuilder().must(Field("category").eq("art")).build()
        art_count_before = client.points.count(COLLECTION, filter=f)
        result = client.points.delete(COLLECTION, filter=f)
        art_count_after = client.points.count(COLLECTION, filter=f)
        count = client.points.count(COLLECTION)
        print(f"  Art before: {art_count_before}, after: {art_count_after}")
        print(f"  Total count: {count}")

        # ── 4. delete with wait=True ─────────────────────────
        print(fmt.format("delete(ids=[7], wait=True)"))
        result = client.points.delete(COLLECTION, ids=[7], wait=True, strict=True)
        print(f"  Result: {result.status}")

        # ── 5. delete(strict=True) — errors if ID missing ───
        print(fmt.format("delete(strict=True) — missing ID"))
        try:
            # ID 999 doesn't exist → strict mode raises
            client.points.delete(COLLECTION, ids=[999], strict=True)
            print("  No error raised (server accepted)")
        except PointNotFoundError as e:
            print(f"  PointNotFoundError: {e}")
        except Exception as e:
            print(f"  Error: {type(e).__name__}: {e}")

        # ── 6. Verify deletions with get ─────────────────────
        print(fmt.format("Verify with get()"))
        remaining = client.points.get(COLLECTION, ids=[8, 9, 10])
        print(f"  Points [8,9,10] retrieved: {[p.id for p in remaining]}")

        deleted = client.points.get(COLLECTION, ids=[1, 2, 3])
        print(f"  Points [1,2,3] (deleted): {[p.id for p in deleted]}")

        # ── 7. Delete remaining with UUID IDs ────────────────
        # Insert some UUID-ID points then delete them
        uuid_points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={"type": "uuid_point"},
            )
            for _ in range(5)
        ]
        client.points.upsert(COLLECTION, uuid_points)
        uuid_ids = [p.id for p in uuid_points]
        print(fmt.format("delete_by_ids() — UUID IDs"))
        client.points.delete_by_ids(COLLECTION, ids=uuid_ids, strict=True)
        f_uuid = FilterBuilder().must(Field("type").eq("uuid_point")).build()
        count = client.points.count(COLLECTION, filter=f_uuid)
        print(f"  UUID points after delete: {count}")

        # Cleanup
        client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
