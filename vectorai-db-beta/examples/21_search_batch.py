############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Search Batch — parallel multi-query search for efficiency.

Demonstrates:
  - search_batch()  — multiple search vectors in one RPC call
  - query_batch()   — multiple universal queries in one RPC

Batched search avoids per-request overhead and is significantly
faster than issuing individual search calls in a loop.

Usage::

    python examples/21_search_batch.py
"""

from __future__ import annotations

import random

from actian_vectorai import (
    Distance,
    Field,
    FilterBuilder,
    PointStruct,
    VectorAIClient,
    VectorParams,
)

SERVER = "localhost:50051"
COLLECTION = "search_batch_demo"
DIM = 32
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

        # Insert data
        points = [
            PointStruct(
                id=i,
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={"category": ["tech", "science", "art"][i % 3]},
            )
            for i in range(1, 101)
        ]
        client.points.upsert(COLLECTION, points)
        print(f"✓ Inserted {len(points)} points")

        # ── search_batch — 5 searches in one call ───────────
        print(fmt.format("search_batch() — 5 queries"))
        searches = [
            {
                "vector": [random.gauss(0, 1) for _ in range(DIM)],
                "limit": 3,
            }
            for _ in range(5)
        ]
        batch_results = client.points.search_batch(COLLECTION, searches)
        for i, results in enumerate(batch_results):
            ids = [r.id for r in results]
            scores = [round(r.score, 4) for r in results]
            print(f"  Search {i + 1}: ids={ids}  scores={scores}")

        # ── search_batch with filters ────────────────────────
        print(fmt.format("search_batch() — with per-query filters"))
        f_tech = FilterBuilder().must(Field("category").eq("tech")).build()
        f_art = FilterBuilder().must(Field("category").eq("art")).build()

        searches_filtered = [
            {
                "vector": [random.gauss(0, 1) for _ in range(DIM)],
                "limit": 3,
                "filter": f_tech,
            },
            {
                "vector": [random.gauss(0, 1) for _ in range(DIM)],
                "limit": 3,
                "filter": f_art,
            },
        ]
        batch_results = client.points.search_batch(COLLECTION, searches_filtered)
        for i, results in enumerate(batch_results):
            cats = [r.payload.get("category", "?") for r in results]
            print(f"  Search {i + 1}: categories={cats}")

        # ── query_batch — multiple universal queries ─────────
        print(fmt.format("query_batch() — 3 universal queries"))
        queries = [
            {"query": [random.gauss(0, 1) for _ in range(DIM)], "limit": 3},
            {"query": [random.gauss(0, 1) for _ in range(DIM)], "limit": 5},
            {
                "query": [random.gauss(0, 1) for _ in range(DIM)],
                "limit": 3,
                "with_payload": False,
            },
        ]
        batch_results = client.points.query_batch(COLLECTION, queries)
        for i, results in enumerate(batch_results):
            ids = [r.id for r in results]
            print(f"  Query {i + 1}: {len(results)} results, ids={ids}")

        # Cleanup
        client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
