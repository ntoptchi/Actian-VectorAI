############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Connection Pool — multiple gRPC channels for high throughput.

Demonstrates:
  - ConnectionPool with pool_size > 1
  - Async context manager usage
  - Pool statistics and health checks

The ConnectionPool round-robins requests across multiple gRPC
channels to maximize throughput under high concurrency.

Usage::

    python examples/20_connection_pool.py
"""

from __future__ import annotations

import asyncio
import random
import time

from actian_vectorai import (
    ConnectionPool,
    Distance,
    PointStruct,
    PoolConfig,
    VectorAIClient,
    VectorParams,
)

SERVER = "localhost:50051"
COLLECTION = "pool_demo"
DIM = 32
fmt = "\n=== {:50} ==="


async def pool_demo() -> None:
    """Demonstrate ConnectionPool (async API)."""

    # ── Connection pool ─────────────────────────────────
    print(fmt.format("ConnectionPool (pool_size=4)"))
    config = PoolConfig(pool_size=4)
    pool = ConnectionPool(SERVER, config=config)
    try:
        await pool.connect()
        print(f"  Pool created with {pool.size} channels")
        print(f"  Address: {pool.address}")
        print(f"  Connected: {pool.is_connected}")

        # Pool provides channels via get_channel()
        channel = pool.get_channel()
        print(f"  Got channel: {type(channel).__name__}")

        # Health check
        healthy = await pool.health_check()
        print(f"  Health check: {'healthy' if healthy else 'unhealthy'}")

        # Pool stats
        stats = pool.get_stats()
        print(f"  Pool stats: {stats}")
    finally:
        await pool.close()
        print("  ✓ Pool closed")

    # ── Async context manager ───────────────────────────
    print(fmt.format("ConnectionPool as async context manager"))
    async with ConnectionPool(SERVER, config=PoolConfig(pool_size=2)) as pool:
        print(f"  Connected: {pool.is_connected}, size={pool.size}")
        channel = pool.get_channel()
        print(f"  Got channel: {type(channel).__name__}")
    print("  ✓ Auto-closed on exit")

    # ── PoolConfig options ──────────────────────────────
    print(fmt.format("PoolConfig options"))
    config = PoolConfig(
        pool_size=8,
        max_message_length=256 * 1024 * 1024,
        keepalive_time_ms=15_000,
        connect_timeout=10.0,
    )
    print(f"  pool_size={config.pool_size}")
    print(f"  max_message_length={config.max_message_length}")
    print(f"  keepalive_time_ms={config.keepalive_time_ms}")
    print(f"  connect_timeout={config.connect_timeout}")


def main() -> None:
    random.seed(42)

    # ── Single client (baseline) ────────────────────────
    print(fmt.format("Single client (pool_size=1)"))
    with VectorAIClient(SERVER) as client:
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
            )
            for i in range(1, 201)
        ]
        client.points.upsert(COLLECTION, points)
        print(f"  ✓ Inserted {len(points)} points")

        # Sequential searches
        t0 = time.perf_counter()
        for _ in range(50):
            client.points.search(
                COLLECTION,
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                limit=10,
            )
        dt = time.perf_counter() - t0
        print(f"  50 sequential searches: {dt:.3f}s ({50 / dt:.0f} ops/s)")

    # Run async pool demo
    asyncio.run(pool_demo())

    # Cleanup
    with VectorAIClient(SERVER) as client:
        client.collections.delete(COLLECTION)
    print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
