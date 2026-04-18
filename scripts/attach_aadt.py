"""Build the AADT spatial index from the FGDL shapefile.

Run after the AADT shapefile is downloaded to ``data/raw/FGDL/aadt/``.
The pickled index is dropped at ``data/processed/aadt_index.pkl`` and
loaded on demand by ingestion + (later) cluster ranking.

Per ROUTEWISE.md s5.1.4, AADT is attached *during* crash ingestion via
``AadtIndex.lookup``; this script just builds the index. After it runs,
re-running ingest_* will populate ``aadt`` / ``aadt_segment_id`` on every
indexed crash whose lat/lon snaps within 50 m of an AADT segment.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings  # noqa: E402
from backend.ingest.aadt import AadtIndex  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("attach_aadt")


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    default_shp_dir = settings.raw_dir / "FGDL" / "aadt"
    default_out = settings.processed_dir / "aadt_index.pkl"

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--shapefile",
        type=Path,
        default=None,
        help=f"Path to FGDL aadt_*.shp (default: first .shp under {default_shp_dir})",
    )
    p.add_argument("--out", type=Path, default=default_out)
    p.add_argument("--max-match-m", type=float, default=50.0)
    args = p.parse_args(argv)

    shp = args.shapefile
    if shp is None:
        candidates = sorted(default_shp_dir.glob("*.shp"))
        if not candidates:
            logger.error(
                "no .shp under %s — download the FGDL AADT layer first "
                "(see data/README.md).",
                default_shp_dir,
            )
            return 1
        shp = candidates[0]

    logger.info("building AADT index from %s", shp)
    index = AadtIndex.build(shp, max_match_m=args.max_match_m)
    index.save(args.out)
    logger.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
