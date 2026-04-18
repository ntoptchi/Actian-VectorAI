############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Payload Management — set, overwrite, delete, clear payload fields.

Demonstrates fine-grained payload (metadata) operations:
  - Set payload on specific points
  - Overwrite entire payload
  - Delete specific keys
  - Clear all payload
  - Field indexes for faster filtering

Usage::

    python examples/07_payload_management.py
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
from actian_vectorai.exceptions import UnimplementedError

SERVER = "localhost:50051"
COLLECTION = "payload_demo"
DIM = 16
fmt = "\n=== {:50} ==="


def main() -> None:  # noqa: C901
    random.seed(42)

    with VectorAIClient(SERVER) as client:
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)
        client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )

        # Insert with initial payload
        points = [
            PointStruct(
                id=i,
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={"name": f"item_{i}", "price": i * 10.0, "tags": ["initial"]},
            )
            for i in range(1, 6)
        ]
        client.points.upsert(COLLECTION, points)
        print("✓ Inserted 5 points with payload")

        # ── Set payload (merge) ─────────────────────────────
        print(fmt.format("Set payload (merge new fields)"))
        try:
            client.points.set_payload(
                COLLECTION,
                payload={"color": "red", "featured": True},
                ids=[1, 2],
            )
            retrieved = client.points.get(COLLECTION, ids=[1, 2])
            for p in retrieved:
                print(f"  id={p.id}  payload={p.payload}")
        except UnimplementedError as e:
            print(f"  ⚠ set_payload not implemented on server: {e}")

        # ── Overwrite payload (replace entirely) ────────────
        print(fmt.format("Overwrite payload (replace)"))
        try:
            client.points.overwrite_payload(
                COLLECTION,
                payload={"name": "overwritten", "new_field": 42},
                ids=[3],
            )
            retrieved = client.points.get(COLLECTION, ids=[3])
            for p in retrieved:
                print(f"  id={p.id}  payload={p.payload}")
                # Original fields (price, tags) should be gone
        except UnimplementedError as e:
            print(f"  ⚠ overwrite_payload not implemented on server: {e}")

        # ── Delete specific keys ────────────────────────────
        print(fmt.format("Delete payload keys"))
        try:
            client.points.delete_payload(
                COLLECTION,
                keys=["tags"],
                ids=[1, 2],
                strict=True,
            )
            retrieved = client.points.get(COLLECTION, ids=[1])
            for p in retrieved:
                print(f"  id={p.id}  payload={p.payload}")
                # 'tags' key should be gone
        except UnimplementedError as e:
            print(f"  ⚠ delete_payload not implemented on server: {e}")

        # ── Set payload by filter ───────────────────────────
        print(fmt.format("Set payload by filter"))
        try:
            client.points.set_payload(
                COLLECTION,
                payload={"discount": 0.10},
                filter=FilterBuilder().must(Field("price").gte(30.0)).build(),
            )
            all_pts = client.points.get(COLLECTION, ids=[1, 2, 3, 4, 5])
            for p in all_pts:
                discount = p.payload.get("discount", "none")
                print(f"  id={p.id}  price={p.payload.get('price', '?')}  discount={discount}")
        except UnimplementedError as e:
            print(f"  ⚠ set_payload (by filter) not implemented on server: {e}")

        # ── Clear all payload ───────────────────────────────
        print(fmt.format("Clear all payload"))
        try:
            client.points.clear_payload(COLLECTION, ids=[5])
            retrieved = client.points.get(COLLECTION, ids=[5])
            for p in retrieved:
                print(f"  id={p.id}  payload={p.payload}")
                # Should be empty/None
        except UnimplementedError as e:
            print(f"  ⚠ clear_payload not implemented on server: {e}")

        # ── Create field index ──────────────────────────────
        # NOTE: Dynamic create_field_index is not yet supported on the server.
        # Declare indexes via PayloadSchema at collection creation time instead.
        # Example (when server supports it):
        #   client.points.create_field_index(COLLECTION, "price", FieldType.FieldTypeFloat)
        #   client.points.create_field_index(COLLECTION, "name", FieldType.FieldTypeKeyword)
        print(fmt.format("Create field index"))
        print("  ⚠ Skipped — dynamic create_field_index not yet supported on server")
        print("    Declare indexes via PayloadSchema at collection creation time")

        # Cleanup
        client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
