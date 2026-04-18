"""manuals collection helpers (manual-level metadata)."""

from __future__ import annotations

from actian_vectorai import PointStruct, VectorAIClient

from ..config import get_settings
from ..embeddings import embed_texts
from ..schemas import RepairManual
from ._ids import stable_id


def _manual_text(manual: RepairManual) -> str:
    return f"{manual.manual_name}. {manual.summary}"


def upsert_manuals(
    client: VectorAIClient,
    manuals: list[RepairManual],
) -> int:
    """Embed and persist manual-level entries (one row per manual)."""
    if not manuals:
        return 0
    cfg = get_settings()

    vectors = embed_texts(_manual_text(m) for m in manuals)
    points = [
        PointStruct(
            id=stable_id(manual.manual_id),
            vector=vec,
            payload={
                "manual_id": manual.manual_id,
                "manual_name": manual.manual_name,
                "summary": manual.summary,
            },
        )
        for manual, vec in zip(manuals, vectors)
    ]
    client.points.upsert(cfg.manuals_collection, points)
    return len(points)


def search_manuals(
    client: VectorAIClient,
    query_vector: list[float],
    *,
    limit: int,
) -> list[dict]:
    """Cosine-search manuals by a pre-embedded query vector."""
    cfg = get_settings()
    results = client.points.search(
        cfg.manuals_collection,
        vector=query_vector,
        limit=limit,
    )
    return [
        {"id": r.id, "score": r.score, "payload": r.payload}
        for r in results
    ]


def hydrate_manual(payload: dict) -> RepairManual:
    """Rebuild a (chunkless) RepairManual from a search-result payload."""
    return RepairManual(
        manual_id=payload["manual_id"],
        manual_name=payload["manual_name"],
        summary=payload["summary"],
        chunks=[],
    )
