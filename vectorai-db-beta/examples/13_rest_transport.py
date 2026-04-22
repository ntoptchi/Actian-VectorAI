############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""REST Transport — using the HTTP/REST API directly.

While the default transport is gRPC, ``RESTTransport`` provides an
HTTP-based alternative using httpx.  Useful for:
  - Environments where gRPC is blocked (proxies, edge networks)
  - Debugging with browser/curl
  - Lightweight integrations

Covers all RESTTransport methods:
  - health_check, collections_list, collections_create, collections_get,
    collections_delete, collections_exists, collections_update
  - points_upsert, points_get, points_delete, points_search,
    points_query, points_count
  - points_set_payload, points_overwrite_payload,
    points_delete_payload, points_clear_payload
  - points_update_vectors

Usage::

    python examples/13_rest_transport.py

.. note::
   Requires the VectorAI server to expose port 50052 for REST.
"""

from __future__ import annotations

import asyncio
import random

from actian_vectorai.transport.rest import RESTTransport

REST_URL = "http://localhost:50052"
COLLECTION = "rest_demo"
DIM = 16


async def main() -> None:
    random.seed(42)

    async with RESTTransport(base_url=REST_URL) as rest:
        # ── Health check ────────────────────────────────────
        health = await rest.health_check()
        print(f"✓ REST health: {health}")

        # ── Collection lifecycle ────────────────────────────
        if await rest.collections_exists(COLLECTION):
            await rest.collections_delete(COLLECTION)

        await rest.collections_create(
            COLLECTION,
            config={"vectors": {"size": DIM, "distance": "Cosine"}},
        )
        print(f"✓ Created '{COLLECTION}'")

        names = await rest.collections_list()
        print(f"  Collections: {names}")

        info = await rest.collections_get(COLLECTION)
        print(f"  Info: status={info.get('status', 'unknown')}")

        # ── Points: upsert ──────────────────────────────────
        points = [
            {
                "id": i,
                "vector": [random.gauss(0, 1) for _ in range(DIM)],
                "payload": {"color": ["red", "blue", "green"][i % 3]},
            }
            for i in range(1, 21)
        ]
        result = await rest.points_upsert(COLLECTION, points)
        print(f"✓ Upserted {len(points)} points: {result}")

        # ── Points: get ─────────────────────────────────────
        retrieved = await rest.points_get(COLLECTION, ids=[1, 2, 3])
        print(f"  Retrieved {len(retrieved)} points")

        # ── Points: search ──────────────────────────────────
        qv = [random.gauss(0, 1) for _ in range(DIM)]
        results = await rest.points_search(COLLECTION, vector=qv, limit=3)
        print(f"  Search top-3: {[(r.get('id'), round(r.get('score', 0), 4)) for r in results]}")

        # ── Points: query ───────────────────────────────────
        results = await rest.points_query(COLLECTION, query={"query": qv, "limit": 3})
        print(f"  Query top-3: {[(r.get('id'), round(r.get('score', 0), 4)) for r in results]}")

        # ── Points: count ───────────────────────────────────
        count = await rest.points_count(COLLECTION)
        print(f"  Count: {count}")

        # ── Payload operations ──────────────────────────────
        await rest.points_set_payload(COLLECTION, payload={"tag": "new"}, ids=[1, 2])
        print("  ✓ set_payload on [1, 2]")

        await rest.points_overwrite_payload(COLLECTION, payload={"tag": "overwritten"}, ids=[1])
        print("  ✓ overwrite_payload on [1]")

        await rest.points_delete_payload(COLLECTION, keys=["tag"], ids=[2])
        print("  ✓ delete_payload on [2]")

        await rest.points_clear_payload(COLLECTION, ids=[1])
        print("  ✓ clear_payload on [1]")

        # ── Update vectors ──────────────────────────────────
        new_vec = [random.gauss(0, 1) for _ in range(DIM)]
        await rest.points_update_vectors(
            COLLECTION,
            points=[{"id": 1, "vector": new_vec}],
        )
        print("  ✓ update_vectors on [1]")

        # ── Delete points ───────────────────────────────────
        await rest.points_delete(COLLECTION, ids=[1, 2])
        print("  ✓ Deleted points [1, 2]")

        count = await rest.points_count(COLLECTION)
        print(f"  Count after delete: {count}")

        # ── Cleanup ─────────────────────────────────────────
        await rest.collections_delete(COLLECTION)
        print(f"\n✓ Cleaned up '{COLLECTION}'")


if __name__ == "__main__":
    asyncio.run(main())
