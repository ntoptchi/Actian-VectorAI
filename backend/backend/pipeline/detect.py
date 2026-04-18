"""Anomaly detection.

Rolling baseline -> per-sensor z-score -> aggregate severity bucket.

The baseline is a simple statistical summary (mean / std per sensor) computed
over a window of recent readings -- "the past day/week" in production, the
last N samples in this scaffold. Anything outside ``z_threshold`` standard
deviations on at least one sensor counts as an anomaly.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from ..config import SENSOR_ORDER, get_settings
from ..schemas import AnomalyEvent, SensorDeviation, SensorReading, Severity


@dataclass(frozen=True)
class BaselineStats:
    """Per-sensor mean and std over a recent window."""

    means: dict[str, float]
    stds: dict[str, float]

    @classmethod
    def from_window(
        cls,
        readings: list[SensorReading],
        sensor_order: tuple[str, ...] = SENSOR_ORDER,
    ) -> "BaselineStats":
        if not readings:
            raise ValueError("Cannot build a baseline from zero readings.")

        means: dict[str, float] = {}
        stds: dict[str, float] = {}
        for sensor in sensor_order:
            samples = [r.values.get(sensor, 0.0) for r in readings]
            mean = statistics.fmean(samples)
            std = statistics.pstdev(samples) if len(samples) > 1 else 0.0
            means[sensor] = mean
            stds[sensor] = std if std > 1e-9 else 1e-6
        return cls(means=means, stds=stds)


def _classify_severity(max_abs_z: float, z_threshold: float) -> Severity:
    """Map the worst per-sensor z-score onto the dashboard's severity vocabulary."""
    if max_abs_z >= z_threshold * 2:
        return "Critical"
    if max_abs_z >= z_threshold:
        return "Elevated"
    return "Watching"


def _summary(deviations: list[SensorDeviation]) -> str:
    """Short natural-language summary used as the classifier query."""
    worst = max(deviations, key=lambda d: abs(d.z_score))
    direction = "high" if worst.z_score > 0 else "low"
    return (
        f"Abnormally {direction} {worst.sensor} reading: "
        f"{worst.value:.2f} vs expected {worst.expected_mean:.2f} "
        f"(+/- {worst.expected_std:.2f}), z={worst.z_score:.2f}."
    )


def detect(
    reading: SensorReading,
    baseline: BaselineStats,
    *,
    z_threshold: float | None = None,
    sensor_order: tuple[str, ...] = SENSOR_ORDER,
) -> AnomalyEvent | None:
    """Return an ``AnomalyEvent`` if ``reading`` breaches the baseline."""
    threshold = z_threshold if z_threshold is not None else get_settings().z_threshold

    deviations: list[SensorDeviation] = []
    max_abs_z = 0.0
    for sensor in sensor_order:
        value = reading.values.get(sensor, 0.0)
        mean = baseline.means.get(sensor, 0.0)
        std = baseline.stds.get(sensor, 1e-6)
        z = (value - mean) / std if std > 0 else 0.0
        if math.isnan(z) or math.isinf(z):
            z = 0.0
        deviations.append(
            SensorDeviation(
                sensor=sensor,
                value=value,
                expected_mean=mean,
                expected_std=std,
                z_score=z,
            )
        )
        max_abs_z = max(max_abs_z, abs(z))

    if max_abs_z < threshold:
        return None

    severity = _classify_severity(max_abs_z, threshold)
    return AnomalyEvent(
        rig_id=reading.rig_id,
        asset_id=reading.asset_id,
        ts=reading.ts,
        severity=severity,
        summary=_summary(deviations),
        deviations=deviations,
        reading=reading,
    )
