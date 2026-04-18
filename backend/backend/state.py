"""In-memory live state for the RigSense backend.

Singleton. Holds:

* a ring buffer of recent ``SensorReading`` per ``asset_id`` (size ``WINDOW``);
* the latest ``AnomalyReport`` observed per asset;
* a rolling history of the last N reports across all assets;
* a rolling history of the last K state transitions for the timeline widget.

Thread-safe: a single ``RLock`` wraps every mutation. That's enough for a
hackathon where one FastAPI worker is writing from ``/ingest`` and readers
come from ``/state/dashboard``.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Deque

from .schemas import AnomalyReport, SensorReading


WINDOW = 60           # readings retained per asset
REPORTS_MAX = 32      # last N reports across all assets
TIMELINE_MAX = 8      # last K state transitions


class LiveState:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._buffers: dict[str, Deque[SensorReading]] = {}
        self._asset_reports: dict[str, AnomalyReport] = {}
        self._recent_reports: Deque[AnomalyReport] = deque(maxlen=REPORTS_MAX)
        self._timeline: Deque[str] = deque(maxlen=TIMELINE_MAX)
        self._asset_status: dict[str, str] = {}
        self._started_at = datetime.now(tz=timezone.utc)
        self._total_ingested = 0

    def push_reading(self, reading: SensorReading) -> None:
        with self._lock:
            buf = self._buffers.setdefault(reading.asset_id, deque(maxlen=WINDOW))
            buf.append(reading)
            self._total_ingested += 1

    def window(self, asset_id: str) -> list[SensorReading]:
        with self._lock:
            return list(self._buffers.get(asset_id, ()))

    def all_windows(self) -> dict[str, list[SensorReading]]:
        with self._lock:
            return {aid: list(buf) for aid, buf in self._buffers.items()}

    def record_report(self, report: AnomalyReport) -> None:
        with self._lock:
            asset_id = report.anomaly.asset_id
            severity = report.anomaly.severity
            prev = self._asset_status.get(asset_id)
            self._asset_reports[asset_id] = report
            self._recent_reports.append(report)
            self._asset_status[asset_id] = severity

            if prev != severity:
                hhmm = report.anomaly.ts.astimezone(timezone.utc).strftime("%H:%M")
                worst = max(report.anomaly.deviations, key=lambda d: abs(d.z_score))
                direction = "exceeded" if worst.z_score > 0 else "dropped below"
                self._timeline.append(
                    f"{hhmm} {asset_id} {worst.sensor} {direction} tolerance "
                    f"(z={worst.z_score:+.1f})"
                )

    def asset_reports(self) -> dict[str, AnomalyReport]:
        with self._lock:
            return dict(self._asset_reports)

    def recent_reports(self) -> list[AnomalyReport]:
        with self._lock:
            return list(self._recent_reports)

    def timeline(self) -> list[str]:
        with self._lock:
            return list(self._timeline)

    def asset_status(self) -> dict[str, str]:
        with self._lock:
            return dict(self._asset_status)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "assets_tracked": len(self._buffers),
                "reports_total": len(self._recent_reports),
                "readings_ingested": self._total_ingested,
            }


_live: LiveState | None = None
_live_lock = threading.Lock()


def get_live_state() -> LiveState:
    global _live
    with _live_lock:
        if _live is None:
            _live = LiveState()
    return _live
