"""End-to-end pipeline.

``analyze_window`` is the only function the API / dashboard needs to call. It
takes a baseline window plus a "current" reading and returns either ``None``
(no anomaly) or a fully-populated ``AnomalyReport``.

``stream_window`` is a convenience for the demo script: it walks a list of
readings, maintains a rolling baseline, and yields one report per detected
anomaly.
"""

from __future__ import annotations

from collections import deque
from typing import Iterable, Iterator

from actian_vectorai import VectorAIClient

from ..config import get_settings
from ..db.sensors import upsert_readings
from ..schemas import AnomalyReport, SensorReading
from .classify import classify
from .detect import BaselineStats, detect
from .retrieve import retrieve


def analyze(
    client: VectorAIClient,
    reading: SensorReading,
    baseline: BaselineStats,
) -> AnomalyReport | None:
    """Run detect -> classify -> retrieve. Return ``None`` if nominal."""
    anomaly = detect(reading, baseline)
    if anomaly is None:
        return None

    matches = classify(client, anomaly)
    guidance = retrieve(client, matches)

    return AnomalyReport(
        anomaly=anomaly,
        matches=matches,
        guidance=guidance,
    )


def stream_window(
    client: VectorAIClient,
    readings: Iterable[SensorReading],
    *,
    window_size: int = 30,
    persist_readings: bool = True,
) -> Iterator[AnomalyReport]:
    """Walk a stream of readings, yielding one report per anomaly.

    The first ``window_size`` readings are used to seed the baseline and are
    never themselves classified -- mirrors how the live system would behave.
    """
    cfg = get_settings()  # noqa: F841 (keeps settings warm for embedders)

    window: deque[SensorReading] = deque(maxlen=window_size)
    pending_persist: list[SensorReading] = []

    for reading in readings:
        if persist_readings:
            pending_persist.append(reading)
            if len(pending_persist) >= 32:
                upsert_readings(client, pending_persist)
                pending_persist = []

        if len(window) < window_size:
            window.append(reading)
            continue

        baseline = BaselineStats.from_window(list(window))
        report = analyze(client, reading, baseline)

        window.append(reading)

        if report is not None:
            yield report

    if persist_readings and pending_persist:
        upsert_readings(client, pending_persist)
