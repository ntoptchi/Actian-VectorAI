"""Minimal HTTP layer for the RigSense pipeline.

Exposes two endpoints for the React dashboard:

* ``GET  /health``  - liveness + VectorAI server version
* ``GET  /demo``    - run the synthetic stream through the orchestrator
                       and return every ``AnomalyReport`` as JSON.
* ``POST /analyze`` - run detect/classify/retrieve on a client-supplied
                       baseline window + current reading.

Kept deliberately small; the real pipeline lives in ``backend.pipeline``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import get_settings
from .db.client import get_client
from .pipeline.detect import BaselineStats
from .pipeline.orchestrator import analyze, stream_window
from .schemas import AnomalyReport, SensorReading
from .seed.sample_sensors import generate_sample_stream


class AnalyzeRequest(BaseModel):
    baseline_window: list[SensorReading]
    reading: SensorReading


class HealthResponse(BaseModel):
    status: str
    vectorai_host: str
    vectorai_version: str | None = None


@asynccontextmanager
async def _lifespan(_app: FastAPI):
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
