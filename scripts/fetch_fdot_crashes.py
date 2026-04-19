"""Pull FDOT crash GeoJSON chunks via the ArcGIS REST API.

Cross-platform replacement for ``data/raw/fetch_crashes.sh`` (bash + curl).
Runs from PowerShell on Windows without WSL/Git-bash quoting headaches.

Each call fetches ``CHUNK_SIZE`` (default 1000) records by OBJECTID range
and writes ``data/raw/crash{upper}.json``. Existing files are skipped.

Usage::

    python scripts/fetch_fdot_crashes.py --start 51 --end 150
    python scripts/fetch_fdot_crashes.py --start 1 --end 50 --force

This intentionally mirrors the bash script's naming convention so the
existing ``ingest_fdot_crash.py`` ingester picks up the new files via its
``crash*.json`` glob without any changes.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("fetch_fdot")

BASE_URL = "https://gis.fdot.gov/arcgis/rest/services/Crashes_All/FeatureServer/0/query"
CHUNK_SIZE = 1000
TIMEOUT_S = 90
RETRIES = 4


def _fetch_chunk(lower: int, upper: int, out_path: Path) -> bool:
    """Fetch one [lower, upper) OBJECTID slice into ``out_path``.

    Returns True on success, False after exhausting retries. Validates
    that the response is non-trivial JSON (>1KB) so we don't silently
    save error bodies as success.
    """
    params = {
        "where": f"OBJECTID >= {lower} AND OBJECTID < {upper}",
        "outFields": "*",
        "f": "geojson",
    }
    url = f"{BASE_URL}?{urlencode(params)}"
    last_err: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = Request(url, headers={"User-Agent": "routewise-ingest/1.0"})
            with urlopen(req, timeout=TIMEOUT_S) as resp:
                body = resp.read()
            if len(body) < 1024:
                # ArcGIS error responses (e.g. {"error":...}) are tiny;
                # treat as failure and retry.
                raise ValueError(f"suspiciously small response ({len(body)} bytes)")
            tmp_path = out_path.with_suffix(out_path.suffix + ".part")
            tmp_path.write_bytes(body)
            tmp_path.replace(out_path)
            return True
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            backoff = min(30, 2 ** attempt)
            logger.warning(
                "  attempt %d/%d for %s failed: %s — retrying in %ds",
                attempt, RETRIES, out_path.name, exc, backoff,
            )
            time.sleep(backoff)
    logger.error("  giving up on %s after %d attempts (%s)", out_path.name, RETRIES, last_err)
    return False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", type=int, required=True, help="First chunk index (1 = OBJECTID 0..999)")
    p.add_argument("--end", type=int, required=True, help="Last chunk index, inclusive")
    p.add_argument("--out-dir", type=Path, default=Path("data/raw"))
    p.add_argument("--force", action="store_true", help="Re-fetch even if the file exists")
    args = p.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    fetched = 0
    skipped = 0
    failed = 0
    for n in range(args.start, args.end + 1):
        upper = n * CHUNK_SIZE
        lower = upper - CHUNK_SIZE
        out = args.out_dir / f"crash{upper}.json"

        if out.exists() and not args.force:
            skipped += 1
            continue

        logger.info("[%d/%d] fetching crash%d.json (OBJECTID %d..%d)",
                    n - args.start + 1, args.end - args.start + 1, upper, lower, upper - 1)
        if _fetch_chunk(lower, upper, out):
            fetched += 1
        else:
            failed += 1

    logger.info("done: %d fetched, %d skipped, %d failed", fetched, skipped, failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
