"""Seed past incidents from the industrial-pump maintenance CSV.

The dataset at ``data/industrial_pump/Large_Industrial_Pump_Maintenance_Dataset.csv``
contains 20,000 pump snapshots with a binary ``Maintenance_Flag``. We:

1. Split rows into nominal (flag=0) and maintenance (flag=1).
2. Compute per-sensor baseline stats over nominal rows.
3. Score each maintenance row by aggregate abs-z and keep the top N.
4. Synthesize a ``PastIncident`` per pick whose description names the top
   deviating sensors -- that's what MiniLM will actually embed.

The CSV columns map onto ``SENSOR_ORDER`` as a superset: ``Temperature ->
bearing_temp``, plus ``vibration``, ``pressure``, ``rpm``, and an added
``flow_rate`` stored in the signature for future use. ``humidity`` and
``lubricant_pressure`` stay 0 -- the pump data doesn't carry them.
"""

from __future__ import annotations

import csv
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

from ..schemas import PastIncident, Severity


DATASET_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "industrial_pump"
    / "Large_Industrial_Pump_Maintenance_Dataset.csv"
)

PUMP_SENSOR_COLUMNS = (
    "Temperature",
    "Vibration",
    "Pressure",
    "Flow_Rate",
    "RPM",
)

# How much of the CSV we treat as historical (seeded) vs live (replayed).
HISTORICAL_FRACTION = 0.5

# Top-N maintenance rows kept as past incidents.
N_INCIDENTS = 60


_COLUMN_TO_SCHEMA: dict[str, str] = {
    "Temperature": "bearing_temp",
    "Vibration": "vibration",
    "Pressure": "pressure",
    "Flow_Rate": "flow_rate",
    "RPM": "rpm",
}


@dataclass(frozen=True)
class PumpRow:
    row_index: int
    pump_id: int
    values: dict[str, float]
    operational_hours: float
    maintenance_flag: int


def load_pump_rows(csv_path: Path = DATASET_PATH) -> list[PumpRow]:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Pump dataset not found at {csv_path}. "
            "Make sure data/industrial_pump/ is populated."
        )

    rows: list[PumpRow] = []
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for idx, raw in enumerate(reader):
            try:
                row = PumpRow(
                    row_index=idx,
                    pump_id=int(float(raw["Pump_ID"])),
                    values={col: float(raw[col]) for col in PUMP_SENSOR_COLUMNS},
                    operational_hours=float(raw["Operational_Hours"]),
                    maintenance_flag=int(float(raw["Maintenance_Flag"])),
                )
            except (KeyError, ValueError):
                continue
            rows.append(row)
    return rows


def split_historical_live(rows: list[PumpRow]) -> tuple[list[PumpRow], list[PumpRow]]:
    """First half = seed; second half = reserved for the live feed."""
    cutoff = int(len(rows) * HISTORICAL_FRACTION)
    return rows[:cutoff], rows[cutoff:]


def _baseline(nominal: list[PumpRow]) -> dict[str, tuple[float, float]]:
    stats: dict[str, tuple[float, float]] = {}
    for col in PUMP_SENSOR_COLUMNS:
        samples = [r.values[col] for r in nominal]
        mean = statistics.fmean(samples)
        std = statistics.pstdev(samples) if len(samples) > 1 else 0.0
        stats[col] = (mean, max(std, 1e-6))
    return stats


