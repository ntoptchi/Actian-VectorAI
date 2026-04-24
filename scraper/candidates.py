"""
Stage 1 — build the candidate crash subset from FDOT GeoJSON.

Reads every `data/raw/crash*.json` file, filters to the date window
2011-06-11 through 2011-11-07 inclusive (America/New_York calendar day),
keeps only "newsworthy" crashes (fatal / serious injury / vulnerable
road user / wrong-way), tiers each for prioritised processing, and
writes `data/candidates.json`.
"""

from __future__ import annotations

import glob
import json
import logging
import os
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple
from zoneinfo import ZoneInfo

log = logging.getLogger("nextup.candidates")

ET = ZoneInfo("America/New_York")

DATE_START = date(2011, 6, 11)
DATE_END = date(2011, 11, 7)

TIER_FATAL = "fatal"
TIER_SERIOUS = "serious"
TIER_VULNERABLE = "vulnerable"
TIER_WRONGWAY = "wrongway"

TIER_ORDER = [TIER_FATAL, TIER_SERIOUS, TIER_VULNERABLE, TIER_WRONGWAY]

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "data", "raw")
CANDIDATES_PATH = os.path.join(HERE, "data", "candidates.json")


def crash_date_et(epoch_ms: int) -> date:
    """
    FDOT encodes CRASH_DATE as epoch ms corresponding to the crash day
    in Eastern Time. Converting UTC->ET and flooring to date() gives
    the correct calendar day even though the stored instant is a few
    hours off from local midnight.
    """
    dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc).astimezone(ET)
    return dt.date()


def classify_tier(props: Dict[str, Any]) -> Optional[str]:
    """
    Returns the tier string for a newsworthy crash, or None if the crash
    does not meet any serious-only criteria.
    """
    if (props.get("NUMBER_OF_KILLED") or 0) > 0:
        return TIER_FATAL
    if (props.get("NUMBER_OF_SERIOUS_INJURIES") or 0) > 0:
        return TIER_SERIOUS
    if props.get("PEDESTRIAN_RELATED_IND") == "Y":
        return TIER_VULNERABLE
    if props.get("BICYCLIST_RELATED_IND") == "Y":
        return TIER_VULNERABLE
    if props.get("MOTORCYCLE_INVOLVED_IND") == "Y":
        return TIER_VULNERABLE
    if props.get("WRONGWAY_IND") == "Y":
        return TIER_WRONGWAY
    return None


def stable_crash_id(props: Dict[str, Any]) -> str:
    for key in ("CASE_NUMBER", "XID", "CRASH_NUMBER"):
        v = props.get(key)
        if v:
            return str(v)
    return f"OBJECTID_{props.get('OBJECTID')}"


def iter_raw_features(raw_dir: str = RAW_DIR) -> Iterator[Tuple[str, Dict[str, Any]]]:
    pattern = os.path.join(raw_dir, "crash*.json")
    files = sorted(glob.glob(pattern))
    log.info("scanning %d crash*.json files", len(files))
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            log.warning("skipping %s: %s", fp, exc)
            continue
        feats = data.get("features") or []
        for feat in feats:
            yield fp, feat


def build_candidates(
    raw_dir: str = RAW_DIR,
    output_path: str = CANDIDATES_PATH,
    date_start: date = DATE_START,
    date_end: date = DATE_END,
) -> Dict[str, Any]:
    """
    Scan the raw GeoJSON files and persist `candidates.json`.
    Returns the in-memory result too so callers can chain without re-reading.
    """
    kept: List[Dict[str, Any]] = []
    stats = {
        "scanned": 0,
        "in_date_window": 0,
        TIER_FATAL: 0,
        TIER_SERIOUS: 0,
        TIER_VULNERABLE: 0,
        TIER_WRONGWAY: 0,
    }

    for _fp, feat in iter_raw_features(raw_dir):
        stats["scanned"] += 1
        props = feat.get("properties") or {}

        cd = props.get("CRASH_DATE")
        if not isinstance(cd, (int, float)):
            continue

        day = crash_date_et(int(cd))
        if not (date_start <= day <= date_end):
            continue
        stats["in_date_window"] += 1

        tier = classify_tier(props)
        if tier is None:
            continue
        stats[tier] += 1

        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") if isinstance(geom, dict) else None

        kept.append({
            "crash_id": stable_crash_id(props),
            "tier": tier,
            "crash_date": day.isoformat(),
            "geometry": {
                "type": geom.get("type") if isinstance(geom, dict) else None,
                "coordinates": coords,
            },
            "properties": props,
        })

    kept.sort(key=lambda r: (TIER_ORDER.index(r["tier"]), r["crash_date"], r["crash_id"]))

    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "dateRange": {"start": date_start.isoformat(), "end": date_end.isoformat()},
        "filter": "serious_only",
        "stats": stats,
        "count": len(kept),
        "candidates": kept,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tmp = output_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    os.replace(tmp, output_path)

    log.info(
        "candidates built: scanned=%d in_window=%d fatal=%d serious=%d vulnerable=%d wrongway=%d -> %d kept",
        stats["scanned"], stats["in_date_window"],
        stats[TIER_FATAL], stats[TIER_SERIOUS],
        stats[TIER_VULNERABLE], stats[TIER_WRONGWAY],
        len(kept),
    )
    log.info("wrote %s", output_path)
    return out


def load_candidates(path: str = CANDIDATES_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    build_candidates()
