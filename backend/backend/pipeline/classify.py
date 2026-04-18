"""Anomaly -> top-k past-incident classification.

Hybrid score per candidate incident:

    score = text_weight   * cosine(text_emb, incident.text_emb)
          + numeric_weight * (1 - normalized_l2(reading, incident.signature))

The text side comes from VectorAI cosine search; the numeric side is computed
client-side over the incident payload's ``signature`` snapshot.
"""

from __future__ import annotations

import math

from actian_vectorai import VectorAIClient

from ..config import SENSOR_ORDER, get_settings
from ..db.incidents import hydrate_incident, search_incidents
from ..embeddings import embed
from ..schemas import AnomalyEvent, IncidentMatch


def _signature_distance(
    reading_values: dict[str, float],
    signature: dict[str, float],
    sensor_order: tuple[str, ...] = SENSOR_ORDER,
) -> float:
    """Normalized L2 distance between two sensor snapshots in [0, 1]."""
    if not signature:
        return 1.0

    sq = 0.0
    norm_sq = 0.0
    for sensor in sensor_order:
        a = reading_values.get(sensor, 0.0)
        b = signature.get(sensor, 0.0)
        sq += (a - b) ** 2
        scale = max(abs(a), abs(b), 1.0)
        norm_sq += scale * scale

    if norm_sq <= 0.0:
        return 0.0
    raw = math.sqrt(sq) / math.sqrt(norm_sq)
    return min(max(raw, 0.0), 1.0)


def classify(
    client: VectorAIClient,
    anomaly: AnomalyEvent,
    *,
    top_k: int | None = None,
) -> list[IncidentMatch]:
    """Return the top-k past incidents that best explain ``anomaly``."""
    cfg = get_settings()
    k = top_k if top_k is not None else cfg.incident_top_k

    query_text = anomaly.summary
    query_vec = embed(query_text)

    raw = search_incidents(client, query_vec, limit=k * 4)
    if not raw:
        return []

    matches: list[IncidentMatch] = []
    for hit in raw:
        incident = hydrate_incident(hit["payload"])
        text_sim = float(hit["score"])
        num_sim = 1.0 - _signature_distance(
            anomaly.reading.values, incident.signature
        )
        score = cfg.text_weight * text_sim + cfg.numeric_weight * num_sim
        matches.append(
            IncidentMatch(
                incident=incident,
                text_similarity=text_sim,
                numeric_similarity=num_sim,
                score=score,
            )
        )

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:k]
