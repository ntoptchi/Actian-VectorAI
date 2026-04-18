"""HTTP layer for the RigSense pipeline.

Endpoints:

* ``GET  /health``            - liveness + VectorAI server version
* ``GET  /demo``              - run the synthetic stream through the orchestrator
* ``POST /analyze``           - run detect/classify/retrieve on a client-supplied
                                 baseline window + current reading
* ``POST /ingest``            - feed a live SensorReading into the in-memory
                                 LiveState; once the window fills, auto-run
                                 detect/classify/retrieve and cache the report
* ``GET  /state/dashboard``   - return a DashboardState shape that mirrors
                                 ``src/data/dashboardData.ts``

Kept deliberately small; the real pipeline lives in ``backend.pipeline``.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import get_settings
from .db.client import get_client
from .live import build_dashboard_state
from .pipeline.detect import BaselineStats
from .pipeline.orchestrator import analyze, stream_window
from .schemas import AnomalyReport, SensorReading
from .seed.sample_sensors import generate_sample_stream
from .state import WINDOW, get_live_state


log = logging.getLogger("rigsense.server")


class AnalyzeRequest(BaseModel):
    baseline_window: list[SensorReading]
    reading: SensorReading


class HealthResponse(BaseModel):
    status: str
    vectorai_host: str
    vectorai_version: str | None = None


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # Warm the live-state singleton so /ingest is usable from tick 1.
    get_live_state()
    yield


app = FastAPI(
    title="RigSense API",
    version="0.1.0",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    cfg = get_settings()
    try:
        with get_client() as client:
            info = client.health_check()
        return HealthResponse(
            status="ok",
            vectorai_host=cfg.vectorai_host,
            vectorai_version=info.get("version"),
        )
    except Exception as exc:
        return HealthResponse(
            status=f"degraded: {exc.__class__.__name__}",
            vectorai_host=cfg.vectorai_host,
        )


@app.get("/demo", response_model=list[AnomalyReport])
def demo() -> list[AnomalyReport]:
    """Stream the canned sample sensor data through the pipeline."""
    stream = generate_sample_stream()
    reports: list[AnomalyReport] = []
    with get_client() as client:
        for report in stream_window(
            client, stream, window_size=30, persist_readings=False
        ):
            reports.append(report)
    return reports


@app.post("/analyze", response_model=AnomalyReport | None)
def analyze_endpoint(req: AnalyzeRequest) -> AnomalyReport | None:
    if not req.baseline_window:
        raise HTTPException(400, "baseline_window must not be empty")
    baseline = BaselineStats.from_window(req.baseline_window)
    with get_client() as client:
        return analyze(client, req.reading, baseline)


@app.post("/ingest", status_code=202)
def ingest(reading: SensorReading) -> Response:
    """Push a live SensorReading into the per-asset ring buffer.

    Once the buffer has at least ``WINDOW // 2`` samples, we run the pipeline
    and cache the resulting AnomalyReport (if any) on LiveState. Failures in
    the pipeline log-and-swallow so a single bad classify call doesn't stop
    the feed.
    """
    live = get_live_state()
    live.push_reading(reading)
    window = live.window(reading.asset_id)
    if len(window) < max(WINDOW // 2, 15):
        return Response(status_code=202)

    baseline = BaselineStats.from_window(window[:-1] or [reading])
    try:
        with get_client() as client:
            report = analyze(client, reading, baseline)
    except Exception as exc:
        log.warning("ingest analyze failed: %s", exc)
        return Response(status_code=202)

    if report is not None:
        live.record_report(report)
    return Response(status_code=202)


@app.get("/state/dashboard")
def state_dashboard() -> dict[str, Any]:
    live = get_live_state()
    return build_dashboard_state(live)
