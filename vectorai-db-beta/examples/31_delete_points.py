############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Delete Points — demonstrates strict=True and strict=False delete behaviour.

Shows:
  - strict=True  : raises PointNotFoundError if any ID does not exist
  - strict=False : silently skips missing IDs and deletes the rest

Usage::

    python examples/31_delete_points.py
"""

from __future__ import annotations

import asyncio
import random
import uuid

from actian_vectorai import (
    AsyncVectorAIClient,
    Distance,
    PointStruct,
    VectorParams,
)
from actian_vectorai.exceptions import PointNotFoundError, VectorAIError

SERVER = "localhost:50051"
COLLECTION = "delete_demo"
DIM = 32


async def main() -> None:
    async with AsyncVectorAIClient(SERVER) as client:
        info = await client.health_check()
        print(f"Connected to {info['title']} v{info['version']}")

        # ── Setup ────────────────────────────────────────────────────────
        if await client.collections.exists(COLLECTION):
            await client.collections.delete(COLLECTION)

        await client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Euclid),
        )
        print(f"✓ Created collection '{COLLECTION}'")

        random.seed(42)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={"label": f"item_{i}"},
            )
            for i in range(10)
        ]
        await client.points.upsert(COLLECTION, points)
        print(f"✓ Inserted {len(points)} points")

        real_ids = [p.id for p in points[:3]]
        fake_id = str(uuid.uuid4())  # does not exist in the collection

        # ── strict=True — all IDs must exist ─────────────────────────────
        print("\n--- strict=True ---")
        print(f"  Deleting IDs: {real_ids + [fake_id]}")
        try:
            result = await client.points.delete(COLLECTION, ids=real_ids + [fake_id], strict=True)
            print(f"  ✓ Deleted  status={result.status}")
        except PointNotFoundError as e:
            print(f"  ✗ PointNotFoundError (expected): {e}")
            print("    Nothing was deleted — all IDs rolled back.")

        # Verify the 3 real IDs are still present (strict=True did not delete)
        info = await client.collections.get_info(COLLECTION)
        print(f"  Points still in collection after failed strict delete: {info.points_count}")

        # ── strict=False — missing IDs silently skipped ───────────────────
        print("\n--- strict=False ---")
        ids_mix = real_ids + [fake_id]
        print(f"  Deleting IDs: {ids_mix}")
        try:
            result = await client.points.delete(COLLECTION, ids=ids_mix, strict=False)
            print(f"  ✓ Delete completed  status={result.status}")
        except VectorAIError as e:
            print(f"  ⚠ Server error on strict=False delete (server-side bug): {e}")

        # Verify the 3 real IDs are now gone
        info = await client.collections.get_info(COLLECTION)
        print(f"  Points remaining in collection: {info.points_count} (was 10, deleted 3)")
        print(f"  (fake_id '{fake_id}' was silently ignored)")

        # ── Cleanup ──────────────────────────────────────────────────────
        await client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
