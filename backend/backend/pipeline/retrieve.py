"""Two-tier guidance retrieval.

For each top-k incident:
  1. Embed ``failure_type + description``.
  2. Cosine-search ``manuals`` and rank by ``incident_sim * manual_sim``.
  3. For each top manual, cosine-search ``manual_chunks`` filtered by
     ``manual_id``; keep the single best chunk.
  4. Final guidance score: ``incident_sim * manual_sim * chunk_sim``.

Manuals are deduped across incidents -- if two incidents both surface the same
manual, we keep the higher-scoring entry.
"""

from __future__ import annotations

from actian_vectorai import VectorAIClient

from ..config import get_settings
from ..db.chunks import hydrate_chunk, search_chunks_for_manual
from ..db.manuals import hydrate_manual, search_manuals
from ..embeddings import embed
from ..schemas import GuidanceHit, IncidentMatch


def _incident_query_text(match: IncidentMatch) -> str:
    return f"{match.incident.failure_type}: {match.incident.description}"


def retrieve(
    client: VectorAIClient,
    matches: list[IncidentMatch],
    *,
    manual_top_k: int | None = None,
    chunk_top_k: int | None = None,
) -> list[GuidanceHit]:
    """Rank manuals + best chunks across the given incident matches."""
    cfg = get_settings()
    m_top = manual_top_k if manual_top_k is not None else cfg.manual_top_k
    c_top = chunk_top_k if chunk_top_k is not None else cfg.chunk_top_k

    best: dict[str, GuidanceHit] = {}

    for match in matches:
        query_vec = embed(_incident_query_text(match))

        manual_hits = search_manuals(client, query_vec, limit=m_top)
        if not manual_hits:
            continue

        for mhit in manual_hits:
            manual = hydrate_manual(mhit["payload"])
            manual_sim = float(mhit["score"])

            chunk_hits = search_chunks_for_manual(
                client,
                query_vec,
                manual_id=manual.manual_id,
                limit=c_top,
            )
            if not chunk_hits:
                continue

            top_chunk_hit = chunk_hits[0]
            chunk = hydrate_chunk(top_chunk_hit["payload"])
            chunk_sim = float(top_chunk_hit["score"])

            score = match.score * manual_sim * chunk_sim

            existing = best.get(manual.manual_id)
            if existing is None or score > existing.score:
                best[manual.manual_id] = GuidanceHit(
                    manual=manual,
                    best_chunk=chunk,
                    incident_similarity=match.score,
                    manual_similarity=manual_sim,
                    chunk_similarity=chunk_sim,
                    score=score,
                )

    ranked = sorted(best.values(), key=lambda g: g.score, reverse=True)
    return ranked[:m_top]
