############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Named Vectors — multi-vector collections.

Demonstrates creating a collection with multiple named vector spaces
(e.g., text embeddings + image embeddings) and searching each
independently.

Usage::

    python examples/29_named_vectors.py
"""

from __future__ import annotations

import random
import uuid

from actian_vectorai import (
    Distance,
    PointStruct,
    VectorAIClient,
    VectorParams,
)

SERVER = "localhost:50051"
COLLECTION = "named_vectors_demo"
TEXT_DIM = 64
IMAGE_DIM = 32


def main() -> None:
    random.seed(42)

    with VectorAIClient(SERVER) as client:
        # Setup
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)

        # ── Create with named vectors ────────────────────────
        print("=== Create collection with named vectors ===")
        client.collections.create(
            COLLECTION,
            vectors_config={
                "text": VectorParams(size=TEXT_DIM, distance=Distance.Cosine),
                "image": VectorParams(size=IMAGE_DIM, distance=Distance.Euclid),
            },
        )
        print(
            f"  ✓ Created '{COLLECTION}' with 'text' ({TEXT_DIM}d) and 'image' ({IMAGE_DIM}d) vectors"
        )

        # ── Insert multi-vector points ───────────────────────
        print("\n=== Insert multi-vector points ===")
        products = [
            ("laptop", "electronics"),
            ("novel", "books"),
            ("jacket", "clothing"),
            ("phone", "electronics"),
            ("textbook", "books"),
            ("sneakers", "clothing"),
            ("tablet", "electronics"),
            ("cookbook", "books"),
            ("hat", "clothing"),
            ("monitor", "electronics"),
        ]
        points = []
        for name, category in products:
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector={
                        "text": [random.gauss(0, 1) for _ in range(TEXT_DIM)],
                        "image": [random.gauss(0, 1) for _ in range(IMAGE_DIM)],
                    },
                    payload={"name": name, "category": category},
                )
            )
        client.points.upsert(COLLECTION, points)
        print(f"  ✓ Inserted {len(points)} products with text + image vectors")

        # ── Search by text vector ────────────────────────────
        print("\n=== Search by text vector ===")
        text_query = [random.gauss(0, 1) for _ in range(TEXT_DIM)]
        results = client.points.search(
            COLLECTION,
            vector=text_query,
            using="text",
            limit=5,
        )
        print("  Top 5 by text similarity:")
        for r in results:
            print(f"    {r.payload['name']:12s} ({r.payload['category']})  score={r.score:.4f}")

        # ── Search by image vector ───────────────────────────
        print("\n=== Search by image vector ===")
        image_query = [random.gauss(0, 1) for _ in range(IMAGE_DIM)]
        results = client.points.search(
            COLLECTION,
            vector=image_query,
            using="image",
            limit=5,
        )
        print("  Top 5 by image similarity:")
        for r in results:
            print(f"    {r.payload['name']:12s} ({r.payload['category']})  score={r.score:.4f}")

        # ── Get points with specific vectors ─────────────────
        print("\n=== Get with vectors ===")
        results = client.points.get(
            COLLECTION,
            ids=[points[0].id],
            with_payload=True,
            with_vectors=True,
        )
        if results:
            p = results[0]
            print(f"  Point {p.id}:")
            print(f"    payload: {p.payload}")
            if hasattr(p, "vector") and isinstance(p.vector, dict):
                for vname, vec in p.vector.items():
                    print(f"    {vname} vector: [{vec[0]:.4f}, {vec[1]:.4f}, ...] (dim={len(vec)})")

        count = client.points.count(COLLECTION)
        print(f"\n  Total points: {count}")

        # Cleanup
        client.collections.delete(COLLECTION)
        print(f"\n✓ Cleaned up collection '{COLLECTION}'")


if __name__ == "__main__":
    main()
