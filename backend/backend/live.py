"""Transform ``LiveState`` into the DashboardState shape the React app expects.

Mirrors the type aliases in ``src/data/dashboardData.ts`` 1:1. The goal is
that the frontend can replace its static imports with a single
``GET /state/dashboard`` call and get the same keys.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .schemas import AnomalyReport, SensorReading
from .state import LiveState


# Static rig topology, duplicated from ``src/data/dashboardData.ts`` so the
# backend can overlay live per-asset status and anomaly scores onto it.
_RIG_TOPOLOGY: dict[str, Any] = {
    "rigId": "rig-north-atlas-07",
    "rigName": "North Atlas 07",
    "viewLabel": "System layout by operating zone",
    "zones": [
        {"id": "compression", "label": "Compression", "x": 6,  "y": 10, "width": 34, "height": 34, "description": "Compression and rotating equipment"},
        {"id": "cooling",     "label": "Cooling",     "x": 44, "y": 10, "width": 22, "height": 34, "description": "Heat exchange and loop control"},
        {"id": "power",       "label": "Power",       "x": 69, "y": 10, "width": 25, "height": 34, "description": "Generation and distribution"},
        {"id": "safety",      "label": "Safety",      "x": 6,  "y": 50, "width": 30, "height": 30, "description": "Gas detection and response"},
        {"id": "storage",     "label": "Storage",     "x": 40, "y": 50, "width": 25, "height": 30, "description": "Buffer tanks and containment"},
        {"id": "drilling",    "label": "Drilling",    "x": 69, "y": 50, "width": 25, "height": 30, "description": "Mud handling and drill-floor systems"},
    ],
    "assets": [
        {"id": "compressor-03",     "label": "Compressor-03",     "shortLabel": "C-03",  "type": "Compressor",     "zoneId": "compression", "x": 18, "y": 21, "status": "normal", "anomalyScore": 0, "metricValue": "", "lastUpdated": ""},
        {"id": "valve-12",          "label": "Valve-12",          "shortLabel": "V-12",  "type": "Control valve",  "zoneId": "compression", "x": 31, "y": 32, "status": "normal", "anomalyScore": 0, "metricValue": "", "lastUpdated": ""},
        {"id": "pump-07",           "label": "Pump-07",           "shortLabel": "P-07",  "type": "Cooling pump",   "zoneId": "cooling",     "x": 51, "y": 24, "status": "normal", "anomalyScore": 0, "metricValue": "", "lastUpdated": ""},
        {"id": "heat-exchanger-2",  "label": "Heat Exchanger-2",  "shortLabel": "HX-2",  "type": "Heat exchanger", "zoneId": "cooling",     "x": 59, "y": 34, "status": "normal", "anomalyScore": 0, "metricValue": "", "lastUpdated": ""},
        {"id": "generator-02",      "label": "Generator-02",      "shortLabel": "G-02",  "type": "Generator",      "zoneId": "power",       "x": 78, "y": 22, "status": "normal", "anomalyScore": 0, "metricValue": "Load stable", "lastUpdated": ""},
        {"id": "switchgear-01",     "label": "Switchgear-01",     "shortLabel": "SG-1",  "type": "Switchgear",     "zoneId": "power",       "x": 87, "y": 33, "status": "offline", "anomalyScore": 0, "metricValue": "Maintenance isolation", "lastUpdated": ""},
        {"id": "gas-sensor-a",      "label": "Gas Sensor-A",      "shortLabel": "GS-A",  "type": "Gas sensor",     "zoneId": "safety",      "x": 16, "y": 63, "status": "normal", "anomalyScore": 0, "metricValue": "", "lastUpdated": ""},
        {"id": "fire-suppression-1","label": "Fire Suppression-1","shortLabel": "FS-1",  "type": "Safety system",  "zoneId": "safety",      "x": 27, "y": 72, "status": "normal", "anomalyScore": 6, "metricValue": "Armed", "lastUpdated": ""},
        {"id": "tank-04",           "label": "Tank-04",           "shortLabel": "T-04",  "type": "Storage tank",   "zoneId": "storage",     "x": 49, "y": 63, "status": "normal", "anomalyScore": 0, "metricValue": "", "lastUpdated": ""},
        {"id": "mud-pump-02",       "label": "Mud Pump-02",       "shortLabel": "MP-2",  "type": "Mud pump",       "zoneId": "drilling",    "x": 80, "y": 63, "status": "normal", "anomalyScore": 12, "metricValue": "Pressure nominal", "lastUpdated": ""},
    ],
    "links": [
        {"id": "l1", "fromAssetId": "compressor-03", "toAssetId": "pump-07"},
        {"id": "l2", "fromAssetId": "pump-07",       "toAssetId": "generator-02"},
        {"id": "l3", "fromAssetId": "compressor-03", "toAssetId": "gas-sensor-a"},
        {"id": "l4", "fromAssetId": "valve-12",      "toAssetId": "tank-04"},
    ],
}


_SEVERITY_TO_STATUS = {
    "Critical": "critical",
    "Elevated": "warning",
    "Watching": "watch",
}


def _hhmm(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%H:%M")


def _pct_deviation(value: float, expected: float) -> str:
    if expected == 0:
        return f"{value:+.2f}"
    pct = 100.0 * (value - expected) / max(abs(expected), 1e-6)
    return f"{pct:+.0f}%"


def _sensor_unit(sensor: str) -> str:
    return {
        "vibration": "mm/s",
        "bearing_temp": "C",
        "pressure": "bar",
        "rpm": "rpm",
        "lubricant_pressure": "bar",
        "humidity": "%RH",
    }.get(sensor, "")


def _anomaly_score(report: AnomalyReport) -> int:
    """Map the worst |z| to a 0-100 dashboard score."""
    worst = max(abs(d.z_score) for d in report.anomaly.deviations)
    # z=0 -> 0, z=3 -> 60, z=6 -> 95 (asymptotic)
    score = min(100.0, 100.0 * (1.0 - pow(0.55, worst / 2.0)))
    return int(round(score))


def _metrics(live: LiveState) -> list[dict[str, str]]:
    statuses = live.asset_status()
    recent = live.recent_reports()
    active = sum(1 for s in statuses.values() if s in ("Critical", "Elevated"))
    affected = len({a for a, s in statuses.items() if s in ("Critical", "Elevated")})
    linked = sum(len(r.matches) for r in recent)
    return [
        {"label": "Active excursions",   "value": str(active),   "change": f"+{active} live", "trend": "up"},
        {"label": "Systems affected",    "value": str(affected), "change": f"{affected} assets", "trend": "up" if affected else "down"},
        {"label": "Prior events linked", "value": str(linked),   "change": "live VectorAI",  "trend": "up"},
        {"label": "Median restore path", "value": "~20 min",     "change": "historical",      "trend": "down"},
    ]


def _alert_summary(live: LiveState) -> list[dict[str, str]]:
    reports = live.recent_reports()
    critical = [r for r in reports if r.anomaly.severity == "Critical"]
    top = critical[-1] if critical else (reports[-1] if reports else None)
    if top is None:
        return [
            {"label": "Critical window",  "value": "--",       "detail": "No live anomalies",      "severity": "Watching"},
            {"label": "Affected asset",   "value": "--",       "detail": "Awaiting ingest",        "severity": "Watching"},
            {"label": "Top driver",       "value": "--",       "detail": "",                        "severity": "Watching"},
            {"label": "Match confidence", "value": "--",       "detail": "",                        "severity": "Watching"},
        ]
    worst = max(top.anomaly.deviations, key=lambda d: abs(d.z_score))
    best_match = top.matches[0] if top.matches else None
    conf = f"{int(round(best_match.score * 100))}%" if best_match else "--"
    conf_detail = best_match.incident.incident_name if best_match else "No prior match"
    return [
        {
            "label": "Critical window",
            "value": _hhmm(top.anomaly.ts),
            "detail": top.anomaly.summary,
            "severity": top.anomaly.severity,
        },
        {
            "label": "Affected asset",
            "value": top.anomaly.asset_id,
            "detail": f"Rig {top.anomaly.rig_id}",
            "severity": top.anomaly.severity,
        },
        {
            "label": "Top driver",
            "value": worst.sensor.replace("_", " "),
            "detail": f"z={worst.z_score:+.1f} vs baseline",
            "severity": "Elevated",
        },
        {
            "label": "Match confidence",
            "value": conf,
            "detail": conf_detail,
            "severity": "Elevated",
        },
    ]


def _anomalies(live: LiveState) -> list[dict[str, Any]]:
    reports = list(reversed(live.recent_reports()))[:4]
    out: list[dict[str, Any]] = []
    for i, r in enumerate(reports):
        worst = max(r.anomaly.deviations, key=lambda d: abs(d.z_score))
        unit = _sensor_unit(worst.sensor)
        out.append({
            "id": f"AN-{r.anomaly.ts.strftime('%H%M%S')}-{i}",
            "metric": worst.sensor.replace("_", " ").title(),
            "value": f"{worst.value:.2f} {unit}".strip(),
            "expected": f"{worst.expected_mean:.2f} {unit}".strip(),
            "deviation": _pct_deviation(worst.value, worst.expected_mean),
            "severity": r.anomaly.severity,
            "scope": f"{r.anomaly.asset_id} / {r.anomaly.rig_id}",
            "signal": r.anomaly.summary,
        })
    return out


def _incident_matches(live: LiveState) -> list[dict[str, Any]]:
    reports = live.recent_reports()
    critical = [r for r in reports if r.anomaly.severity == "Critical"]
    top = critical[-1] if critical else (reports[-1] if reports else None)
    if top is None:
        return []
    out: list[dict[str, Any]] = []
    for m in top.matches[:3]:
        out.append({
            "id": m.incident.incident_id,
            "incident": m.incident.incident_name,
            "similarity": int(round(m.score * 100)),
            "cause": m.incident.failure_type,
            "resolution": m.incident.description[:160],
            "impact": f"Signature z={max(abs(d.z_score) for d in top.anomaly.deviations):.1f}",
            "owner": "Reliability Engineering",
        })
    return out


def _insights(live: LiveState) -> list[dict[str, str]]:
    reports = live.recent_reports()
    critical = [r for r in reports if r.anomaly.severity == "Critical"]
    top = critical[-1] if critical else (reports[-1] if reports else None)
    if top is None or not top.guidance:
        return []
    out: list[dict[str, str]] = []
    labels = ("Probable failure mode", "Fastest prior recovery", "Next field action")
    for label, hit in zip(labels, top.guidance[:3]):
        out.append({
            "title": label,
            "detail": f"{hit.manual.manual_name}: {hit.best_chunk.text}",
        })
    return out


def _anomaly_chart(live: LiveState) -> list[dict[str, Any]]:
    statuses = live.asset_status()
    hot = next(
        (a for a, s in statuses.items() if s == "Critical"),
        next((a for a, s in statuses.items() if s == "Elevated"), None),
    )
    if hot is None:
        windows = live.all_windows()
        if not windows:
            return []
        hot = next(iter(windows))
    window = live.window(hot)[-15:]
    report = live.asset_reports().get(hot)
    baseline_mean = 0.0
    baseline_std = 0.0
    if report is not None:
        vib = next((d for d in report.anomaly.deviations if d.sensor == "vibration"), None)
        if vib is not None:
            baseline_mean = vib.expected_mean
            baseline_std = vib.expected_std
    out: list[dict[str, Any]] = []
    for r in window:
        value = float(r.values.get("vibration", 0.0))
        z = abs(value - baseline_mean) / baseline_std if baseline_std > 0 else 0.0
        severity = "Critical" if z >= 6 else ("Elevated" if z >= 3 else "Watching")
        out.append({
            "timestamp": _hhmm(r.ts),
            "actual": round(value, 2),
            "expectedMin": round(baseline_mean - baseline_std, 2),
            "expectedMax": round(baseline_mean + baseline_std, 2),
            "severity": severity,
        })
    return out


def _topology(live: LiveState) -> dict[str, Any]:
    statuses = live.asset_status()
    reports = live.asset_reports()
    topo: dict[str, Any] = {
        "rigId": _RIG_TOPOLOGY["rigId"],
        "rigName": _RIG_TOPOLOGY["rigName"],
        "viewLabel": _RIG_TOPOLOGY["viewLabel"],
        "zones": _RIG_TOPOLOGY["zones"],
        "links": _RIG_TOPOLOGY["links"],
        "assets": [],
    }
    for asset in _RIG_TOPOLOGY["assets"]:
        aid = asset["id"]
        overlay = dict(asset)
        sev = statuses.get(aid)
        if sev is not None:
            overlay["status"] = _SEVERITY_TO_STATUS.get(sev, overlay["status"])
            report = reports.get(aid)
            if report is not None:
                overlay["anomalyScore"] = _anomaly_score(report)
                worst = max(report.anomaly.deviations, key=lambda d: abs(d.z_score))
                unit = _sensor_unit(worst.sensor)
                overlay["metricValue"] = f"{worst.value:.2f} {unit}".strip()
                overlay["lastUpdated"] = _hhmm(report.anomaly.ts)
        topo["assets"].append(overlay)
    return topo


def _response_timeline(live: LiveState) -> list[str]:
    timeline = live.timeline()
    if timeline:
        return timeline[-5:]
    return []


def build_dashboard_state(live: LiveState) -> dict[str, Any]:
    return {
        "metrics": _metrics(live),
        "alertSummary": _alert_summary(live),
        "anomalies": _anomalies(live),
        "incidentMatches": _incident_matches(live),
        "insights": _insights(live),
        "anomalyChart": _anomaly_chart(live),
        "responseTimeline": _response_timeline(live),
        "rigTopology": _topology(live),
        "stats": live.stats(),
    }


__all__ = ["build_dashboard_state"]

# Expose the sensor reading type for server-side ingestion callers.
_SensorReading = SensorReading
