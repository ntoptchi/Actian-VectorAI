"""manual_chunks collection helpers (per-chunk text)."""

from __future__ import annotations

from actian_vectorai import (
    Field as VField,
    FilterBuilder,
    PointStruct,
    VectorAIClient,
)

from ..config import get_settings
from ..embeddings import embed_texts
from ..schemas import RepairManual, RepairManualChunk
from ._ids import stable_id


def upsert_manual_chunks(
    client: VectorAIClient,
    manuals: list[RepairManual],
) -> int:
    """Embed and persist every chunk of every manual."""
    cfg = get_settings()

    chunks: list[RepairManualChunk] = []
    for manual in manuals:
        for chunk in manual.chunks:
            chunks.append(
                RepairManualChunk(
                    chunk_id=chunk.chunk_id,
                    manual_id=manual.manual_id,
                    manual_name=manual.manual_name,
                    text=chunk.text,
                )
            )

    if not chunks:
        return 0

    vectors = embed_texts(c.text for c in chunks)
    points = [
        PointStruct(
            id=stable_id(chunk.chunk_id),
            vector=vec,
            payload={
                "chunk_id": chunk.chunk_id,
                "manual_id": chunk.manual_id,
                "manual_name": chunk.manual_name,
                "text": chunk.text,
            },
        )
        for chunk, vec in zip(chunks, vectors)
    ]
    client.points.upsert(cfg.manual_chunks_collection, points)
    return len(points)


def search_chunks_for_manual(
    client: VectorAIClient,
    query_vector: list[float],
    *,
    manual_id: str,
    limit: int,
) -> list[dict]:
    """Cosine-search chunks restricted to a single manual."""
    cfg = get_settings()
    f = FilterBuilder().must(VField("manual_id").eq(manual_id)).build()
    results = client.points.search(
        cfg.manual_chunks_collection,
        vector=query_vector,
        limit=limit,
        filter=f,
    )
    return [
        {"id": r.id, "score": r.score, "payload": r.payload}
        for r in results
    ]


def hydrate_chunk(payload: dict) -> RepairManualChunk:
    """Rebuild a RepairManualChunk from a search-result payload."""
    return RepairManualChunk(
        chunk_id=payload["chunk_id"],
        manual_id=payload["manual_id"],
        manual_name=payload["manual_name"],
        text=payload["text"],
    )
