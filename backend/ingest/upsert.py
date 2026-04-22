"""Shared VDB upsert helper used by every ingestion CLI.

Centralises:
  - deterministic ``uuid5`` point IDs (ROUTEWISE.md s5.1.7),
  - batched embedding + upsert,
  - ``has_narrative`` / ``aadt`` payload preservation,
  - friendly progress logging,
  - transient-timeout retry (the local VDB occasionally pauses >30 s
    for index flushing under sustained write pressure; see
    ``_upsert_with_retry``).
"""

from __future__ import annotations

import logging
import time
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

# Upsert retry policy for DEADLINE_EXCEEDED / transient gRPC failures.
# The client itself has max_retries=3 for UNAVAILABLE/RESOURCE_EXHAUSTED
# but TimeoutError is surfaced to us; retry it up to this many times
# with linear backoff before giving up.
_UPSERT_MAX_RETRIES = 3
_UPSERT_RETRY_SLEEP_S = 5.0


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


def _upsert_with_retry(client, collection: str, points: list) -> None:
    """Wrap ``client.points.upsert`` with linear-backoff retry on timeout.

    The VDB server occasionally exceeds the (now 120 s) gRPC deadline
    under sustained write pressure as it flushes its index. A single
    blip shouldn't tank an hour-long ingest — re-upserting is safe
    because point IDs are deterministic ``uuid5(source, case_id)``, so
    retries are idempotent.
    """
    from actian_vectorai.exceptions import TimeoutError as VdbTimeoutError

    for attempt in range(1, _UPSERT_MAX_RETRIES + 1):
        try:
            client.points.upsert(collection, points)
            return
        except VdbTimeoutError as exc:
            if attempt == _UPSERT_MAX_RETRIES:
                logger.error(
                    "upsert timed out after %d attempts; giving up: %s",
                    _UPSERT_MAX_RETRIES, exc,
                )
                raise
            sleep_s = _UPSERT_RETRY_SLEEP_S * attempt
            logger.warning(
                "upsert timed out (attempt %d/%d); retrying in %.1fs: %s",
                attempt, _UPSERT_MAX_RETRIES, sleep_s, exc,
            )
            time.sleep(sleep_s)


def upsert_docs(docs: Iterable[SituationDoc], *, batch_size: int = 256) -> int:
    """Embed + upsert a stream of docs into the configured collection.

    Returns the number of points written.
    """
    from actian_vectorai import PointStruct

    ensure_collection()
    client = get_client()
    collection = client_collection_name()

    n_total = 0
    for batch in _chunks(docs, batch_size):
        texts = [render_narrative(d) for d in batch]
        vectors = embed(texts)

        points: list = []
        for doc, vec in zip(batch, vectors):
            pid = point_id_for(doc)
            payload = doc.model_dump(mode="json")
            points.append(PointStruct(id=pid, vector=vec.tolist(), payload=payload))

        _upsert_with_retry(client, collection, points)
        n_total += len(points)
        logger.info("upserted %d (running total %d)", len(points), n_total)

    return n_total


def client_collection_name() -> str:
    from backend.config import get_settings

    return get_settings().vdb_collection
