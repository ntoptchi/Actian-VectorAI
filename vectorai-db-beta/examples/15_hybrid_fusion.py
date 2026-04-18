############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Hybrid / Fusion Search — combine dense + sparse retrieval.

Demonstrates:
  - Client-side Reciprocal Rank Fusion (RRF)
  - Distribution-Based Score Fusion (DBSF)
  - Multi-query fusion with different weights
  - Combining dense search with keyword filter for hybrid effect

True hybrid search combines dense vectors (semantic) with sparse
vectors (BM25/TF-IDF) and fuses the results.

Usage::

    python examples/15_hybrid_fusion.py
"""

from __future__ import annotations

import random

from actian_vectorai import (
    Distance,
    PointStruct,
    VectorAIClient,
    VectorParams,
    distribution_based_score_fusion,
    reciprocal_rank_fusion,
)

SERVER = "localhost:50051"
COLLECTION = "hybrid_demo"
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

        # Insert 100 points with "terms" payload (simulated keywords)
        points = [
            PointStruct(
                id=i,
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={
                    "text": f"Document {i} about {['AI', 'ML', 'NLP', 'CV'][i % 4]}",
                    "terms": ["AI", "ML", "NLP", "CV"][i % 4],
                },
            )
            for i in range(1, 101)
        ]
        client.points.upsert(COLLECTION, points)
        print(f"✓ Inserted {len(points)} points")

        # Two different query vectors (simulating dense + "sparse")
        query_dense = [random.gauss(0, 1) for _ in range(DIM)]
        query_semantic = [random.gauss(0, 1) for _ in range(DIM)]

        # ── Run two separate searches ───────────────────────
        print(fmt.format("Dense search #1"))
        results_a = client.points.search(
            COLLECTION,
            vector=query_dense,
            limit=20,
        )
        for r in results_a[:5]:
            print(f"  id={r.id:3d}  score={r.score:.4f}")

        print(fmt.format("Dense search #2 (different vector)"))
        results_b = client.points.search(
            COLLECTION,
            vector=query_semantic,
            limit=20,
        )
        for r in results_b[:5]:
            print(f"  id={r.id:3d}  score={r.score:.4f}")

        # ── Reciprocal Rank Fusion ──────────────────────────
        print(fmt.format("RRF fusion (k=60)"))
        fused_rrf = reciprocal_rank_fusion(
            [results_a, results_b],
            limit=10,
            ranking_constant_k=60,
        )
        for r in fused_rrf[:5]:
            print(f"  id={r.id:3d}  fused_score={r.score:.4f}")

        # ── Distribution-Based Score Fusion ─────────────────
        print(fmt.format("DBSF fusion"))
        fused_dbsf = distribution_based_score_fusion(
            [results_a, results_b],
            limit=10,
        )
        for r in fused_dbsf[:5]:
            print(f"  id={r.id:3d}  fused_score={r.score:.4f}")

        # ── Compare top-5 ──────────────────────────────────
        print(fmt.format("Comparison of top-5 IDs"))
        rrf_ids = [r.id for r in fused_rrf[:5]]
        dbsf_ids = [r.id for r in fused_dbsf[:5]]
        print(f"  RRF:  {rrf_ids}")
        print(f"  DBSF: {dbsf_ids}")
        overlap = set(rrf_ids) & set(dbsf_ids)
        print(f"  Overlap: {len(overlap)} / 5")

        # Cleanup
        client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
