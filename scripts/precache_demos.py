"""Pre-cache /trip/brief responses for the demo trips.

Hits the local FastAPI backend (must be running on :8000) and writes
each response under ``data/cache/trip/<slug>.json``. The backend
loads these on startup; if a request matches a cached trip+departure
within 1 minute, it serves the cached payload — avoids ORS and VDB
roundtrips during the demo.

Usage::

    uvicorn backend.main:app &
    python scripts/precache_demos.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib import request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("precache_demos")


# (slug, lat/lon origin, lat/lon destination, departure-hour-of-day)
DEMO_TRIPS = [
    ("miami-tampa-evening", (25.7617, -80.1918), (27.9506, -82.4572), 18),
    ("miami-tampa-rainy-night", (25.7617, -80.1918), (27.9506, -82.4572), 22),
    ("jax-pensacola-day", (30.3322, -81.6557), (30.4213, -87.2169), 10),
    ("jax-pensacola-night", (30.3322, -81.6557), (30.4213, -87.2169), 21),
    ("orlando-tampa-evening", (28.5383, -81.3792), (27.9506, -82.4572), 19),
]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default="http://localhost:8000")
    args = p.parse_args(argv)

    out_dir = get_settings().cache_dir / "trip"
    out_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).date()
    for slug, origin, dest, hour in DEMO_TRIPS:
        ts = datetime.combine(
            today + timedelta(days=1),
            datetime.min.time().replace(hour=hour),
            tzinfo=timezone.utc,
        )
        body = {
            "origin": {"lat": origin[0], "lon": origin[1]},
            "destination": {"lat": dest[0], "lon": dest[1]},
            "timestamp": ts.isoformat(),
        }
        url = f"{args.base}/trip/brief"
        logger.info("hitting %s for %s", url, slug)
        try:
            req = request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=120) as resp:  # noqa: S310
                payload = resp.read()
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed: %s", exc)
            continue
        path = out_dir / f"{slug}.json"
        path.write_bytes(payload)
        logger.info("cached %s (%.1fkb)", path.name, len(payload) / 1024)

    logger.info("done. %d trips cached under %s", len(DEMO_TRIPS), out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
