"""Replay pump CSV rows as a live sensor stream.

We deliberately only replay the second half of the CSV: the top half was
consumed by ``backend.seed.pump_dataset.build_incidents`` to create the
seeded past-incidents, and re-playing those same rows would be circular.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator


PUMP_SENSOR_COLUMNS = ("Temperature", "Vibration", "Pressure", "Flow_Rate", "RPM")
HISTORICAL_FRACTION = 0.5

_COLUMN_TO_SCHEMA: dict[str, str] = {
    "Temperature": "bearing_temp",
    "Vibration": "vibration",
    "Pressure": "pressure",
    "RPM": "rpm",
}


def _to_values(raw: dict[str, str]) -> dict[str, float]:
    values: dict[str, float] = {
        "vibration": 0.0,
        "bearing_temp": 0.0,
        "pressure": 0.0,
        "rpm": 0.0,
        "lubricant_pressure": 0.0,
        "humidity": 0.0,
    }
    for col, schema_key in _COLUMN_TO_SCHEMA.items():
        try:
            values[schema_key] = float(raw[col])
        except (KeyError, ValueError):
            pass
    try:
        values["flow_rate"] = float(raw["Flow_Rate"])
    except (KeyError, ValueError):
        pass
    return values


def load_live_rows(csv_path: Path) -> dict[int, list[dict[str, float]]]:
    """Return {pump_id: [row_values_dict...]} for the second half of the CSV."""
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"CSV not found at {csv_path}")

    all_rows: list[tuple[int, dict[str, str]]] = []
    with open(csv_path, "r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            try:
                pump_id = int(float(raw["Pump_ID"]))
            except (KeyError, ValueError):
                continue
            all_rows.append((pump_id, raw))

    cutoff = int(len(all_rows) * HISTORICAL_FRACTION)
    live_rows = all_rows[cutoff:]

    by_pump: dict[int, list[dict[str, float]]] = {}
    for pump_id, raw in live_rows:
        by_pump.setdefault(pump_id, []).append(_to_values(raw))
    return by_pump


class PumpReplay:
    """Wraps the live half of the CSV as a resettable per-pump cursor."""

    def __init__(self, csv_path: Path) -> None:
        self._by_pump = load_live_rows(csv_path)
        self._cursors: dict[int, int] = {pid: 0 for pid in self._by_pump}

    @property
    def pump_ids(self) -> list[int]:
        return list(self._by_pump.keys())

    @property
    def cursors(self) -> dict[int, int]:
        return dict(self._cursors)

    @property
    def totals(self) -> dict[int, int]:
        return {pid: len(rows) for pid, rows in self._by_pump.items()}

    def next_tick(self) -> Iterator[tuple[int, dict[str, float]]]:
        """One row per pump, cycling through the CSV indefinitely."""
        for pid, rows in self._by_pump.items():
            if not rows:
                continue
            idx = self._cursors[pid] % len(rows)
            yield pid, rows[idx]
            self._cursors[pid] = idx + 1
