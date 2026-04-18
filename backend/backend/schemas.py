"""Pydantic models that flow through the RigSense pipeline.

Every input and output crossing a module boundary is one of these models. That
keeps subagents honest and makes it easy to JSON-serialize an ``AnomalyReport``
straight to the React dashboard later.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Severity = Literal["Critical", "Elevated", "Watching"]


class SensorReading(BaseModel):
    """One multi-sensor sample from a single asset at a single timestamp."""

    model_config = ConfigDict(frozen=True)

    rig_id: str
    asset_id: str
    ts: datetime
    values: dict[str, float] = Field(
        description="Sensor name -> reading. Keys must be a subset of SENSOR_ORDER.",
    )

    def vector(self, sensor_order: tuple[str, ...]) -> list[float]:
        """Project ``values`` onto the canonical sensor order."""
        return [float(self.values.get(name, 0.0)) for name in sensor_order]


class PastIncident(BaseModel):
    """A historic failure event used as a retrieval anchor."""

    incident_id: str
    incident_name: str
    failure_type: str
    severity: Severity
    description: str
    signature: dict[str, float] = Field(
        description="Sensor reading snapshot at the time of the incident.",
    )
    related_manual_ids: list[str] = Field(default_factory=list)


class RepairManualChunk(BaseModel):
    """A chunk of text from a repair manual, retrievable on its own."""

    chunk_id: str
    manual_id: str
    manual_name: str
    text: str


class RepairManual(BaseModel):
    """A repair manual, retrievable as a whole before drilling into chunks."""

    manual_id: str
    manual_name: str
    summary: str
    chunks: list[RepairManualChunk] = Field(default_factory=list)


class SensorDeviation(BaseModel):
    """Per-sensor breakdown of a detected anomaly."""

    sensor: str
    value: float
    expected_mean: float
    expected_std: float
    z_score: float


class AnomalyEvent(BaseModel):
    """Output of the detect step. The thing classify / retrieve operate on."""

    rig_id: str
    asset_id: str
    ts: datetime
    severity: Severity
    summary: str = Field(
        description="Short natural-language summary used as the classifier query.",
    )
    deviations: list[SensorDeviation]
    reading: SensorReading


class IncidentMatch(BaseModel):
    """A past incident scored against the current anomaly."""

    incident: PastIncident
    text_similarity: float
    numeric_similarity: float
    score: float = Field(description="Hybrid score actually used for ranking.")


class GuidanceHit(BaseModel):
    """A retrieved manual + its single best chunk for the current anomaly."""

    manual: RepairManual
    best_chunk: RepairManualChunk
    incident_similarity: float
    manual_similarity: float
    chunk_similarity: float
    score: float = Field(description="incident_sim * manual_sim * chunk_sim.")


class AnomalyReport(BaseModel):
    """End-to-end pipeline output. One report per detected anomaly."""

    anomaly: AnomalyEvent
    matches: list[IncidentMatch]
    guidance: list[GuidanceHit]