def _abs_z(row: PumpRow, baseline: dict[str, tuple[float, float]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for col in PUMP_SENSOR_COLUMNS:
        mean, std = baseline[col]
        out[col] = abs((row.values[col] - mean) / std)
    return out


def _severity(max_abs_z: float) -> Severity:
    if max_abs_z >= 4.0:
        return "Critical"
    if max_abs_z >= 2.5:
        return "Elevated"
    return "Watching"


def _direction(z: float) -> str:
    return "high" if z >= 0 else "low"


def _manual_for(top_sensors: list[str]) -> list[str]:
    """Keyword match top deviating sensors to the seeded repair manuals."""
    tags = {s.lower() for s in top_sensors}
    manuals: list[str] = []

    if {"vibration", "rpm"} & tags:
        manuals.append("MAN-COMP-01")
        manuals.append("MAN-VIB-01")
    if {"temperature", "pressure"} & tags:
        manuals.append("MAN-COMP-01")
    if {"flow_rate", "pressure"} & tags:
        manuals.append("MAN-COOL-01")

    # dedupe preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for m in manuals:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    if not ordered:
        ordered = ["MAN-COMP-01"]
    return ordered


def _describe(row: PumpRow, baseline: dict[str, tuple[float, float]]) -> tuple[str, str, str]:
    """Return (incident_name, failure_type, description)."""
    abs_z = _abs_z(row, baseline)
    sorted_sensors = sorted(PUMP_SENSOR_COLUMNS, key=lambda c: abs_z[c], reverse=True)
    top1 = sorted_sensors[0]
    top2 = sorted_sensors[1]

    def _signed(col: str) -> float:
        mean, std = baseline[col]
        return (row.values[col] - mean) / std

    dir1 = _direction(_signed(top1))
    dir2 = _direction(_signed(top2))

    pretty = {
        "Temperature": "bearing temperature",
        "Vibration": "vibration",
        "Pressure": "discharge pressure",
        "Flow_Rate": "flow rate",
        "RPM": "shaft speed",
    }

    failure_map = {
        ("Vibration",   "high"): "Rotor imbalance / resonance",
        ("Vibration",   "low"):  "Sensor calibration drift",
        ("Temperature", "high"): "Bearing overheat",
        ("Temperature", "low"):  "Sensor calibration drift",
        ("Pressure",    "high"): "Discharge blockage",
        ("Pressure",    "low"):  "Suction starvation",
        ("Flow_Rate",   "high"): "Bypass leakage",
        ("Flow_Rate",   "low"):  "Impeller degradation",
        ("RPM",         "high"): "Drive overspeed",
        ("RPM",         "low"):  "Drive stall / torque loss",
    }
    failure_type = failure_map.get((top1, dir1), f"{pretty[top1].title()} anomaly")

    incident_name = (
        f"Pump {row.pump_id}: {dir1} {pretty[top1]} with {dir2} {pretty[top2]}"
    )

    description = (
        f"Pump {row.pump_id} at {row.operational_hours:.0f} op-hours exhibited "
        f"{dir1} {pretty[top1]} ({row.values[top1]:.2f} vs nominal "
        f"{baseline[top1][0]:.2f} +/- {baseline[top1][1]:.2f}, "
        f"z={_signed(top1):+.1f}) combined with {dir2} {pretty[top2]} "
        f"({row.values[top2]:.2f} vs nominal {baseline[top2][0]:.2f} +/- "
        f"{baseline[top2][1]:.2f}, z={_signed(top2):+.1f}). "
        "Signature aligned with a maintenance event in the historical record."
    )

    return incident_name, failure_type, description


def _to_signature(row: PumpRow) -> dict[str, float]:
    """Map CSV columns into the backend's SENSOR_ORDER superset."""
    signature: dict[str, float] = {
        "vibration": 0.0,
        "bearing_temp": 0.0,
        "pressure": 0.0,
        "rpm": 0.0,
        "lubricant_pressure": 0.0,
        "humidity": 0.0,
    }
    for col, schema_key in _COLUMN_TO_SCHEMA.items():
        if schema_key in signature:
            signature[schema_key] = row.values[col]
    signature["flow_rate"] = row.values["Flow_Rate"]
    return signature


def build_incidents(
    csv_path: Path = DATASET_PATH,
    n: int = N_INCIDENTS,
) -> list[PastIncident]:
    rows = load_pump_rows(csv_path)
    historical, _ = split_historical_live(rows)

    nominal = [r for r in historical if r.maintenance_flag == 0]
    maintenance = [r for r in historical if r.maintenance_flag == 1]
    if not nominal or not maintenance:
        raise RuntimeError(
            "Historical half of the CSV must contain both nominal and "
            "maintenance rows to build incidents."
        )

    baseline = _baseline(nominal)

    scored: list[tuple[float, PumpRow, dict[str, float]]] = []
    for row in maintenance:
        z = _abs_z(row, baseline)
        agg = math.sqrt(sum(v * v for v in z.values()))
        scored.append((agg, row, z))

    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:n]

    incidents: list[PastIncident] = []
    for agg, row, z in top:
        max_z = max(z.values())
        name, failure_type, description = _describe(row, baseline)
        sorted_sensors = sorted(PUMP_SENSOR_COLUMNS, key=lambda c: z[c], reverse=True)[:2]
        incidents.append(
            PastIncident(
                incident_id=f"PUMP-INC-{row.row_index:05d}",
                incident_name=name,
                failure_type=failure_type,
                severity=_severity(max_z),
                description=description,
                signature=_to_signature(row),
                related_manual_ids=_manual_for(sorted_sensors),
            )
        )

    return incidents


PUMP_PAST_INCIDENTS: list[PastIncident] = []


def ensure_loaded() -> list[PastIncident]:
    """Lazy-populate ``PUMP_PAST_INCIDENTS`` the first time it's needed."""
    if not PUMP_PAST_INCIDENTS:
        PUMP_PAST_INCIDENTS.extend(build_incidents())
    return PUMP_PAST_INCIDENTS
