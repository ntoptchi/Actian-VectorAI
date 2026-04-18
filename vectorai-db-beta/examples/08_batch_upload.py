############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Batch Upload — efficient bulk ingestion with upload_points().

Demonstrates:
  - upload_points() with automatic batching and retry
  - Performance comparison: small vs large batch sizes
  - Using SmartBatcher for advanced batching control
  - Throughput measurement

Usage::

    python examples/08_batch_upload.py
"""

from __future__ import annotations

import random
import time

from actian_vectorai import (
    Distance,
    PointStruct,
    VectorAIClient,
    VectorParams,
)

SERVER = "localhost:50051"
COLLECTION = "batch_demo"
DIM = 64
NUM_POINTS = 5000
fmt = "\n=== {:50} ==="


def generate_points(n: int, dim: int) -> list[PointStruct]:
    """Generate random points with metadata."""
    return [
        PointStruct(
            id=i,
            vector=[random.gauss(0, 1) for _ in range(dim)],
            payload={
                "batch": i // 100,
                "value": random.random(),
            },
        )
        for i in range(1, n + 1)
    ]


def main() -> None:
    random.seed(42)

    with VectorAIClient(SERVER) as client:
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)
        client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )

        points = generate_points(NUM_POINTS, DIM)
        print(f"Generated {len(points)} points ({DIM}d vectors)")

        # ── upload_points() with default batch size ─────────
        print(fmt.format("upload_points (batch_size=256)"))
        t0 = time.perf_counter()
        total = client.upload_points(COLLECTION, points, batch_size=256)
        elapsed = time.perf_counter() - t0
        throughput = total / elapsed
        print(f"  ✓ Uploaded {total} points in {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.0f} points/sec")

        # Reset for next test
        client.collections.delete(COLLECTION)
        client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )

        # ── upload_points() with larger batch size ──────────
        print(fmt.format("upload_points (batch_size=1000)"))
        t0 = time.perf_counter()
        total = client.upload_points(COLLECTION, points, batch_size=1000)
        elapsed = time.perf_counter() - t0
        throughput = total / elapsed
        print(f"  ✓ Uploaded {total} points in {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.0f} points/sec")

        # ── Verify ──────────────────────────────────────────
        print(fmt.format("Verify"))
        count = client.points.count(COLLECTION)
        print(f"  Total points in collection: {count}")

        # Quick search to verify data
        query = [random.gauss(0, 1) for _ in range(DIM)]
        results = client.points.search(COLLECTION, vector=query, limit=3)
        print(f"  Search returned {len(results)} results")

        # Cleanup
        client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
