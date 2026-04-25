"""
Brave Search API client with a token-bucket rate limiter.

Docs: https://api.search.brave.com/app/documentation/web-search/get-started

The free tier is 1 req/sec. We default to that and allow BRAVE_RPS to
override from env for paid plans.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from datetime import date
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter

log = logging.getLogger("nextup.brave")

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


class BraveError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class TokenBucket:
    """Thread-safe token bucket rate limiter."""

    def __init__(self, rps: float, burst: Optional[float] = None):
        self.rate = max(rps, 1e-6)
        self.capacity = burst if burst is not None else max(rps, 1.0)
        self.tokens = self.capacity
        self.last = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
                self.last = now
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                needed = 1.0 - self.tokens
                wait = needed / self.rate
            time.sleep(wait)


class BraveClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        rps: Optional[float] = None,
        session: Optional[requests.Session] = None,
    ):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            raise BraveError("BRAVE_API_KEY is not set (checked env + .env via load_dotenv)")
        # Brave's Data-for-Search plan allows up to 50 rps; free tier is 1 rps.
        # Default to 20 (safely below the paid ceiling); override via BRAVE_RPS=1
        # in .env if you're on the free tier.
        rps_val = rps if rps is not None else float(os.getenv("BRAVE_RPS", "20.0"))
        self.bucket = TokenBucket(rps_val)
        self.session = session or requests.Session()
        # Default urllib3 pool is 10 connections — far too small for the 20+
        # parallel workers the linker spawns. Mount an adapter sized to the
        # rate limit so connections are reused instead of rebuilt per request.
        pool_size = max(32, int(rps_val) * 2)
        adapter = HTTPAdapter(
            pool_connections=pool_size,
            pool_maxsize=pool_size,
            max_retries=0,
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        })

    def search(
        self,
        query: str,
        *,
        count: int = 10,
        freshness: Optional[str] = None,
        country: str = "us",
        search_lang: str = "en",
        max_attempts: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Execute a Brave web search. Returns a list of
        { url, title, description, age } dicts (possibly empty).
        """
        params: Dict[str, Any] = {
            "q": query,
            "count": max(1, min(count, 20)),
            "country": country,
            "search_lang": search_lang,
            "safesearch": "moderate",
        }
        if freshness:
            params["freshness"] = freshness

        last_err: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            self.bucket.acquire()
            try:
                res = self.session.get(BRAVE_ENDPOINT, params=params, timeout=20)
            except Exception as exc:
                last_err = exc
                log.warning("brave network error (attempt %d/%d): %s", attempt, max_attempts, exc)
                time.sleep(min(2 ** attempt, 15))
                continue

            if res.status_code == 429:
                retry_after = res.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.replace(".", "", 1).isdigit() else min(2 ** attempt, 30)
                log.warning("brave 429 rate-limited, sleeping %.1fs", wait)
                time.sleep(wait)
                continue

            if 200 <= res.status_code < 300:
                try:
                    data = res.json()
                except Exception as exc:
                    raise BraveError(f"invalid JSON from Brave: {exc}") from exc
                return _parse_web_results(data)

            body_peek = (res.text or "")[:300].replace("\n", " ")
            log.warning("brave HTTP %d (attempt %d/%d): %s", res.status_code, attempt, max_attempts, body_peek)
            last_err = BraveError(f"HTTP {res.status_code}: {body_peek}", res.status_code)
            if res.status_code in (500, 502, 503, 504):
                time.sleep(min(2 ** attempt, 15))
                continue
            raise last_err

        raise last_err or BraveError(f"brave search exhausted retries for {query!r}")


