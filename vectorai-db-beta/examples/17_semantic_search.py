############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Semantic Search — simulated embedding search with payload filtering.

Demonstrates:
  - Simulated embedding generation
  - ANN search with top-K
  - Combined vector + payload filter (pre-filter / post-filter)
  - Score threshold filtering
  - Hybrid approach: semantic similarity + metadata constraints

This mirrors a real-world RAG (Retrieval-Augmented Generation) pipeline
where you encode a query, search for similar documents, and filter
by metadata.

Usage::

    python examples/17_semantic_search.py
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
COLLECTION = "semantic_demo"
DIM = 64
fmt = "\n=== {:50} ==="

# Simulated document corpus
DOCUMENTS = [
    {
        "id": 1,
        "text": "Python is a popular programming language",
        "topic": "programming",
        "year": 2024,
    },
    {
        "id": 2,
        "text": "Machine learning transforms data into insights",
        "topic": "ml",
        "year": 2024,
    },
    {
        "id": 3,
        "text": "Vector databases enable semantic search",
        "topic": "databases",
        "year": 2024,
    },
    {"id": 4, "text": "Neural networks learn hierarchical features", "topic": "ml", "year": 2023},
    {
        "id": 5,
        "text": "SQL is the language of relational databases",
        "topic": "databases",
        "year": 2020,
    },
    {"id": 6, "text": "Deep learning requires large datasets", "topic": "ml", "year": 2023},
    {"id": 7, "text": "Graph databases model relationships", "topic": "databases", "year": 2022},
    {"id": 8, "text": "Transformers revolutionized NLP", "topic": "ml", "year": 2023},
    {
        "id": 9,
        "text": "Rust is a memory-safe systems language",
        "topic": "programming",
        "year": 2024,
    },
    {"id": 10, "text": "Embeddings represent meaning as vectors", "topic": "ml", "year": 2024},
]


def fake_embed(text: str, dim: int = DIM) -> list[float]:
    """Deterministic pseudo-embedding based on text hash."""
    random.seed(hash(text) % (2**32))
    return [random.gauss(0, 1) for _ in range(dim)]


def main() -> None:
    with VectorAIClient(SERVER) as client:
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)
        client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )

        # Field indexes for filtered search
        # NOTE: Dynamic create_field_index not yet supported on the server.
        # Filtered search still works without explicit indexes.

        # Embed and insert documents
        points = [
            PointStruct(
                id=doc["id"],
                vector=fake_embed(doc["text"]),
                payload={"text": doc["text"], "topic": doc["topic"], "year": doc["year"]},
            )
            for doc in DOCUMENTS
        ]
        client.points.upsert(COLLECTION, points)
        print(f"✓ Indexed {len(DOCUMENTS)} documents")

        # ── Pure semantic search ────────────────────────────
        print(fmt.format("Semantic: 'how do vector databases work?'"))
        query_vec = fake_embed("how do vector databases work?")
        results = client.points.search(
            COLLECTION,
            vector=query_vec,
            limit=5,
            with_payload=True,
        )
        for r in results:
            print(f"  score={r.score:.4f} | {r.payload['text']}")

        # ── Filtered semantic search ────────────────────────
        print(fmt.format("Semantic + filter: topic='ml'"))
        f = FilterBuilder().must(Field("topic").eq("ml")).build()
        results = client.points.search(
            COLLECTION,
            vector=query_vec,
            filter=f,
            limit=5,
        )
        for r in results:
            print(f"  score={r.score:.4f} | [{r.payload['topic']}] {r.payload['text']}")

        # ── Range-filtered semantic search ──────────────────
        print(fmt.format("Semantic + filter: year >= 2023"))
        f = FilterBuilder().must(Field("year").gte(2023)).build()
        results = client.points.search(
            COLLECTION,
            vector=query_vec,
            filter=f,
            limit=5,
        )
        for r in results:
            print(f"  score={r.score:.4f} | [{r.payload['year']}] {r.payload['text']}")

        # ── Score threshold ─────────────────────────────────
        print(fmt.format("Semantic with score_threshold=0.5"))
        results = client.points.search(
            COLLECTION,
            vector=query_vec,
            limit=10,
            score_threshold=0.5,
        )
        print(f"  {len(results)} results above threshold")
        for r in results:
            print(f"  score={r.score:.4f} | {r.payload['text']}")

        # ── Combined: topic filter ─────────────────────────
        print(fmt.format("Filter by topic: ml"))
        f = FilterBuilder().must(Field("topic").eq("ml")).build()
        results = client.points.search(
            COLLECTION,
            vector=query_vec,
            filter=f,
            limit=5,
        )
        for r in results:
            print(f"  score={r.score:.4f} | {r.payload['text']}")

        # Cleanup
        client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
