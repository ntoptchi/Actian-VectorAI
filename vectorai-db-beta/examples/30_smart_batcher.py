############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Smart Batcher — automatic batching for high-throughput ingestion.

Demonstrates using ``SmartBatcher`` to buffer individual upsert calls
and flush them efficiently in batches.  Configurable by size, byte
threshold, and time limit.

Usage::

    python examples/30_smart_batcher.py
"""

from __future__ import annotations

import asyncio
import random

from actian_vectorai import (
    AsyncVectorAIClient,
    BatcherConfig,
    Distance,
    PointStruct,
    SmartBatcher,
    VectorParams,
)

SERVER = "localhost:50051"
COLLECTION = "smart_batcher_demo"
DIM = 32


async def main() -> None:
    random.seed(42)

    async with AsyncVectorAIClient(SERVER) as client:
        # Setup
        if await client.collections.exists(COLLECTION):
            await client.collections.delete(COLLECTION)
        await client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )

        # ── Define flush callback ────────────────────────────
        flush_count = 0

        async def flush_callback(collection_name, items):
            nonlocal flush_count
            flush_count += 1
            points = [
                PointStruct(id=item.id, vector=item.vector, payload=item.payload) for item in items
            ]
            await client.points.upsert(collection_name, points)
            print(f"  Flushed batch #{flush_count}: {len(items)} points")

        # ── Configure batcher ────────────────────────────────
        print("=== Smart Batcher with custom config ===")
        config = BatcherConfig(
            size_limit=25,  # Flush every 25 items
            byte_limit=1024 * 1024,  # or 1MB
            time_limit_ms=500,  # or 500ms
            max_concurrent_flushes=2,
        )
        print(f"  Config: size={config.size_limit}, time={config.time_limit_ms}ms")

        batcher = SmartBatcher(flush_callback, config)
        await batcher.start()

        # ── Add 100 items (will auto-batch at 25) ───────────
        print("\n=== Adding 100 items ===")
        futures = []
        for i in range(100):
            vector = [random.gauss(0, 1) for _ in range(DIM)]
            payload = {"batch_item": i, "category": f"cat_{i % 5}"}
            future = await batcher.add(COLLECTION, i + 1, vector, payload)
            futures.append(future)

        # Wait for all items to be flushed
        await asyncio.gather(*futures)
        print(f"\n  ✓ All 100 items flushed in {flush_count} batches")

        # Stop batcher
        await batcher.stop()

        # Verify
        count = await client.points.count(COLLECTION)
        print(f"  ✓ Collection has {count} points")

        # ── Default config batcher ───────────────────────────
        print("\n=== Default config batcher ===")
        default_batcher = SmartBatcher(flush_callback)
        await default_batcher.start()

        for i in range(50):
            vector = [random.gauss(0, 1) for _ in range(DIM)]
            future = await default_batcher.add(
                COLLECTION,
                1000 + i,
                vector,
                {"extra": True},
            )
            futures.append(future)

        await default_batcher.stop(flush_remaining=True)

        count = await client.points.count(COLLECTION)
        print(f"  ✓ Collection now has {count} points total")

        # Cleanup
        await client.collections.delete(COLLECTION)
        print(f"\n✓ Cleaned up collection '{COLLECTION}'")


if __name__ == "__main__":
    asyncio.run(main())
