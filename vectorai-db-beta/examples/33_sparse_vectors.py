############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Sparse Vectors — keyword/BM25-style retrieval with sparse vector search.

Sparse vectors represent text as high-dimensional term-frequency vectors
where most values are zero.  They are ideal for keyword matching and
complement dense vectors in hybrid retrieval pipelines.

Demonstrates:
  - Creating a collection with a sparse vector space
  - Upserting points with sparse vectors (indices + values)
  - Searching using a sparse query vector
  - Combined dense + sparse named-vector collection for hybrid retrieval

Usage::

    python examples/33_sparse_vectors.py
"""

from __future__ import annotations

import random
import uuid

from actian_vectorai import (
    Distance,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorAIClient,
    VectorParams,
)
from actian_vectorai.exceptions import VectorAIError

SERVER = "localhost:50051"
VOCAB_SIZE = 1000  # simulated vocabulary size (sparse vector dimension)
DENSE_DIM = 64  # dense embedding dimension for hybrid example


# ── Helpers ───────────────────────────────────────────────────────────────────


def sparse_from_text(text: str, vocab_size: int = VOCAB_SIZE) -> SparseVector:
    """Simulate a BM25-style sparse vector from text.

    In production, replace with a real sparse encoder such as:
      - SPLADE (neural sparse)
      - BM25 (TF-IDF term weighting)
      - FastText bag-of-words
    """
    rng = random.Random(hash(text) % (2**32))
    # Pick 5-15 random non-zero term indices
    n_terms = rng.randint(5, 15)
    indices = sorted(rng.sample(range(vocab_size), n_terms))
    values = [round(rng.uniform(0.1, 2.0), 4) for _ in indices]
    return SparseVector(indices=indices, values=values)


def dense_embed(text: str, dim: int = DENSE_DIM) -> list[float]:
    """Simulate a dense embedding."""
    rng = random.Random(hash(text + "dense") % (2**32))
    return [rng.gauss(0, 1) for _ in range(dim)]


# ── Documents ─────────────────────────────────────────────────────────────────

DOCS = [
    "vector database similarity search approximate nearest neighbor",
    "keyword search BM25 term frequency inverse document frequency",
    "machine learning neural network embedding representation",
    "database indexing performance optimization query execution",
    "natural language processing tokenization vocabulary sparse",
    "cosine similarity dot product euclidean distance metric",
    "retrieval augmented generation large language model context",
    "payload metadata filtering exact match range query",
]


def main() -> None:
    random.seed(42)

    with VectorAIClient(SERVER) as client:
        # ── Part 1: Sparse-only collection ───────────────────────────────
        print("=== Part 1: Sparse-only collection ===")

        sparse_collection = "sparse_demo"
        if client.collections.exists(sparse_collection):
            client.collections.delete(sparse_collection)

        try:
            client.collections.create(
                sparse_collection,
                sparse_vectors_config={"sparse": SparseVectorParams()},
            )
            print(f"✓ Created sparse collection '{sparse_collection}'")

            # Upsert points with sparse vectors
            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector={"sparse": sparse_from_text(doc)},
                    payload={"text": doc, "doc_id": i},
                )
                for i, doc in enumerate(DOCS)
            ]
            client.points.upsert(sparse_collection, points)
            print(f"✓ Inserted {len(points)} sparse vectors")

            # Search with a sparse query
            query_text = "keyword search term frequency retrieval"
            query_sparse = sparse_from_text(query_text)
            print(f'\nSparse query: "{query_text}"')
            print(f"  Non-zero terms: {len(query_sparse.indices)}")

            results = client.points.search(
                sparse_collection,
                vector=query_sparse.values,
                vector_name="sparse",
                sparse_indices=query_sparse.indices,
                limit=3,
                with_payload=True,
            )
            print("Top 3 results:")
            for r in results:
                print(f"  score={r.score:.4f}  text={r.payload['text'][:60]}")

            client.collections.delete(sparse_collection)

        except VectorAIError as e:
            print(f"  ⚠ Sparse-only collection not supported on this server: {e}")
            if client.collections.exists(sparse_collection):
                client.collections.delete(sparse_collection)

        # ── Part 2: Hybrid collection (dense + sparse named vectors) ─────
        print("\n=== Part 2: Hybrid collection (dense + sparse) ===")

        hybrid_collection = "hybrid_demo"
        if client.collections.exists(hybrid_collection):
            client.collections.delete(hybrid_collection)

        try:
            client.collections.create(
                hybrid_collection,
                vectors_config={
                    "dense": VectorParams(size=DENSE_DIM, distance=Distance.Cosine),
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(),
                },
            )
            print(f"✓ Created hybrid collection '{hybrid_collection}'")

            # Upsert points with both dense and sparse vectors
            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector={
                        "dense": dense_embed(doc),
                        "sparse": sparse_from_text(doc),
                    },
                    payload={"text": doc},
                )
                for doc in DOCS
            ]
            client.points.upsert(hybrid_collection, points)
            print(f"✓ Inserted {len(points)} points with dense + sparse vectors")

            # Dense search — use vector_name to target the "dense" space
            query_text = "approximate nearest neighbor search"
            dense_results = client.points.search(
                hybrid_collection,
                vector=dense_embed(query_text),
                vector_name="dense",
                limit=3,
                with_payload=True,
            )
            print(f'\nDense search for "{query_text}":')
            for r in dense_results:
                print(f"  score={r.score:.4f}  {r.payload['text'][:60]}")

            # Sparse search — use vector_name + sparse_indices/values
            sparse_q = sparse_from_text(query_text)
            sparse_results = client.points.search(
                hybrid_collection,
                vector=sparse_q.values,
                vector_name="sparse",
                sparse_indices=sparse_q.indices,
                limit=3,
                with_payload=True,
            )
            print(f'\nSparse search for "{query_text}":')
            for r in sparse_results:
                print(f"  score={r.score:.4f}  {r.payload['text'][:60]}")

            client.collections.delete(hybrid_collection)

        except VectorAIError as e:
            print(f"  ⚠ Hybrid collection not supported on this server: {e}")
            if client.collections.exists(hybrid_collection):
                client.collections.delete(hybrid_collection)

        print("\n✓ Done")


if __name__ == "__main__":
    main()
