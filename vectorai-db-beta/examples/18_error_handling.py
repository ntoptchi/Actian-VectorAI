############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Error Handling — graceful exception management.

Demonstrates:
  - Typed exception hierarchy
  - CollectionNotFoundError
  - CollectionExistsError
  - DimensionMismatchError
  - VectorAIError base class
  - is_retryable() + get_retry_delay() helpers
  - PEP 678 __notes__ on exceptions

Robust error handling is mandatory for production deployments.

Usage::

    python examples/18_error_handling.py
"""

from __future__ import annotations

import random

from actian_vectorai import (
    CollectionExistsError,
    CollectionNotFoundError,
    DimensionMismatchError,
    Distance,
    ServerError,
    UnimplementedError,
    VectorAIClient,
    VectorAIError,
    VectorParams,
    get_retry_delay,
    is_retryable,
)
from actian_vectorai.exceptions import ValidationError

SERVER = "localhost:50051"
COLLECTION = "error_demo"
DIM = 8
fmt = "\n=== {:50} ==="


def main() -> None:
    random.seed(42)

    with VectorAIClient(SERVER) as client:
        # ── Collection not found ────────────────────────────
        print(fmt.format("CollectionNotFoundError"))
        try:
            client.points.search("nonexistent_collection", vector=[0.0] * DIM, limit=5)
        except CollectionNotFoundError as e:
            print(f"  Caught: {type(e).__name__}: {e}")
            print(
                f"  Notes: {e.__notes__}"
                if hasattr(e, "__notes__") and e.__notes__
                else "  (no notes)"
            )

        # ── Collection already exists ───────────────────────
        print(fmt.format("CollectionExistsError"))
        # Use recreate() to ensure collection exists cleanly
        client.collections.recreate(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )
        # Demonstrate how to check before creating (avoids server error)
        if client.collections.exists(COLLECTION):
            print(f"  Collection '{COLLECTION}' already exists — would raise CollectionExistsError")
            print("  Use exists() check or get_or_create() to avoid this error")
        else:
            client.collections.create(
                COLLECTION,
                vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
            )

        # ── get_or_create (idempotent alternative) ──────────
        print(fmt.format("get_or_create() — no error"))
        info = client.collections.get_or_create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )
        print(f"  Collection '{COLLECTION}' exists (idempotent)")

        # ── Base class catch-all ────────────────────────────
        print(fmt.format("VectorAIError catch-all"))
        try:
            client.points.search("nonexistent", vector=[0.0] * DIM, limit=5)
        except VectorAIError as e:
            print(f"  Caught: {type(e).__name__}: {e}")
            print(f"  Is retryable? {is_retryable(e)}")
            delay = get_retry_delay(e)
            print(f"  Retry delay: {delay}s" if delay else "  No retry delay")

        # ── Retry logic pattern ─────────────────────────────
        print(fmt.format("Retry pattern"))
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                # Intentionally fail with bad collection name
                client.points.search("does_not_exist", vector=[0.0] * DIM, limit=1)
                break
            except VectorAIError as e:
                if is_retryable(e) and attempt < max_retries:
                    delay = get_retry_delay(e) or 1.0
                    print(f"  Attempt {attempt} failed (retryable), waiting {delay}s…")
                    import time

                    time.sleep(delay)
                else:
                    print(
                        f"  Attempt {attempt}: {type(e).__name__} (not retryable or last attempt)"
                    )
                    break

        # ── Exception hierarchy ─────────────────────────────
        print(fmt.format("Exception hierarchy"))
        hierarchy = [
            VectorAIError,
            CollectionNotFoundError,
            CollectionExistsError,
            DimensionMismatchError,
            ValidationError,
            ServerError,
            UnimplementedError,
        ]
        for exc_cls in hierarchy:
            bases = " → ".join(c.__name__ for c in exc_cls.__mro__[1:3])
            print(f"  {exc_cls.__name__} ← {bases}")

        # Cleanup
        client.collections.delete(COLLECTION)
        print("\n✓ Cleaned up")


if __name__ == "__main__":
    main()
