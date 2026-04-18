"""Generate a synthetic sensor stream for the demo.

The stream is structured so the rolling-window detector has something
interesting to find: a long nominal baseline, a short Critical compressor
event, a recovery, then a slow-burn humidity drift.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from ..schemas import SensorReading


_RIG_ID = "rig-north-atlas-07"
_NOMINAL = {
    "vibration": 6.5,
    "bearing_temp": 61.0,
    "pressure": 1.0,
    "rpm": 3300.0,
    "lubricant_pressure": 3.0,
    "humidity": 42.0,
}
_NOISE = {
    "vibration": 0.4,
    "bearing_temp": 0.6,
    "pressure": 0.05,
    "rpm": 12.0,
    "lubricant_pressure": 0.05,
    "humidity": 0.4,
}


def _nominal(rng: random.Random, asset_id: str, ts: datetime) -> SensorReading:
    values = {
        sensor: _NOMINAL[sensor] + rng.gauss(0.0, _NOISE[sensor])
        for sensor in _NOMINAL
    }
    return SensorReading(
        rig_id=_RIG_ID,
        asset_id=asset_id,
        ts=ts,
        values=values,
    )


def _spike(
    rng: random.Random,
    asset_id: str,
    ts: datetime,
    overrides: dict[str, float],
) -> SensorReading:
    values = {
        sensor: _NOMINAL[sensor] + rng.gauss(0.0, _NOISE[sensor])
        for sensor in _NOMINAL
    }
    values.update(overrides)
    return SensorReading(
        rig_id=_RIG_ID,
        asset_id=asset_id,
        ts=ts,
        values=values,
    )


def generate_sample_stream(
    *,
    asset_id: str = "compressor-03",
    seed: int = 42,
    baseline_n: int = 60,
    event_n: int = 8,
    recovery_n: int = 30,
    drift_n: int = 20,
) -> list[SensorReading]:
    """Return a deterministic list of readings for the demo."""
    rng = random.Random(seed)
    start = datetime(2026, 4, 17, 21, 0, tzinfo=timezone.utc)
    step = timedelta(seconds=15)

    stream: list[SensorReading] = []
    t = start

    for _ in range(baseline_n):
        stream.append(_nominal(rng, asset_id, t))
        t += step

    for i in range(event_n):
        progress = (i + 1) / event_n
        stream.append(
            _spike(
                rng,
                asset_id,
                t,
                overrides={
                    "vibration": 9.0 + 9.0 * progress,
                    "bearing_temp": 65.0 + 18.0 * progress,
                    "lubricant_pressure": 3.0 - 1.4 * progress,
                },
            )
        )
        t += step

    for i in range(recovery_n):
        decay = math.exp(-i / 8.0)
        stream.append(
            _spike(
                rng,
                asset_id,
                t,
                overrides={
                    "vibration": _NOMINAL["vibration"] + 9.0 * decay,
                    "bearing_temp": _NOMINAL["bearing_temp"] + 18.0 * decay,
                    "lubricant_pressure": _NOMINAL["lubricant_pressure"]
                    - 1.4 * decay,
                },
            )
        )
        t += step

    for i in range(drift_n):
        progress = (i + 1) / drift_n
        stream.append(
            _spike(
                rng,
                "tank-04",
                t,
                overrides={
                    "humidity": _NOMINAL["humidity"] + 25.0 * progress,
                    "vibration": 0.4 + rng.gauss(0.0, 0.1),
                    "rpm": 0.0,
                    "lubricant_pressure": 0.0,
                },
            )
        )
        t += step

    return stream
