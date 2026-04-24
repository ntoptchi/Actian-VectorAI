"""
Score an extracted article against a crash record. Additive 0..100.

Weights (from plan):
  - Date within +/- 1 day of CRASH_DATE: +30
    Within +/- 3 days:                   +15
    Within +/- 14 days:                  +5
  - COUNTY_TXT (or city) in title+body: +20
  - Road fuzzy match (on_road, int_road, state_road): up to +40
  - Victim counts match ("N killed"/"N dead"): +15
  - crash/accident/collision/wreck keyword present: +5 (required, else disqualified)
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any, Dict, List, Tuple

try:
    from rapidfuzz import fuzz
    _HAS_FUZZ = True
except Exception:
    _HAS_FUZZ = False

log = logging.getLogger("nextup.matcher")

DEFAULT_THRESHOLD = 55
CRASH_KEYWORDS = re.compile(r"\b(crash|accident|collision|wreck|smash|pileup|pile[- ]up)\b", re.I)
KILLED_WORDS = ("killed", "dead", "dies", "died", "fatality", "fatalities", "fatal")


def _normalise(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _date_points(article_date_iso: str, crash_day_iso: str) -> Tuple[int, str]:
    try:
        ad = date.fromisoformat(article_date_iso[:10])
        cd = date.fromisoformat(crash_day_iso[:10])
    except Exception:
        return 0, ""
    delta = abs((ad - cd).days)
    if delta <= 1:
        return 30, f"date_within_1d({delta}d)"
    if delta <= 3:
        return 15, f"date_within_3d({delta}d)"
    if delta <= 14:
        return 5, f"date_within_14d({delta}d)"
    return 0, ""


def _county_points(county_txt: str, blob: str) -> Tuple[int, str]:
    if not county_txt:
        return 0, ""
    c = county_txt.lower().replace("-", " ")
    if c and c in blob:
        return 20, f"county:{county_txt}"
    core = c.split()[0] if c else ""
    if core and len(core) >= 4 and re.search(r"\b" + re.escape(core) + r"\b", blob):
        return 12, f"county_core:{core}"
    return 0, ""


def _road_tokens(road: str) -> List[str]:
    if not road:
        return []
    tokens = [t for t in re.split(r"\s+", road.strip().lower()) if t]
    return tokens


def _road_points(props: Dict[str, Any], title: str, body: str) -> Tuple[int, List[str]]:
    points = 0
    reasons: List[str] = []
    blob = f"{title}\n{body}".lower()

    try:
        from brave import normalize_road_name  # deferred to avoid cycles
    except Exception:
        normalize_road_name = None  # type: ignore

    for key, weight in (("ON_ROADWAY_NAME", 20), ("INT_ROADWAY_NAME", 10)):
        raw = (props.get(key) or "").strip()
        if not raw:
            continue
        forms: List[str] = [raw.lower()]
        if normalize_road_name is not None:
            norm = normalize_road_name(raw).lower()
            if norm and norm not in forms:
                forms.append(norm)

        matched = False
        for form in forms:
            if form and form in blob:
                points += weight
                reasons.append(f"{key.lower()}_exact")
                matched = True
                break
        if matched:
            continue

        if _HAS_FUZZ:
            best = 0
            for form in forms:
                if len(form) < 4:
                    continue
                s = int(fuzz.partial_ratio(form, blob))
                if s > best:
                    best = s
            if best >= 90:
                points += weight
                reasons.append(f"{key.lower()}_fuzzy_{best}")
            elif best >= 80:
                points += weight // 2
                reasons.append(f"{key.lower()}_fuzzy_{best}")

    state_road = (props.get("STATE_ROAD_NUMBER") or "").strip().lower()
    if state_road and state_road in blob:
        points += 10
        reasons.append(f"state_road:{state_road}")

    us_road = props.get("US_ROAD_NUMBER")
    if isinstance(us_road, str) and us_road.strip():
        us_norm = us_road.strip().lower()
        if us_norm in blob:
            points += 10
            reasons.append(f"us_road:{us_norm}")

    return points, reasons


def _victim_points(props: Dict[str, Any], blob: str) -> Tuple[int, List[str]]:
    killed = int(props.get("NUMBER_OF_KILLED") or 0)
    if killed <= 0:
        return 0, []
    for w in KILLED_WORDS:
        pat = re.compile(r"\b" + str(killed) + r"\b[^.]{0,40}\b" + w + r"\b", re.I)
        if pat.search(blob):
            return 15, [f"victims_{killed}_{w}"]
    if re.search(r"\b(fatal|killed|dead)\b", blob, re.I):
        return 8, ["victims_fatal_keyword"]
    return 0, []


def score_match(article: Dict[str, Any], crash: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns { score: int, reasons: [str], disqualified: bool, disqualifyReason?: str }.
    """
    title = _normalise(article.get("title") or "")
    body = _normalise(article.get("text") or "")
    blob = f"{title}\n{body}"

    if not CRASH_KEYWORDS.search(blob):
        return {"score": 0, "reasons": [], "disqualified": True, "disqualifyReason": "no_crash_keyword"}

    if len(body) < 120:
        return {"score": 0, "reasons": [], "disqualified": True, "disqualifyReason": "body_too_short"}

    reasons: List[str] = ["crash_keyword"]
    score = 5

    props = crash.get("properties") or {}

    pub = article.get("publishedDate") or ""
    crash_day = crash.get("crash_date") or ""
    d_pts, d_reason = _date_points(pub, crash_day)
    if d_pts:
        score += d_pts
        reasons.append(d_reason)

    c_pts, c_reason = _county_points((props.get("COUNTY_TXT") or ""), blob)
    if c_pts:
        score += c_pts
        reasons.append(c_reason)

    r_pts, r_reasons = _road_points(props, title, body)
    score += r_pts
    reasons.extend(r_reasons)

    v_pts, v_reasons = _victim_points(props, blob)
    score += v_pts
    reasons.extend(v_reasons)

    for ind, tag in (
        ("PEDESTRIAN_RELATED_IND", "pedestrian"),
        ("BICYCLIST_RELATED_IND", "bicyclist"),
        ("MOTORCYCLE_INVOLVED_IND", "motorcycle"),
        ("WRONGWAY_IND", "wrong-way"),
    ):
        if props.get(ind) == "Y" and tag in blob:
            score += 5
            reasons.append(f"mode:{tag}")

    return {
        "score": min(score, 100),
        "reasons": reasons,
        "disqualified": False,
    }


def pick_best(
    article_candidates: List[Dict[str, Any]],
    crash: Dict[str, Any],
    threshold: int = DEFAULT_THRESHOLD,
) -> Tuple[Dict[str, Any] | None, List[Dict[str, Any]]]:
    """
    Given a list of { url, title, text, publishedDate, ... } article dicts,
    return (best_above_threshold | None, all_scored sorted desc).
    `all_scored` entries have 'matchScore' / 'matchReasons' added.
    """
    scored: List[Dict[str, Any]] = []
    for art in article_candidates:
        res = score_match(art, crash)
        scored.append({
            **art,
            "matchScore": res["score"],
            "matchReasons": res["reasons"],
            "disqualified": res.get("disqualified", False),
            "disqualifyReason": res.get("disqualifyReason"),
        })
    scored.sort(key=lambda a: a["matchScore"], reverse=True)
    best = next((a for a in scored if not a["disqualified"] and a["matchScore"] >= threshold), None)
    return best, scored
