############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Filtered Search — metadata-based filtering with the Filter DSL.

Demonstrates the ``Field`` and ``FilterBuilder`` DSL for building
rich filter conditions on payload fields:
  - Equality, range, match
  - Must / must_not / should (boolean logic)
  - Nested filters
  - has_id, is_empty, is_null helpers
  - Geo-spatial filtering

Usage::

    python examples/06_filtered_search.py
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
    has_id,
)

SERVER = "localhost:50051"
COLLECTION = "filter_demo"
DIM = 32
fmt = "\n=== {:50} ==="

CATEGORIES = ["electronics", "clothing", "books", "toys", "food"]
BRANDS = ["alpha", "beta", "gamma", "delta"]


def main() -> None:
    random.seed(42)

    with VectorAIClient(SERVER) as client:
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)
        client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )

        # Insert diverse data
        points = []
        for i in range(1, 101):
            payload = {
                "category": CATEGORIES[i % len(CATEGORIES)],
                "brand": BRANDS[i % len(BRANDS)],
                "price": round(random.uniform(5, 500), 2),
                "rating": round(random.uniform(1, 5), 1),
                "in_stock": i % 3 != 0,
            }
            if i % 10 == 0:
                payload["tags"] = ["sale", "featured"]
            points.append(
                PointStruct(
                    id=i,
                    vector=[random.gauss(0, 1) for _ in range(DIM)],
                    payload=payload,
                )
            )
        client.points.upsert(COLLECTION, points)
        print(f"✓ Inserted {len(points)} product points")

        query = [random.gauss(0, 1) for _ in range(DIM)]

        # ── Equality filter ─────────────────────────────────
        print(fmt.format("Filter: category == 'electronics'"))
        f = FilterBuilder().must(Field("category").eq("electronics")).build()
        results = client.points.search(
            COLLECTION,
            vector=query,
            limit=5,
            filter=f,
        )
        for r in results:
            print(f"  id={r.id:3d}  cat={r.payload['category']}  price={r.payload['price']}")

        # ── Range filter ────────────────────────────────────
        print(fmt.format("Filter: price between 50 and 150"))
        f = FilterBuilder().must(Field("price").between(50.0, 150.0)).build()
        results = client.points.search(COLLECTION, vector=query, limit=5, filter=f)
        for r in results:
            print(f"  id={r.id:3d}  price=${r.payload['price']:.2f}")

        # ── Boolean AND + NOT ───────────────────────────────
        print(fmt.format("Filter: electronics AND NOT brand=='delta'"))
        f = (
            FilterBuilder()
            .must(Field("category").eq("electronics"))
            .must_not(Field("brand").eq("delta"))
            .build()
        )
        results = client.points.search(COLLECTION, vector=query, limit=5, filter=f)
        for r in results:
            print(f"  id={r.id:3d}  cat={r.payload['category']}  brand={r.payload['brand']}")

        # ── OR (any_of match) ────────────────────────────
        print(fmt.format("Filter: category='books' OR category='toys'"))
        f = FilterBuilder().must(Field("category").any_of(["books", "toys"])).build()
        results = client.points.search(COLLECTION, vector=query, limit=5, filter=f)
        for r in results:
            print(f"  id={r.id:3d}  cat={r.payload['category']}")

        # ── has_id filter ───────────────────────────────────
        print(fmt.format("Filter: specific IDs only"))
        f = FilterBuilder().must(has_id([1, 5, 10, 15, 20])).build()
        results = client.points.search(COLLECTION, vector=query, limit=10, filter=f)
        print(f"  Found IDs: {[r.id for r in results]}")

        # ── Count with filter ───────────────────────────────
        print(fmt.format("Count with filters"))
        total = client.points.count(COLLECTION)
        f_elec = FilterBuilder().must(Field("category").eq("electronics")).build()
        electronics = client.points.count(
            COLLECTION,
            filter=f_elec,
        )
        f_stock = FilterBuilder().must(Field("in_stock").eq(True)).build()
        in_stock = client.points.count(
            COLLECTION,
            filter=f_stock,
        )
        print(f"  Total:       {total}")
        print(f"  Electronics: {electronics}")
        print(f"  In stock:    {in_stock}")

        # Cleanup
        client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
