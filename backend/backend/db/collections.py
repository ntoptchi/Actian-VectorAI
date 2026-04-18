"""Collection bootstrap.

One call -- ``bootstrap_collections(client)`` -- creates the four RigSense
collections idempotently. Existing collections are dropped and recreated so
re-running the script after a schema tweak is a no-op concern.
"""

from __future__ import annotations

from actian_vectorai import Distance, VectorAIClient, VectorParams

from ..config import Settings, get_settings


def _recreate(
    client: VectorAIClient,
    name: str,
    *,
    size: int,
    distance: Distance,
) -> None:
    if client.collections.exists(name):
        client.collections.delete(name)
    client.collections.create(
        name,
        vectors_config=VectorParams(size=size, distance=distance),
    )


def bootstrap_collections(
    client: VectorAIClient,
    settings: Settings | None = None,
) -> list[str]:
    """Create all four collections, returning their names in fixed order."""
    cfg = settings or get_settings()

    _recreate(
        client,
        cfg.sensor_readings_collection,
        size=cfg.sensor_dim,
        distance=Distance.Euclid,
    )
    _recreate(
        client,
        cfg.past_incidents_collection,
        size=cfg.embedding_dim,
        distance=Distance.Cosine,
    )
    _recreate(
        client,
        cfg.manuals_collection,
        size=cfg.embedding_dim,
        distance=Distance.Cosine,
    )
    _recreate(
        client,
        cfg.manual_chunks_collection,
        size=cfg.embedding_dim,
        distance=Distance.Cosine,
    )

    return [
        cfg.sensor_readings_collection,
        cfg.past_incidents_collection,
        cfg.manuals_collection,
        cfg.manual_chunks_collection,
    ]
