"""Shared VDB upsert helper used by every ingestion CLI.

Centralises:
  - deterministic ``uuid5`` point IDs (ROUTEWISE.md s5.1.7),
  - batched embedding + upsert,
  - ``has_narrative`` / ``aadt`` payload preservation,
  - friendly progress logging.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING

from backend.embeddings import embed
from backend.ingest.situation_doc import render_narrative
from backend.schemas import SituationDoc
from backend.vdb import ensure_collection, get_client

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Stable namespace for uuid5(point_id, source + case_id).
NAMESPACE = uuid.UUID("4ec5f5e0-7a1b-4f33-8b66-04e7e15e0001")


def point_id_for(doc: SituationDoc) -> str:
    seed = f"{doc.source}:{doc.case_id}"
    return str(uuid.uuid5(NAMESPACE, seed))


def _chunks(iterable: Iterable, size: int) -> Iterator[list]:
    batch: list = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def upsert_docs(docs: Iterable[SituationDoc], *, batch_size: int = 256) -> int:
    """Embed + upsert a stream of docs into the configured collection.

    Returns the number of points written.
    """
    from actian_vectorai import PointStruct

    ensure_collection()
    client = get_client()

    n_total = 0
    for batch in _chunks(docs, batch_size):
        texts = [render_narrative(d) for d in batch]
        vectors = embed(texts)

        points: list = []
        for doc, vec in zip(batch, vectors):
            pid = point_id_for(doc)
            payload = doc.model_dump(mode="json")
            points.append(PointStruct(id=pid, vector=vec.tolist(), payload=payload))

        client.points.upsert(client_collection_name(), points)
        n_total += len(points)
        logger.info("upserted %d (running total %d)", len(points), n_total)

    return n_total


def client_collection_name() -> str:
    from backend.config import get_settings

    return get_settings().vdb_collection
