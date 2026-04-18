############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Hello World — minimal getting-started example.

This is the simplest possible example showing how to:
  1. Connect to Actian VectorAI DB
  2. Create a collection
  3. Insert vectors
  4. Search for similar vectors
  5. Clean up

Usage::

    python examples/01_hello_world.py
"""

from __future__ import annotations

import uuid

from actian_vectorai import (
    Distance,
    PointStruct,
    VectorAIClient,
    VectorParams,
)

SERVER = "localhost:50051"


def main() -> None:
    with VectorAIClient(SERVER) as client:
        # 1. Health check
        info = client.health_check()
        print(f"Connected to {info['title']} v{info['version']}")

        collection = "hello_world"

        # 2. Create collection (128-dim cosine)
        if client.collections.exists(collection):
            client.collections.delete(collection)

        client.collections.create(
            collection,
            vectors_config=VectorParams(size=128, distance=Distance.Cosine),
        )
        print(f"✓ Created collection '{collection}'")

        # 3. Insert points (using UUID string IDs)
        import random

        random.seed(42)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=[random.gauss(0, 1) for _ in range(128)],
                payload={"color": ["red", "blue", "green"][i % 3]},
            )
            for i in range(10)
        ]
        client.points.upsert(collection, points)
        print(f"✓ Inserted {len(points)} points")

        # 4. Search
        query = [random.gauss(0, 1) for _ in range(128)]
        results = client.points.search(collection, vector=query, limit=3)
        print("\nTop 3 search results:")
        for r in results:
            print(f"  id={r.id}  score={r.score:.4f}  payload={r.payload}")

        # 5. Clean up
        client.collections.delete(collection)
        print(f"\n✓ Deleted collection '{collection}'")


if __name__ == "__main__":
    main()
