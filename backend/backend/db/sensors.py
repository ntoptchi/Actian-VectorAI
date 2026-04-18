"""Sensor-readings collection helpers."""

from __future__ import annotations

import uuid

from actian_vectorai import (
    Field as VField,
    FilterBuilder,
    PointStruct,
    VectorAIClient,
)

from ..config import SENSOR_ORDER, get_settings
from ..schemas import SensorReading


def _to_point(reading: SensorReading) -> PointStruct:
    return PointStruct(
        id=str(uuid.uuid4()),
        vector=reading.vector(SENSOR_ORDER),
        payload={
            "rig_id": reading.rig_id,
            "asset_id": reading.asset_id,
            "ts": reading.ts.isoformat(),
            "values": reading.values,
        },
    )


def upsert_readings(
    client: VectorAIClient,
    readings: list[SensorReading],
) -> int:
    """Persist a batch of sensor readings. Returns the count written."""
    if not readings:
        return 0
    points = [_to_point(r) for r in readings]
    client.points.upsert(get_settings().sensor_readings_collection, points)
    return len(points)


def search_similar_readings(
    client: VectorAIClient,
    reading: SensorReading,
    *,
    limit: int = 10,
    asset_id: str | None = None,
) -> list[dict]:
    """Find historical readings closest to ``reading`` (by L2 distance)."""
    cfg = get_settings()
    builder = FilterBuilder()
    if asset_id is not None:
        builder = builder.must(VField("asset_id").eq(asset_id))
    f = builder.build()

    results = client.points.search(
        cfg.sensor_readings_collection,
        vector=reading.vector(SENSOR_ORDER),
        limit=limit,
        filter=f,
    )
    return [
        {"id": r.id, "score": r.score, "payload": r.payload}
        for r in results
    ]
