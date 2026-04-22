############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Scroll Pagination — efficient batch iteration through large result sets.

Demonstrates scroll-based pagination for efficient point enumeration:
  - Basic scroll with pagination
  - Scroll with filters
  - Scroll with offset tracking
  - scroll_all() async generator for automatic pagination
  - Use cases: backups, batch processing, point enumeration

Key advantages over search():
  - No vector query required — iterate by insertion order or custom sort
  - Efficient for large collections — server handles internal pagination
  - No limit on total points — scroll includes all matching points
  - State machine: offset tracks current position

Usage::

    python examples/37_scroll_pagination.py
"""

from __future__ import annotations

import asyncio
import random

from actian_vectorai import (
    AsyncVectorAIClient,
    Distance,
    Field,
    FilterBuilder,
    PointStruct,
    VectorAIClient,
    VectorParams,
)

SERVER = "localhost:50051"
COLLECTION = "scroll_demo"
DIM = 32
fmt = "\n=== {:50} ==="


def make_vector() -> list[float]:
    return [random.gauss(0, 1) for _ in range(DIM)]


def main_sync() -> None:
    """Synchronous scroll examples."""
    random.seed(42)

    with VectorAIClient(SERVER) as client:
        # Setup
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)
        client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )

        # Populate with 50 points
        print(fmt.format("Populating collection with 50 points"))
        points = [
            PointStruct(
                id=i,
                vector=make_vector(),
                payload={
                    "category": ["electronics", "books", "clothing"][i % 3],
                    "price": random.randint(10, 500),
                    "in_stock": i % 2 == 0,
                },
            )
            for i in range(50)
        ]
        client.points.upsert(COLLECTION, points)
        print(f"  ✓ Inserted {len(points)} points")

        # ── Basic scroll (manual pagination) ─────────────────
        print(fmt.format("Basic scroll — manual pagination"))
        page_num = 1
        total_scrolled = 0
        offset = None
        while True:
            points_page, next_offset = client.points.scroll(
                COLLECTION, offset=offset, limit=10
            )
            print(f"  Page {page_num}: {len(points_page)} points")
            total_scrolled += len(points_page)
            if next_offset is None:
                break
            offset = next_offset
            page_num += 1
        print(f"  ✓ Total scrolled: {total_scrolled} points")

        # ── Scroll with filter ───────────────────────────────
        print(fmt.format("Scroll with filter"))
        f = FilterBuilder().must(Field("in_stock").eq(True)).build()
        in_stock_points = []
        offset = None
        while True:
            points_page, next_offset = client.points.scroll(
                COLLECTION, offset=offset, filter=f, limit=10
            )
            in_stock_points.extend(points_page)
            if next_offset is None:
                break
            offset = next_offset
        print(f"  ✓ Found {len(in_stock_points)} in-stock points")

        # ── Scroll with vectors included ──────────────────────
        print(fmt.format("Scroll with vectors"))
        points_page, _ = client.points.scroll(
            COLLECTION, with_vectors=True, limit=5
        )
        print(f"  Retrieved {len(points_page)} points with vectors")
        for p in points_page[:2]:
            print(f"    id={p.id}, vectors_dim={len(p.vectors)}")

        # ── Scroll without payload ───────────────────────────
        print(fmt.format("Scroll without payload (efficient for large points)"))
        points_page, _ = client.points.scroll(
            COLLECTION, with_payload=False, limit=5
        )
        print(f"  Retrieved {len(points_page)} point IDs")
        for p in points_page[:2]:
            print(f"    id={p.id}, has_payload={p.payload is not None}")


async def main_async() -> None:
    """Asynchronous scroll examples using async generator."""
    random.seed(42)

    async with AsyncVectorAIClient(SERVER) as client:
        # Setup (reuse collection from sync example)
        print(fmt.format("Async: Using existing collection"))

        # ── scroll_all() async generator ──────────────────────
        print(fmt.format("Async: scroll_all() — auto-pagination"))
        all_points = []
        page_count = 0
        async for points_page in client.points.scroll_all(
            COLLECTION, limit=15
        ):
            all_points.extend(points_page)
            page_count += 1
            print(f"  Page {page_count}: {len(points_page)} points")
        print(f"  ✓ Total via scroll_all: {len(all_points)} points")

        # ── scroll_all() with filter ────────────────────────
        print(fmt.format("Async: scroll_all() with filter"))
        f = FilterBuilder().must(Field("category").eq("electronics")).build()
        electronics = []
        async for points_page in client.points.scroll_all(
            COLLECTION, filter=f, limit=10
        ):
            electronics.extend(points_page)
        print(f"  ✓ Found {len(electronics)} electronics")

        # ── Parallel batch processing ───────────────────────
        print(fmt.format("Async: Process pages concurrently"))
        batch_results = []

        async def process_batch(points_batch: list) -> int:
            """Simulate async processing (e.g., re-embedding, validation)."""
            await asyncio.sleep(0.01)  # Simulate work
            return len(points_batch)

        page_count = 0
        tasks = []
        async for points_page in client.points.scroll_all(
            COLLECTION, limit=10
        ):
            # Queue batch for async processing
            task = process_batch(points_page)
            tasks.append(task)
            page_count += 1

        # Wait for all batches to complete
        results = await asyncio.gather(*tasks)
        processed = sum(results)
        print(f"  Processed {page_count} pages ({processed} points total)")


def main() -> None:
    """Run both sync and async examples."""
    print("\n" + "=" * 60)
    print("SCROLL PAGINATION EXAMPLES")
    print("=" * 60)

    # Sync examples
    main_sync()

    # Async examples
    print("\n" + "─" * 60)
    print("ASYNC EXAMPLES")
    print("─" * 60)
    asyncio.run(main_async())

    print("\n" + "=" * 60)
    print("✓ All examples completed successfully")
    print("=" * 60)


if __name__ == "__main__":
    main()
