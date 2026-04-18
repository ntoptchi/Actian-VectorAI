############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Universal Query API — single endpoint for all retrieval modes.

Demonstrates:
  - query()       — nearest-neighbor via query vector
  - query_batch() — multiple queries in one call
  - PrefetchQuery — multi-stage retrieval (prefetch → re-rank)

The query() method is a unified interface for flexible retrieval.

Usage::

    python examples/09_query_api.py
"""

from __future__ import annotations

import random

from actian_vectorai import (
    Distance,
    PointStruct,
    VectorAIClient,
    VectorParams,
)
from actian_vectorai.exceptions import UnimplementedError, VectorAIError
from actian_vectorai.models.enums import Fusion
from actian_vectorai.models.points import PrefetchQuery

SERVER = "localhost:50051"
COLLECTION = "query_api_demo"
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

        # Insert data with category payload
        points = [
            PointStruct(
                id=i,
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={
                    "category": ["A", "B", "C"][i % 3],
                    "price": round(random.uniform(10, 100), 2),
                },
            )
            for i in range(1, 51)
        ]
        client.points.upsert(COLLECTION, points)
        print(f"✓ Inserted {len(points)} points")

        # ── Nearest-neighbor query ──────────────────────────
        print(fmt.format("query() — nearest neighbor"))
        query_vec = [random.gauss(0, 1) for _ in range(DIM)]
        results = client.points.query(COLLECTION, query=query_vec, limit=5)
        for r in results:
            print(f"  id={r.id:3d}  score={r.score:.4f}")

        # ── Query with filter ───────────────────────────────
        print(fmt.format("query() — with filter"))
        from actian_vectorai import Field, FilterBuilder

        f = FilterBuilder().must(Field("category").eq("A")).build()
        results = client.points.query(
            COLLECTION,
            query=query_vec,
            filter=f,
            limit=5,
        )
        for r in results:
            print(f"  id={r.id:3d}  score={r.score:.4f}  cat={r.payload['category']}")

        # ── Query with payload/vector selectors ─────────────
        print(fmt.format("query() — with_payload & with_vectors"))
        from actian_vectorai.models.points import WithPayloadSelector

        results = client.points.query(
            COLLECTION,
            query=query_vec,
            limit=3,
            with_payload=WithPayloadSelector(include=["price"]),
            with_vectors=True,
        )
        for r in results:
            print(f"  id={r.id:3d}  payload={r.payload}  has_vector={r.vectors is not None}")

        # ── Batch queries ───────────────────────────────────
        print(fmt.format("query_batch() — 3 queries at once"))
        queries = [
            {"query": [random.gauss(0, 1) for _ in range(DIM)], "limit": 3},
            {"query": [random.gauss(0, 1) for _ in range(DIM)], "limit": 3},
            {"query": [random.gauss(0, 1) for _ in range(DIM)], "limit": 3},
        ]
        batch_results = client.points.query_batch(COLLECTION, queries)
        for i, results in enumerate(batch_results):
            ids = [r.id for r in results]
            print(f"  Query {i + 1}: {ids}")

        # ── Prefetch query (multi-stage) ────────────────────
        print(fmt.format("query() — with prefetch (multi-stage)"))
        prefetch = [
            PrefetchQuery(
                query=query_vec,
                limit=20,  # Broad first pass
            ),
        ]
        try:
            results = client.points.query(
                COLLECTION,
                query={"fusion": Fusion.RRF},  # merge prefetch results via RRF
                prefetch=prefetch,
                limit=5,
            )
            for r in results:
                print(f"  id={r.id:3d}  score={r.score:.4f}")
        except UnimplementedError as e:
            print(f"  ⚠ Prefetch not supported on this server: {e}")
        except VectorAIError as e:
            print(f"  ⚠ Prefetch query failed: {e}")

        # ── Query with score threshold ──────────────────────
        print(fmt.format("query() — score_threshold + offset"))
        results = client.points.query(
            COLLECTION,
            query=query_vec,
            score_threshold=0.0,
            offset=2,
            limit=3,
        )
        print(f"  Results (offset=2, threshold=0.0): {len(results)}")
        for r in results:
            print(f"  id={r.id:3d}  score={r.score:.4f}")

        # Cleanup
        client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
