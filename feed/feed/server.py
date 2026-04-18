"""FastAPI app that replays pump CSV rows to the backend on a tick."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException

from .config import ASSET_MAP, get_settings
from .replay import PumpReplay


log = logging.getLogger("rigsense.feed")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class _State:
    def __init__(self) -> None:
        cfg = get_settings()
        self.replay = PumpReplay(Path(cfg.csv_path))
        self.tick_seconds = cfg.tick_seconds
        self.speed_factor = 1.0
        self.paused = False
        self.ticks = 0
        self.sent = 0
        self.errors = 0
        self.last_error: str | None = None


_state: _State | None = None
_task: asyncio.Task[None] | None = None


async def _ticker() -> None:
    assert _state is not None
    cfg = get_settings()
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            try:
                if not _state.paused:
                    _state.ticks += 1
                    ts = datetime.now(tz=timezone.utc).isoformat()
                    for pump_id, values in _state.replay.next_tick():
                        asset_id = ASSET_MAP.get(pump_id)
                        if asset_id is None:
                            continue
                        payload = {
                            "rig_id": cfg.rig_id,
                            "asset_id": asset_id,
                            "ts": ts,
                            "values": values,
                        }
                        try:
                            resp = await client.post(
                                f"{cfg.backend_url}/ingest", json=payload
                            )
                            if resp.status_code >= 400:
                                _state.errors += 1
                                _state.last_error = (
                                    f"{resp.status_code}: {resp.text[:120]}"
                                )
                            else:
                                _state.sent += 1
                        except httpx.HTTPError as exc:
                            _state.errors += 1
                            _state.last_error = f"{exc.__class__.__name__}: {exc}"
                # speed_factor scales the interval: 2.0 => half the sleep
                await asyncio.sleep(_state.tick_seconds / max(_state.speed_factor, 0.01))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.exception("tick loop error: %s", exc)
                _state.errors += 1
                _state.last_error = f"{exc.__class__.__name__}: {exc}"
                await asyncio.sleep(1.0)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    global _state, _task
    _state = _State()
    log.info(
        "feed starting: %d pumps, cursors=%s",
        len(_state.replay.pump_ids),
        _state.replay.totals,
    )
    _task = asyncio.create_task(_ticker())
    try:
        yield
    finally:
        if _task is not None:
            _task.cancel()
            try:
                await _task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="RigSense Feed", version="0.1.0", lifespan=_lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status")
def status() -> dict[str, object]:
    if _state is None:
        raise HTTPException(503, "feed not started")
    return {
        "paused": _state.paused,
        "tick_seconds": _state.tick_seconds,
        "speed_factor": _state.speed_factor,
        "ticks": _state.ticks,
        "sent": _state.sent,
        "errors": _state.errors,
        "last_error": _state.last_error,
        "cursors": _state.replay.cursors,
        "totals": _state.replay.totals,
        "asset_map": ASSET_MAP,
    }


@app.post("/pause")
def pause() -> dict[str, bool]:
    assert _state is not None
    _state.paused = True
    return {"paused": True}


@app.post("/resume")
def resume() -> dict[str, bool]:
    assert _state is not None
    _state.paused = False
    return {"paused": False}


@app.post("/speed")
def speed(factor: float = 1.0) -> dict[str, float]:
    assert _state is not None
    if factor <= 0:
        raise HTTPException(400, "factor must be > 0")
    _state.speed_factor = factor
    return {"speed_factor": factor}
