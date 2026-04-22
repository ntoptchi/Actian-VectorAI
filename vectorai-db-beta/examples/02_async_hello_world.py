############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Async Hello World — async/await version of the getting-started example.

Demonstrates ``AsyncVectorAIClient`` with the ``async with`` context
manager pattern.

Usage::

    python examples/02_async_hello_world.py
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
from actian_vectorai.exceptions import ErrorCode, ValidationError, VectorAIError

SERVER = "localhost:50051"


async def main() -> None:
    async with AsyncVectorAIClient(SERVER) as client:
        await client.health_check()

        # ── Demonstrate ValidationError with an invalid collection name ──
        bad_name = "Facial Recognition"  # spaces not allowed
        try:
            if await client.collections.exists(bad_name):
                await client.collections.delete(bad_name)
            await client.collections.create(
                bad_name,
                vectors_config=VectorParams(size=128, distance=Distance.Euclid),
            )
        except ValidationError as e:
            print(f"✗ Validation error: {e}")
            print(f"  numeric check : {e.code == 422}")
            print(f"  named check   : {e.code == ErrorCode.UNPROCESSABLE_ENTITY}")
        except VectorAIError as e:
            print(f"✗ Failed: {e}")

        # ── Main demo with a valid collection name ──
        collection = "async_hello_world"

        if await client.collections.exists(collection):
            await client.collections.delete(collection)

        await client.collections.create(
            collection,
            vectors_config=VectorParams(size=128, distance=Distance.Euclid),
        )
        print(f"✓ Created collection '{collection}'")

        random.seed(123)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=[random.gauss(0, 1) for _ in range(128)],
                payload={"label": f"item_{i}"},
            )
            for i in range(20)
        ]
        await client.points.upsert(collection, points)
        print(f"✓ Inserted {len(points)} points")

        query = [random.gauss(0, 1) for _ in range(128)]
        results = await client.points.search(collection, vector=query, limit=5, with_vectors=True, with_payload=False)
        print(f"\nTop 5 results: {results}")
        for r in results:
            print(f"  id={r.id}  score={r.score:.4f}  payload={r.payload}  vectors={r.vectors}")

        await client.collections.delete(collection)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
