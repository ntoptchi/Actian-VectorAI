"""past_incidents collection helpers."""

from __future__ import annotations

from actian_vectorai import PointStruct, VectorAIClient

from ..config import get_settings
from ..embeddings import embed_texts
from ..schemas import PastIncident
from ._ids import stable_id


def _incident_text(incident: PastIncident) -> str:
    """Canonical string we embed for an incident."""
    return (
        f"{incident.incident_name}. "
        f"Failure type: {incident.failure_type}. "
        f"{incident.description}"
    )


def upsert_incidents(
    client: VectorAIClient,
    incidents: list[PastIncident],
) -> int:
    """Embed and persist a batch of incidents."""
    if not incidents:
        return 0
    cfg = get_settings()

    vectors = embed_texts(_incident_text(i) for i in incidents)
    points = [
        PointStruct(
            id=stable_id(incident.incident_id),
            vector=vec,
            payload={
                "incident_id": incident.incident_id,
                "incident_name": incident.incident_name,
                "failure_type": incident.failure_type,
                "severity": incident.severity,
                "description": incident.description,
                "signature": incident.signature,
                "related_manual_ids": incident.related_manual_ids,
            },
        )
        for incident, vec in zip(incidents, vectors)
    ]
    client.points.upsert(cfg.past_incidents_collection, points)
    return len(points)


def search_incidents(
    client: VectorAIClient,
    query_vector: list[float],
    *,
    limit: int,
) -> list[dict]:
    """Cosine-search past incidents by a pre-embedded query vector."""
    cfg = get_settings()
    results = client.points.search(
        cfg.past_incidents_collection,
        vector=query_vector,
        limit=limit,
    )
    return [
        {"id": r.id, "score": r.score, "payload": r.payload}
        for r in results
    ]


def hydrate_incident(payload: dict) -> PastIncident:
    """Rebuild a PastIncident from a search-result payload."""
    return PastIncident(
        incident_id=payload["incident_id"],
        incident_name=payload["incident_name"],
        failure_type=payload["failure_type"],
        severity=payload["severity"],
        description=payload["description"],
        signature=payload.get("signature", {}),
        related_manual_ids=payload.get("related_manual_ids", []),
    )
