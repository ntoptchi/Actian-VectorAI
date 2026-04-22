############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Quantization — memory-efficient vector storage.

Vector quantization compresses float32 vectors to reduce memory usage,
trading a small amount of search accuracy for significant memory savings.

Three quantization types are supported:

  ScalarQuantization   — float32 → int8 (4× memory reduction)
  ProductQuantization  — configurable compression (4×–64×)
  BinaryQuantization   — float32 → 1 bit (32× memory reduction)

All types support optional rescoring: the top candidates from the
compressed index are re-ranked using the original float32 vectors,
recovering most of the lost accuracy.

Usage::

    python examples/34_quantization.py
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
from actian_vectorai.exceptions import VectorAIError
from actian_vectorai.models.collections import (
    BinaryQuantization,
    ProductQuantization,
    QuantizationConfig,
    ScalarQuantization,
)
from actian_vectorai.models.enums import CompressionRatio, QuantizationType
from actian_vectorai.models.points import QuantizationSearchParams, SearchParams

SERVER = "localhost:50051"
DIM = 128
N_POINTS = 200


def make_points(n: int, dim: int) -> list[PointStruct]:
    random.seed(42)
    return [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=[random.gauss(0, 1) for _ in range(dim)],
            payload={"label": f"item_{i}"},
        )
        for i in range(n)
    ]


def run_search(client: VectorAIClient, collection: str, dim: int, rescore: bool) -> None:
    """Run a search with optional quantization rescoring."""
    query = [random.gauss(0, 1) for _ in range(dim)]
    search_params = (
        SearchParams(quantization=QuantizationSearchParams(rescore=rescore, oversampling=2.0))
        if rescore
        else None
    )
    results = client.points.search(
        collection,
        vector=query,
        limit=5,
        params=search_params,
    )
    label = "with rescore" if rescore else "no rescore"
    if results:
        print(f"  Top result ({label}): id={results[0].id}  score={results[0].score:.4f}")
    else:
        print(f"  ({label}): no results returned")


def demo_quantization(
    client: VectorAIClient,
    name: str,
    collection: str,
    quantization_config: QuantizationConfig,
    description: str,
) -> None:
    print(f"\n--- {name}: {description} ---")

    if client.collections.exists(collection):
        client.collections.delete(collection)

    try:
        client.collections.create(
            collection,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
            quantization_config=quantization_config,
        )

        points = make_points(N_POINTS, DIM)
        client.points.upsert(collection, points)
        print(f"  ✓ Inserted {N_POINTS} points with {name}")

        info = client.collections.get_info(collection)
        q = info.config.params.quantization_config if info.config else None
        if q:
            print("  Quantization confirmed in collection config")

        run_search(client, collection, DIM, rescore=False)
        run_search(client, collection, DIM, rescore=True)

        client.collections.delete(collection)

    except VectorAIError as e:
        print(f"  ⚠ Not supported on this server: {e}")
        if client.collections.exists(collection):
            client.collections.delete(collection)


def main() -> None:
    random.seed(0)

    with VectorAIClient(SERVER) as client:
        info = client.health_check()
        print(f"Connected to {info['title']} v{info['version']}")

        print(f"\nDimension: {DIM}   Points: {N_POINTS}")
        print(f"Uncompressed memory per vector: {DIM * 4} bytes (float32)")

        # ── Scalar Quantization (float32 → int8) ─────────────────────────
        demo_quantization(
            client,
            name="ScalarQuantization",
            collection="quant_scalar_demo",
            quantization_config=QuantizationConfig(
                scalar=ScalarQuantization(
                    type=QuantizationType.Int8,
                    quantile=0.99,  # clip outliers at 99th percentile
                    always_ram=True,  # keep quantized index in RAM
                )
            ),
            description=f"float32 → int8 (~4× reduction, ~{DIM} bytes/vector)",
        )

        # ── Product Quantization (configurable compression) ───────────────
        demo_quantization(
            client,
            name="ProductQuantization",
            collection="quant_product_demo",
            quantization_config=QuantizationConfig(
                product=ProductQuantization(
                    compression=CompressionRatio.x4,  # 4× compression
                    always_ram=True,
                )
            ),
            description=f"Subspace quantization, 4× compression (~{DIM} bytes/vector)",
        )

        # ── Binary Quantization (maximum compression) ─────────────────────
        demo_quantization(
            client,
            name="BinaryQuantization",
            collection="quant_binary_demo",
            quantization_config=QuantizationConfig(binary=BinaryQuantization(always_ram=True)),
            description=f"float32 → 1 bit (~32× reduction, ~{DIM // 8} bytes/vector)",
        )

        print("\n=== Memory comparison (per vector) ===")
        print(f"  float32 (no quantization): {DIM * 4:>6} bytes")
        print(f"  ScalarQuantization int8  : {DIM * 1:>6} bytes  (4×  reduction)")
        print(f"  ProductQuantization x4   : {DIM * 1:>6} bytes  (4×  reduction)")
        print(f"  BinaryQuantization       : {DIM // 8:>6} bytes  (32× reduction)")
        print("\n✓ Done")


if __name__ == "__main__":
    main()
