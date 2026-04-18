############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Field Indexes — payload field indexing for faster filtered search.

Creating a field index on a payload key tells the server to build an
inverted index / B-tree for that field, making filtered searches
significantly faster at scale instead of scanning every vector.

Demonstrates create_field_index() with the following FieldType values:
  - FieldTypeKeyword  — exact string match, string in-set filters
  - FieldTypeInteger  — numeric equality / range filters
  - FieldTypeFloat    — floating-point range filters
  - FieldTypeBool     — true/false filters
  - FieldTypeUuid     — UUID equality / in-set filters

Usage::

    python examples/10_field_indexes.py
"""

from __future__ import annotations

import random
import uuid

from actian_vectorai import (
    Distance,
    Field,
    FilterBuilder,
    PointStruct,
    VectorAIClient,
    VectorParams,
)
from actian_vectorai.exceptions import UnimplementedError, VectorAIError
from actian_vectorai.models.enums import FieldType

SERVER = "localhost:50051"
COLLECTION = "field_index_demo"
DIM = 32

CATEGORIES = ["electronics", "clothing", "books", "furniture", "sports"]


def main() -> None:
    random.seed(42)

    with VectorAIClient(SERVER) as client:
        # ── Setup ────────────────────────────────────────────
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)

        client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Euclid),
        )
        print(f"✓ Created collection '{COLLECTION}'")

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={
                    "category": random.choice(CATEGORIES),
                    "price": round(random.uniform(5.0, 500.0), 2),
                    "in_stock": random.choice([True, False]),
                    "item_id": str(uuid.uuid4()),
                    "quantity": random.randint(0, 100),
                },
            )
            for _ in range(100)
        ]
        client.points.upsert(COLLECTION, points)
        print(f"✓ Inserted {len(points)} points")

        # ── Filtered search WITHOUT index (full scan) ────────
        print("\n--- Filtered search WITHOUT field index ---")
        f = FilterBuilder().must(Field("category").eq("electronics")).build()
        results = client.points.search(
            COLLECTION,
            vector=[random.gauss(0, 1) for _ in range(DIM)],
            filter=f,
            limit=5,
        )
        print(f"  Found {len(results)} electronics items (full scan)")

        # ── Create field indexes ─────────────────────────────
        print("\n--- Creating field indexes ---")

        indexes = [
            ("category", FieldType.FieldTypeKeyword, "keyword index for exact match"),
            ("price", FieldType.FieldTypeFloat, "float index for range queries"),
            ("in_stock", FieldType.FieldTypeBool, "bool index for true/false"),
            ("item_id", FieldType.FieldTypeUuid, "UUID index for ID lookups"),
            ("quantity", FieldType.FieldTypeInteger, "integer index for range queries"),
        ]

        for field_name, field_type, desc in indexes:
            try:
                client.points.create_field_index(
                    COLLECTION,
                    field_name=field_name,
                    field_type=field_type,
                )
                print(f"  ✓ Created {desc} on '{field_name}'")
            except UnimplementedError as e:
                print(f"  ⚠ {desc} on '{field_name}' not implemented: {e}")
            except VectorAIError as e:
                print(f"  ⚠ {desc} on '{field_name}': {type(e).__name__}")

        # ── Inspect payload schema via get_info ───────────────
        info = client.collections.get_info(COLLECTION)
        if info.payload_schema:
            print("\n--- Indexed payload schema ---")
            for field, schema in info.payload_schema.items():
                print(f"  {field}: {schema.data_type}")

        # ── Filtered searches using indexed fields ────────────
        print("\n--- Filtered searches WITH indexes (faster at scale) ---")

        # Keyword filter
        f_kw = FilterBuilder().must(Field("category").eq("electronics")).build()
        r = client.points.search(
            COLLECTION,
            vector=[random.gauss(0, 1) for _ in range(DIM)],
            filter=f_kw,
            limit=5,
        )
        print(f"  category == 'electronics': {len(r)} results")

        # Float range filter
        f_price = FilterBuilder().must(Field("price").range(gte=10.0, lte=50.0)).build()
        r = client.points.search(
            COLLECTION,
            vector=[random.gauss(0, 1) for _ in range(DIM)],
            filter=f_price,
            limit=5,
        )
        print(f"  price in [10.0, 50.0]: {len(r)} results")

        # Bool filter
        f_stock = FilterBuilder().must(Field("in_stock").eq(True)).build()
        count = client.points.count(COLLECTION, filter=f_stock)
        print(f"  in_stock == True: {count} total points")

        # Integer range filter
        f_qty = FilterBuilder().must(Field("quantity").gte(50)).build()
        r = client.points.search(
            COLLECTION,
            vector=[random.gauss(0, 1) for _ in range(DIM)],
            filter=f_qty,
            limit=5,
        )
        print(f"  quantity >= 50: {len(r)} results")

        # ── Cleanup ──────────────────────────────────────────
        client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