def _parse_web_results(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    web = (data.get("web") or {}).get("results") or []
    for r in web:
        url = r.get("url")
        if not url:
            continue
        out.append({
            "url": url,
            "title": r.get("title") or "",
            "description": r.get("description") or "",
            "age": r.get("age") or r.get("page_age") or "",
            "source": "web",
        })
    news = (data.get("news") or {}).get("results") or []
    for r in news:
        url = r.get("url")
        if not url:
            continue
        out.append({
            "url": url,
            "title": r.get("title") or "",
            "description": r.get("description") or "",
            "age": r.get("age") or r.get("page_age") or "",
            "source": "news",
        })
    return out


def freshness_range(start: date, end: date) -> str:
    """Brave supports a custom freshness window as YYYY-MM-DDtoYYYY-MM-DD.

    Empirical note: for >10-year-old archival content, `freshness` appears
    to *hurt* recall rather than help, so linker.py no longer passes this.
    """
    return f"{start.isoformat()}to{end.isoformat()}"


# Road-type abbreviation expansion. News articles use colloquial spellings,
# not FDOT shorthand — so we generate both forms and issue multiple queries.
_ROAD_TYPE_EXPANSIONS = {
    "RD": "Road",
    "ST": "Street",
    "AVE": "Avenue",
    "AV": "Avenue",
    "BLVD": "Boulevard",
    "PKY": "Parkway",
    "PKWY": "Parkway",
    "HWY": "Highway",
    "TR": "Trail",
    "TRL": "Trail",
    "DR": "Drive",
    "CT": "Court",
    "LN": "Lane",
    "PL": "Place",
    "TER": "Terrace",
    "WAY": "Way",
    "CIR": "Circle",
    "BCH": "Beach",
    "EXPY": "Expressway",
    "TPKE": "Turnpike",
}

_DIRECTIONAL_EXPANSIONS = {
    "N": "North", "S": "South", "E": "East", "W": "West",
    "NE": "Northeast", "NW": "Northwest", "SE": "Southeast", "SW": "Southwest",
}

_ORDINAL_PATTERN = re.compile(r"^(\d+)(ST|ND|RD|TH)$", re.I)


def _titlecase_ordinal(token: str) -> str:
    """`268TH` -> `268th`, preserving the number and lowercasing the suffix."""
    m = _ORDINAL_PATTERN.match(token)
    if m:
        return f"{m.group(1)}{m.group(2).lower()}"
    return token


def normalize_road_name(raw: str) -> str:
    """
    Convert FDOT-style road strings to the form typical in news articles:
      "SW 268TH ST"      -> "SW 268th Street"
      "COMMERCE PKY"     -> "Commerce Parkway"
      "MILITARY TR"      -> "Military Trail"
      "SR 19"            -> "State Road 19"
      "US 27"            -> "US 27"
      "I 95" / "I-95"    -> "I-95"
    The directional prefix and ordinals are preserved; road-type abbreviations
    are expanded; the rest is title-cased.
    """
    if not raw:
        return ""
    s = raw.strip()

    su = s.upper()
    if re.match(r"^I[\s\-]?\d+$", su):
        num = re.sub(r"\D", "", su)
        return f"I-{num}"
    if re.match(r"^US[\s\-]?\d+$", su):
        num = re.sub(r"\D", "", su)
        return f"US {num}"
    if re.match(r"^SR[\s\-]?\d+[A-Z]?$", su):
        m = re.match(r"^SR[\s\-]?(\d+[A-Z]?)$", su)
        return f"State Road {m.group(1).upper()}"
    if re.match(r"^CR[\s\-]?\d+[A-Z]?$", su):
        m = re.match(r"^CR[\s\-]?(\d+[A-Z]?)$", su)
        return f"County Road {m.group(1).upper()}"

    tokens = re.split(r"\s+", s)
    out: List[str] = []
    last_idx = len(tokens) - 1
    for i, tok in enumerate(tokens):
        u = tok.upper()
        if i == 0 and u in _DIRECTIONAL_EXPANSIONS:
            out.append(u)
            continue
        if i == last_idx and u in _ROAD_TYPE_EXPANSIONS:
            out.append(_ROAD_TYPE_EXPANSIONS[u])
            continue
        if _ORDINAL_PATTERN.match(tok):
            out.append(_titlecase_ordinal(tok))
            continue
        if u.isdigit() or all(c.isdigit() or c == "-" for c in u):
            out.append(u)
            continue
        if len(u) <= 3 and u.isalpha() and u in _DIRECTIONAL_EXPANSIONS:
            out.append(u)
            continue
        out.append(tok.capitalize())
    return " ".join(out)


def build_queries(crash: Dict[str, Any]) -> List[str]:
    """
    Build up to ~4 query variants for a crash, ordered from most specific
    to most general. The caller issues variant N+1 only if variant N returns
    zero usable hits.

    Variants:
      1. "<normalized primary road>" <county> county Florida <modifier> crash <date>
      2. "<raw primary road>" <county> county Florida <modifier> crash <date>
         (kept in case original spelling appears verbatim in older copy)
      3. "<normalized primary road>" "<normalized int road>" Florida <date>
      4. <county> county Florida <modifier> crash <date>
    """
    props = crash.get("properties") or {}
    county = (props.get("COUNTY_TXT") or "").title()
    on_road_raw = (props.get("ON_ROADWAY_NAME") or "").strip()
    int_road_raw = (props.get("INT_ROADWAY_NAME") or "").strip()
    state_road = (props.get("STATE_ROAD_NUMBER") or "").strip()
    us_road = (props.get("US_ROAD_NUMBER") or "")
    us_road = us_road.strip() if isinstance(us_road, str) else ""

    primary_raw = on_road_raw or state_road or us_road
    primary_norm = normalize_road_name(primary_raw)
    int_norm = normalize_road_name(int_road_raw)

    date_str = crash.get("crash_date") or ""
    try:
        d = date.fromisoformat(date_str)
        pretty_date = d.strftime("%B %#d, %Y") if os.name == "nt" else d.strftime("%B %-d, %Y")
    except Exception:
        pretty_date = date_str

    killed = props.get("NUMBER_OF_KILLED") or 0
    peds = props.get("NUMBER_OF_PEDESTRIANS") or 0
    moto = props.get("MOTORCYCLE_INVOLVED_IND") == "Y"
    bike = props.get("BICYCLIST_RELATED_IND") == "Y"
    wrongway = props.get("WRONGWAY_IND") == "Y"

    modifier_bits: List[str] = []
    if killed >= 2:
        modifier_bits.append(f"{killed} killed")
    elif killed == 1:
        modifier_bits.append("fatal")
    if peds > 0 or props.get("PEDESTRIAN_RELATED_IND") == "Y":
        modifier_bits.append("pedestrian")
    if moto:
        modifier_bits.append("motorcycle")
    if bike:
        modifier_bits.append("bicyclist")
    if wrongway:
        modifier_bits.append("wrong-way")
    modifier = " ".join(modifier_bits)

    queries: List[str] = []

    def _make(parts: List[str]) -> str:
        return re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()

    if primary_norm:
        queries.append(_make([
            f'"{primary_norm}"', county, "county Florida", modifier, "crash", pretty_date,
        ]))

    if primary_raw and primary_raw.upper() != primary_norm.upper():
        queries.append(_make([
            f'"{primary_raw}"', county, "county Florida", modifier, "crash", pretty_date,
        ]))

    if primary_norm and int_norm:
        queries.append(_make([
            f'"{primary_norm}"', f'"{int_norm}"', "Florida", modifier, "crash", pretty_date,
        ]))

    queries.append(_make([
        county, "county Florida", modifier or "crash", pretty_date,
    ]))

    seen = set()
    dedup: List[str] = []
    for q in queries:
        if q and q not in seen:
            seen.add(q)
            dedup.append(q)
    return dedup
