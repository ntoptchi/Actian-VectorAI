"""FastAPI entry point for RouteWise.

Run via::

    uvicorn backend.main:app --reload --port 8080

The ``./start.sh`` script picks this up automatically once it exists.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.routers import hotspots, trip
from backend.vdb import ensure_collection, health as vdb_health

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("routewise")

settings = get_settings()

app = FastAPI(
    title="RouteWise API",
    version="0.1.0",
    description=(
        "Pre-trip briefing for unfamiliar long drives. Powered by Actian "
        "VectorAI DB. See ROUTEWISE.md for the spec."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trip.router)
app.include_router(hotspots.router)


@app.on_event("startup")
async def _on_startup() -> None:
    """Best-effort VDB bootstrap. Don't crash if VDB is down — the brief
    endpoint is required to degrade gracefully (ROUTEWISE.md s2.4).
    """
    try:
        ensure_collection()
    except Exception as exc:  # noqa: BLE001
        logger.warning("VDB bootstrap skipped (DB unreachable?): %s", exc)


@app.get("/health")
async def health() -> dict:
    """Liveness + VDB connectivity probe."""
    return {
        "ok": True,
        "service": "routewise-api",
        "version": app.version,
        "vdb": vdb_health(),
    }
