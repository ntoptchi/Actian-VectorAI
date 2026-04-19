"""In-memory copy of the crash corpus, used for hot-path filtering.

The Actian VectorAI server in our dev environment does not implement
payload-field indexes (``create_field_index`` returns 501), so any
``points.scroll`` call with a payload filter (e.g. ``h3_cell IN (...)``
plus ``hour_bucket IN (...)``) does a full sequential scan inside the
engine and times out around the 30 s default RPC deadline. With ~5
filter chunks per request and several timeouts each, a single
``/trip/brief`` was taking 90–160 seconds.

The corpus is small enough to hold entirely in process memory
(140K rows × ~30 fields ≈ a few hundred MB). Loading it once at
startup turns the geographic filter into a list comprehension —
microseconds — and brings the total request well under the 8 s
budget. Background-loaded on a daemon thread so the API can serve
``/health`` and other lightweight endpoints immediately.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_PAGE_SIZE = 10_000

_cache: Optional[list[dict]] = None
_load_lock = threading.Lock()
_loading_thread: Optional[threading.Thread] = None


def _load_all() -> list[dict]:
    """Pull every crash payload via paginated unfiltered ``scroll``.

    Returns a flat list of payload dicts; vectors are not loaded
    because we don't need them on the read path (we filter
    geographically and temporally with plain dict access).
    """
    from backend.config import get_settings
    from backend.vdb import get_client

    client = get_client()
    name = get_settings().vdb_collection

    out: list[dict] = []
    offset = None
    t0 = time.perf_counter()
    while True:
        page, offset = client.points.scroll(
            name, offset=offset, limit=_PAGE_SIZE, with_vectors=False,
        )
        for r in page:
            payload = getattr(r, "payload", None)
            if payload:
                out.append(payload)
        if not offset or not page:
            break
    logger.info(
        "crash_cache: loaded %d crashes in %.1fs",
        len(out), time.perf_counter() - t0,
    )
    return out


def get_crashes() -> list[dict]:
    """Return the cached corpus, blocking on the first call.

    Subsequent calls are O(1). Thread-safe via double-checked
    locking — multiple concurrent first callers will collapse to a
    single load.
    """
    global _cache
    if _cache is not None:
        return _cache
    with _load_lock:
        if _cache is None:
            _cache = _load_all()
        return _cache


def warm_in_background() -> None:
    """Kick off the cache load on a daemon thread.

    Safe to call multiple times — only the first call spawns a
    thread. Designed for the FastAPI startup hook so the API binds
    immediately and the corpus is ready by the time the first
    ``/trip/brief`` arrives.
    """
    global _loading_thread
    if _cache is not None or _loading_thread is not None:
        return
    _loading_thread = threading.Thread(
        target=get_crashes,
        name="crash-cache-loader",
        daemon=True,
    )
    _loading_thread.start()
    logger.info("crash_cache: warm-up thread started")


def cache_status() -> dict:
    """Lightweight status used by ``/health`` to report cache readiness."""
    return {
        "loaded": _cache is not None,
        "size": len(_cache) if _cache is not None else 0,
    }
