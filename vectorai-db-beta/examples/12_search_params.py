############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Search Parameters — tuning search quality and controlling output.

Demonstrates:
  - SearchParams: hnsw_ef, exact, quantization, indexed_only
  - WithPayloadSelector: include / exclude specific payload fields
  - WithVectorsSelector: request vectors back with results
  - score_threshold: filter by minimum score
  - offset: pagination via offset
  - using: search on a named vector

Usage::

    python examples/12_search_params.py
"""

from __future__ import annotations

import random

from actian_vectorai import (
    Distance,
    PointStruct,
    VectorAIClient,
    VectorParams,
)
from actian_vectorai.models.points import (
    QuantizationSearchParams,
    SearchParams,
    WithPayloadSelector,
)

SERVER = "localhost:50051"
COLLECTION = "search_params_demo"
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
                payload={
                    "title": f"Document {i}",
                    "category": ["tech", "science", "art"][i % 3],
                    "content": f"Content of document {i} with some text",
                    "rating": round(random.uniform(1, 5), 1),
                },
            )
            for i in range(1, 101)
        ]
        client.points.upsert(COLLECTION, points)
        print(f"✓ Inserted {len(points)} points")

        qv = [random.gauss(0, 1) for _ in range(DIM)]

        # ── 1. Default search (no params) ───────────────────
        print(fmt.format("Default search (approximate ANN)"))
        results = client.points.search(COLLECTION, vector=qv, limit=3)
        for r in results:
            print(f"  id={r.id:3d}  score={r.score:.4f}")

        # ── 2. SearchParams: hnsw_ef for quality tuning ─────
        print(fmt.format("SearchParams(hnsw_ef=128) — higher recall"))
        params = SearchParams(hnsw_ef=128)
        results = client.points.search(COLLECTION, vector=qv, limit=3, params=params)
        for r in results:
            print(f"  id={r.id:3d}  score={r.score:.4f}")

        # ── 3. SearchParams: exact=True for brute-force ─────
        print(fmt.format("SearchParams(exact=True) — brute force"))
        params = SearchParams(exact=True)
        results = client.points.search(COLLECTION, vector=qv, limit=3, params=params)
        for r in results:
            print(f"  id={r.id:3d}  score={r.score:.4f}")

        # ── 4. SearchParams: quantization control ────────────
        print(fmt.format("SearchParams(quantization) — trade speed/quality"))
        params = SearchParams(
            quantization=QuantizationSearchParams(
                ignore=False,
                rescore=True,
                oversampling=2.0,
            )
        )
        results = client.points.search(COLLECTION, vector=qv, limit=3, params=params)
        for r in results:
            print(f"  id={r.id:3d}  score={r.score:.4f}")

        # ── 5. WithPayloadSelector: include only some fields ─
        print(fmt.format("with_payload — include only 'title'"))
        results = client.points.search(
            COLLECTION,
            vector=qv,
            limit=3,
            with_payload=WithPayloadSelector(include=["title"]),
        )
        for r in results:
            print(f"  id={r.id:3d}  payload={r.payload}")

        # ── 6. WithPayloadSelector: exclude fields ───────────
        print(fmt.format("with_payload — exclude 'content'"))
        results = client.points.search(
            COLLECTION,
            vector=qv,
            limit=3,
            with_payload=WithPayloadSelector(exclude=["content"]),
        )
        for r in results:
            keys = list(r.payload.keys()) if r.payload else []
            print(f"  id={r.id:3d}  payload keys={keys}")

        # ── 7. with_payload=False — no payload ───────────────
        print(fmt.format("with_payload=False — no payload returned"))
        results = client.points.search(
            COLLECTION,
            vector=qv,
            limit=3,
            with_payload=False,
        )
        for r in results:
            print(f"  id={r.id:3d}  score={r.score:.4f}  payload={r.payload}")

        # ── 8. WithVectorsSelector — request vectors back ────
        print(fmt.format("with_vectors=True — get vectors back"))
        results = client.points.search(
            COLLECTION,
            vector=qv,
            limit=2,
            with_vectors=True,
            with_payload=False,
        )
        for r in results:
            vec_len = len(r.vectors) if r.vectors else 0
            print(f"  id={r.id:3d}  score={r.score:.4f}  vector_dim={vec_len}")

        # ── 9. score_threshold — minimum score cutoff ────────
        print(fmt.format("score_threshold — minimum score"))
        results = client.points.search(
            COLLECTION,
            vector=qv,
            limit=100,
            score_threshold=0.5,
        )
        print(f"  Points with score >= 0.5: {len(results)}")

        # ── 10. offset — pagination ─────────────────────────
        print(fmt.format("offset — paginate through results"))
        page1 = client.points.search(COLLECTION, vector=qv, limit=3, offset=0)
        page2 = client.points.search(COLLECTION, vector=qv, limit=3, offset=3)
        print(f"  Page 1 ids: {[r.id for r in page1]}")
        print(f"  Page 2 ids: {[r.id for r in page2]}")

        # Cleanup
        client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
