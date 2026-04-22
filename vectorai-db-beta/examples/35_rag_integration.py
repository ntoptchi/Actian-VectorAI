############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""RAG Integration — Retrieval-Augmented Generation pattern.

Shows how to use VectorAI as a knowledge store for LLM applications:

  1. Ingest: chunk documents, embed text, store vectors + metadata
  2. Retrieve: search by semantic similarity, optionally filter by topic
  3. Augment: format retrieved chunks as context for an LLM prompt

This example uses random vectors to simulate embeddings so it runs
without an actual embedding model.  In production, replace the
``embed()`` stub with your real embedding function (OpenAI, HuggingFace,
Cohere, etc.).

Usage::

    python examples/35_rag_integration.py
"""

from __future__ import annotations

import asyncio
import random
import uuid

from actian_vectorai import (
    AsyncVectorAIClient,
    Distance,
    Field,
    FilterBuilder,
    PointStruct,
    VectorParams,
)

SERVER = "localhost:50051"
COLLECTION = "rag_knowledge_base"
EMBED_DIM = 128  # match your real embedding model output dimension

# ── Simulated document corpus ─────────────────────────────────────────────────

DOCUMENTS = [
    {
        "text": "VectorAI supports cosine, dot-product, and Euclidean distance metrics.",
        "source": "docs/vector_search.md",
        "page": 1,
        "topic": "vector_search",
    },
    {
        "text": "Use FilterBuilder to combine must, should, and must_not conditions.",
        "source": "docs/filtering.md",
        "page": 1,
        "topic": "filtering",
    },
    {
        "text": "The HNSW index provides approximate nearest-neighbor search with high recall.",
        "source": "docs/indexes.md",
        "page": 2,
        "topic": "vector_search",
    },
    {
        "text": "Payload fields can store arbitrary JSON metadata alongside each vector.",
        "source": "docs/payloads.md",
        "page": 1,
        "topic": "payloads",
    },
    {
        "text": "upload_points() batches large datasets automatically for high throughput.",
        "source": "docs/upload.md",
        "page": 1,
        "topic": "ingestion",
    },
    {
        "text": "SmartBatcher buffers writes and flushes when size or time limits are reached.",
        "source": "docs/batcher.md",
        "page": 1,
        "topic": "ingestion",
    },
    {
        "text": "scroll() iterates all points in a collection using a cursor-based approach.",
        "source": "docs/scroll.md",
        "page": 1,
        "topic": "retrieval",
    },
    {
        "text": "Named vectors allow one collection to hold multiple embedding spaces.",
        "source": "docs/named_vectors.md",
        "page": 1,
        "topic": "vector_search",
    },
    {
        "text": "The recommend() API finds similar points using positive/negative examples.",
        "source": "docs/recommend.md",
        "page": 1,
        "topic": "retrieval",
    },
    {
        "text": "VDE operations include optimize, flush, rebuild_index, and compact_collection.",
        "source": "docs/vde.md",
        "page": 1,
        "topic": "administration",
    },
    {
        "text": "Collection aliases enable zero-downtime index rebuilds by swapping names.",
        "source": "docs/aliases.md",
        "page": 1,
        "topic": "administration",
    },
    {
        "text": "Range filters on numeric payload fields use gte, lte, gt, lt operators.",
        "source": "docs/filtering.md",
        "page": 2,
        "topic": "filtering",
    },
    {
        "text": "Binary quantization compresses float32 vectors to 1 bit, reducing memory 32×.",
        "source": "docs/quantization.md",
        "page": 1,
        "topic": "vector_search",
    },
    {
        "text": "The query() API is the universal search entry point supporting all strategies.",
        "source": "docs/query.md",
        "page": 1,
        "topic": "retrieval",
    },
    {
        "text": "ConnectionPool manages multiple gRPC channels for high-concurrency workloads.",
        "source": "docs/connection.md",
        "page": 1,
        "topic": "administration",
    },
]


def embed(text: str) -> list[float]:
    """Simulate an embedding model.

    Replace with your real embedding call, e.g.:
        response = openai.embeddings.create(model="text-embedding-3-small", input=text)
        return response.data[0].embedding
    """
    rng = random.Random(hash(text) % (2**32))
    return [rng.gauss(0, 1) for _ in range(EMBED_DIM)]


def format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks as LLM context."""
    lines = []
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"[{i}] Source: {chunk['source']} (page {chunk['page']})")
        lines.append(f"    {chunk['text']}")
    return "\n".join(lines)


async def main() -> None:
    async with AsyncVectorAIClient(SERVER) as client:
        info = await client.health_check()
        print(f"Connected to {info['title']} v{info['version']}")

        # ── 1. Create collection ──────────────────────────────────────────
        if await client.collections.exists(COLLECTION):
            await client.collections.delete(COLLECTION)

        await client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.Cosine),
        )
        print(f"✓ Created knowledge base collection '{COLLECTION}'")

        # ── 2. Ingest: embed and store document chunks ────────────────────
        print(f"\n--- Ingesting {len(DOCUMENTS)} document chunks ---")
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embed(doc["text"]),
                payload=doc,
            )
            for doc in DOCUMENTS
        ]
        await client.upload_points(COLLECTION, points, batch_size=50)
        print(f"✓ Ingested {len(points)} chunks")

        # ── 3. Retrieve: semantic search (no filter) ──────────────────────
        print("\n--- Semantic retrieval (no filter) ---")
        query_text = "How do I speed up filtered search?"
        query_vec = embed(query_text)

        results = await client.points.search(
            COLLECTION,
            vector=query_vec,
            limit=3,
            with_payload=True,
        )
        print(f'Query: "{query_text}"')
        print("Top 3 chunks retrieved:")
        retrieved_chunks = [r.payload for r in results]
        print(format_context(retrieved_chunks))

        # ── 4. Retrieve: filtered by topic ────────────────────────────────
        print("\n--- Topic-filtered retrieval ---")
        topic_filter = FilterBuilder().must(Field("topic").eq("vector_search")).build()

        results_filtered = await client.points.search(
            COLLECTION,
            vector=embed("what distance metrics are supported?"),
            filter=topic_filter,
            limit=3,
            with_payload=True,
        )
        print('Query: "what distance metrics are supported?"')
        print("Filter: topic == 'vector_search'")
        print(f"Found {len(results_filtered)} chunks:")
        for r in results_filtered:
            print(f"  [{r.score:.4f}] {r.payload['text'][:80]}")

        # ── 5. Count chunks per topic ─────────────────────────────────────
        print("\n--- Knowledge base stats by topic ---")
        topics = set(doc["topic"] for doc in DOCUMENTS)
        for topic in sorted(topics):
            f = FilterBuilder().must(Field("topic").eq(topic)).build()
            n = await client.points.count(COLLECTION, filter=f)
            print(f"  {topic:20s}: {n} chunks")

        # ── 6. Show how context feeds into an LLM prompt ─────────────────
        print("\n--- Example LLM prompt with retrieved context ---")
        user_question = "How does VectorAI handle large-scale data ingestion?"
        top_chunks = await client.points.search(
            COLLECTION,
            vector=embed(user_question),
            limit=3,
            with_payload=True,
        )
        context = format_context([r.payload for r in top_chunks])
        prompt = (
            f"Answer the following question using only the context provided.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {user_question}\n"
            f"Answer:"
        )
        print(prompt)
        print("\n  # In production: pass `prompt` to your LLM (OpenAI, Anthropic, etc.)")

        # ── Cleanup ──────────────────────────────────────────────────────
        await client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
