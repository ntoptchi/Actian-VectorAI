"""VectorAI DB wiring for the ``routewise_coaching`` collection.

Distinct from ``backend.vdb`` (which owns the big ``routewise_crashes``
corpus) because the coaching collection has a very different shape:

  - **Smaller** (~500 enriched news articles vs ~100k+ crashes), so
    server-side ANN works without the in-memory cache workaround.
  - **Multi-vector**: three dense named vectors (``lesson``,
    ``incident``, ``factors_text``) so dense retrieval can match on
    distinct facets (what the driver should do, what happened, which
    factors were involved).
  - **Sparse (best-effort)**: a ``factors`` sparse vector for
    keyword-style term matching. If the VDB server returns
    ``UnimplementedError`` on sparse creation we quietly fall back to
    dense-only — the retrieval service handles the missing channel.

Pattern distilled from ``vectorai-db-beta/examples/29_named_vectors.py``
and ``vectorai-db-beta/examples/33_sparse_vectors.py``.
"""

from __future__ import annotations

import logging

from backend.config import get_settings
from backend.ingest.factor_vocab import VOCAB_SIZE
from backend.vdb import get_client

logger = logging.getLogger(__name__)

# Named-vector keys. Exported so ingestion + retrieval agree on the names.
VEC_LESSON = "lesson"
VEC_INCIDENT = "incident"
VEC_FACTORS_TEXT = "factors_text"
VEC_SPARSE = "factors"

DENSE_VECTORS: tuple[str, ...] = (VEC_LESSON, VEC_INCIDENT, VEC_FACTORS_TEXT)


def ensure_coaching_collection() -> bool:
    """Create ``routewise_coaching`` if missing. Idempotent.

    Returns ``True`` if the collection ended up with a working sparse
    vector space (verified via a test upsert), ``False`` if we had to
    fall back to dense-only. Callers use this flag to decide whether
    the sparse retrieval stage is available.

    The verification is stricter than it sounds: some VDB server builds
    silently accept ``sparse_vectors_config`` on creation but then 422
    on the first sparse upsert with *"Unknown vector name"*. We'd
    rather discover that immediately (and fall back to dense-only) than
    have retrieval silently broken.
    """
    from actian_vectorai import (
        Distance,
        SparseVectorParams,
        VectorParams,
    )

    settings = get_settings()
    client = get_client()
    name = settings.vdb_coaching_collection

    if client.collections.exists(name):
        has_sparse = _probe_sparse_support(client, name)
        logger.info(
            "VDB collection %s already exists (sparse=%s)", name, has_sparse
        )
        return has_sparse

    dense_config = {
        v: VectorParams(size=settings.vdb_vector_size, distance=Distance.Cosine)
        for v in DENSE_VECTORS
    }

    # Attempt dense + sparse; verify via roundtrip; fall back if needed.
    try:
        client.collections.create(
            name,
            vectors_config=dense_config,
            sparse_vectors_config={VEC_SPARSE: SparseVectorParams()},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "sparse create raised; falling back to dense-only: %s", exc,
        )
        if client.collections.exists(name):
            client.collections.delete(name)
        client.collections.create(name, vectors_config=dense_config)
        logger.info(
            "created VDB collection %s (dense=%s, sparse=DISABLED via create-exception)",
            name, list(DENSE_VECTORS),
        )
        return False

    if _probe_sparse_support(client, name):
        logger.info(
            "created VDB collection %s (dense=%s, sparse=%s, vocab=%d)",
            name, list(DENSE_VECTORS), VEC_SPARSE, VOCAB_SIZE,
        )
        return True

    # Server accepted sparse config but doesn't actually honour it.
    # Recreate dense-only so the ingest path doesn't blow up.
    logger.warning(
        "sparse creation reported success but probe failed — "
        "recreating collection %s as dense-only", name,
    )
    client.collections.delete(name)
    client.collections.create(name, vectors_config=dense_config)
    return False


def _probe_sparse_support(client, name: str) -> bool:  # type: ignore[no-untyped-def]
    """Verify the sparse space actually exists by round-tripping a probe point.

    We upsert a single point with a tiny sparse vector, then immediately
    delete it. If either step raises, we treat the collection as
    dense-only. This is the only trustworthy signal on this server
    build — metadata inspection lies (the server returns the config
    we passed but then 422s on real upserts).
    """
    try:
        from actian_vectorai import PointStruct, SparseVector

        probe_id = "__sparse_probe__"
        zero_vec = [0.0] * get_settings().vdb_vector_size
        probe = PointStruct(
            id=probe_id,
            vector={
                VEC_LESSON: zero_vec,
                VEC_INCIDENT: zero_vec,
                VEC_FACTORS_TEXT: zero_vec,
                VEC_SPARSE: SparseVector(indices=[0], values=[1.0]),
            },
            payload={"__probe__": True},
        )
        client.points.upsert(name, [probe])
    except Exception as exc:  # noqa: BLE001
        logger.debug("sparse probe upsert failed: %s", exc)
        return False
    try:
        client.points.delete(name, [probe_id])
    except Exception:  # noqa: BLE001
        pass
    return True


def coaching_collection_name() -> str:
    return get_settings().vdb_coaching_collection


def coaching_health() -> dict:
    """Lightweight probe used by diagnostics + scripts."""
    try:
        client = get_client()
        name = coaching_collection_name()
        if not client.collections.exists(name):
            return {"ok": False, "error": f"collection '{name}' missing"}
        count = client.points.count(name)
        return {"ok": True, "collection": name, "points": count}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
