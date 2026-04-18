"""VectorAI DB client wiring for RouteWise.

Provides:
  - ``get_client()`` — process-cached sync client.
  - ``ensure_collection()`` — idempotent collection bootstrap with the
    payload indexes ROUTEWISE.md s6.2 calls for.

The sync client is wrapped via ``asyncio.to_thread`` from the FastAPI
routers (see VectorAI DB README "Note" about sync-in-async usage).
"""

from __future__ import annotations

import logging
from functools import lru_cache

from backend.config import get_settings

logger = logging.getLogger(__name__)


# Payload fields we want exact-match indexes on at query time
# (see ROUTEWISE.md s6.2).
INDEXED_PAYLOAD_FIELDS: tuple[str, ...] = (
    "h3_cell",
    "state",
    "source",
    "severity",
)


@lru_cache(maxsize=1)
def get_client():  # type: ignore[no-untyped-def]
    """Return a process-cached ``VectorAIClient`` connected to the DB."""
    from actian_vectorai import VectorAIClient

    settings = get_settings()
    return VectorAIClient(settings.vdb_address)


def ensure_collection() -> None:
    """Create the ``routewise_crashes`` collection if it doesn't exist.

    Idempotent. Also creates payload indexes for the fields we filter on
    at query time. Safe to call from ingestion scripts and from the API
    startup hook.
    """
    from actian_vectorai import Distance, VectorParams

    settings = get_settings()
    client = get_client()
    name = settings.vdb_collection

    if not client.collections.exists(name):
        client.collections.create(
            name,
            vectors_config=VectorParams(
                size=settings.vdb_vector_size,
                distance=Distance.Cosine,
            ),
        )
        logger.info("created VDB collection %s", name)
    else:
        logger.info("VDB collection %s already exists", name)

    # Best-effort payload indexes; server may report UNIMPLEMENTED for
    # dynamic field indexing (see VectorAI DB README "Current Status").
    # That's fine — exact filters still work, just unindexed.
    for field in INDEXED_PAYLOAD_FIELDS:
        try:
            client.points.create_field_index(name, field_name=field)  # type: ignore[attr-defined]
            logger.info("created payload index on %s.%s", name, field)
        except Exception as exc:  # noqa: BLE001 — server-side feature gate
            logger.debug("skipping payload index on %s.%s: %s", name, field, exc)


def health() -> dict:
    """Lightweight VDB liveness probe used by ``/health``."""
    try:
        info = get_client().health_check()
        return {"ok": True, **info}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
