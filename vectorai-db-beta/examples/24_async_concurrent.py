############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Async Concurrency — parallel operations with asyncio.

Demonstrates:
  - AsyncVectorAIClient usage
  - Concurrent searches with asyncio.gather
  - Parallel collection operations
  - Async context manager
  - High-throughput async ingestion

Async is essential for web servers (FastAPI, aiohttp) and
high-throughput data pipelines.

Usage::

    python examples/24_async_concurrent.py
"""

from __future__ import annotations

import asyncio
import random
import time

from actian_vectorai import (
    AsyncVectorAIClient,
    Distance,
    PointStruct,
    VectorParams,
)

SERVER = "localhost:50051"
COLLECTION = "async_demo"
DIM = 32
fmt = "\n=== {:50} ==="


async def main() -> None:
    random.seed(42)

    # ── Async context manager ───────────────────────────
    print(fmt.format("AsyncVectorAIClient — context manager"))
    async with AsyncVectorAIClient(SERVER) as client:
        # Setup
        if await client.collections.exists(COLLECTION):
            await client.collections.delete(COLLECTION)
        await client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )

        # ── Async upsert ───────────────────────────────
        print(fmt.format("Async upsert — 500 points"))
        points = [
            PointStruct(
                id=i,
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={"group": i % 10},
            )
            for i in range(1, 501)
        ]
        # Upload in batches concurrently
        batch_size = 100
        batches = [points[i : i + batch_size] for i in range(0, len(points), batch_size)]
        t0 = time.perf_counter()
        await asyncio.gather(*[client.points.upsert(COLLECTION, batch) for batch in batches])
        dt = time.perf_counter() - t0
        print(f"  ✓ {len(points)} points in {dt:.3f}s ({len(points) / dt:.0f} pts/s)")

        # ── Concurrent searches ─────────────────────────
        print(fmt.format("asyncio.gather — 50 parallel searches"))
        queries = [[random.gauss(0, 1) for _ in range(DIM)] for _ in range(50)]
        t0 = time.perf_counter()
        results = await asyncio.gather(
            *[client.points.search(COLLECTION, vector=q, limit=10) for q in queries]
        )
        dt = time.perf_counter() - t0
        print(f"  ✓ {len(results)} searches in {dt:.3f}s ({len(results) / dt:.0f} qps)")
        print(f"  First query top-3: {[r.id for r in results[0][:3]]}")

        # ── Concurrent mixed operations ─────────────────
        print(fmt.format("Mixed concurrent operations"))
        t0 = time.perf_counter()
        search_task = client.points.search(
            COLLECTION,
            vector=queries[0],
            limit=5,
        )
        count_task = client.points.count(COLLECTION, exact=True)
        get_task = client.points.get(COLLECTION, ids=[1, 2, 3, 4, 5])
        info_task = client.collections.get_info(COLLECTION)

        search_res, count_res, get_res, info_res = await asyncio.gather(
            search_task,
            count_task,
            get_task,
            info_task,
        )
        dt = time.perf_counter() - t0
        print(f"  ✓ 4 operations in {dt:.3f}s")
        print(f"    Search:  {len(search_res)} results")
        print(f"    Count:   {count_res} points")
        print(f"    Get:     {len(get_res)} points")
        print(f"    Info:    status={info_res.status}")

        # ── Batch search comparison ─────────────────────
        print(fmt.format("search_batch vs asyncio.gather"))

        # Method 1: search_batch (server-side batching)
        t0 = time.perf_counter()
        batch_results = await client.points.search_batch(
            COLLECTION,
            searches=[{"vector": q, "limit": 5} for q in queries[:20]],
        )
        dt_batch = time.perf_counter() - t0

        # Method 2: asyncio.gather (client-side concurrency)
        t0 = time.perf_counter()
        gather_results = await asyncio.gather(
            *[client.points.search(COLLECTION, vector=q, limit=5) for q in queries[:20]]
        )
        dt_gather = time.perf_counter() - t0

        print(f"  search_batch:    {dt_batch:.3f}s (20 queries)")
        print(f"  asyncio.gather:  {dt_gather:.3f}s (20 queries)")

        # Cleanup
        await client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
