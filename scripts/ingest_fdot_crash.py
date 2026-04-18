"""Ingest FDOT Open Data crash layer (FL non-fatal coverage).

Reads from ``data/raw/FDOT/crash/`` containing the GeoJSON or shapefile
export from https://gis-fdot.opendata.arcgis.com/. We accept both file
formats; geopandas figures out the rest.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings  # noqa: E402
from backend.ingest.normalize import from_fdot_crash_row  # noqa: E402
from backend.ingest.upsert import upsert_docs  # noqa: E402
from backend.schemas import SituationDoc  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("ingest_fdot")


def _iter_features(crash_dir: Path) -> Iterator[dict]:
    """Yield one row dict per FDOT crash feature, with lat/lon attached."""
    try:
        import geopandas as gpd  # type: ignore[import-not-found]
    except ImportError:
        logger.error(
            "geopandas is required for FDOT ingest. "
            "Install via `pip install geopandas`."
        )
        return

    files = list(crash_dir.glob("*.geojson")) + list(crash_dir.glob("*.shp"))
    if not files:
        logger.warning("no .geojson or .shp under %s", crash_dir)
        return

    for f in files:
        logger.info("reading %s", f)
        gdf = gpd.read_file(f).to_crs(4326)
        for _, row in gdf.iterrows():
            d = row.to_dict()
            geom = row.geometry
            if geom is not None and not geom.is_empty:
                d["__lat"] = float(geom.y)
                d["__lon"] = float(geom.x)
            yield d


def _docs(limit: int | None) -> Iterator[SituationDoc]:
    crash_dir = get_settings().raw_dir / "FDOT" / "crash"
    if not crash_dir.exists():
        logger.warning("missing FDOT crash dir %s", crash_dir)
        return

    n = 0
    for row in _iter_features(crash_dir):
        try:
            doc = from_fdot_crash_row(row)
        except NotImplementedError:
            logger.error(
                "from_fdot_crash_row is still a stub. Implement it before "
                "running ingest_fdot_crash."
            )
            return
        if doc is None:
            continue
        yield doc
        n += 1
        if limit is not None and n >= limit:
            return


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--batch-size", type=int, default=512)
    args = p.parse_args(argv)
    n = upsert_docs(_docs(args.limit), batch_size=args.batch_size)
    logger.info("FDOT ingest complete: %d points upserted", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
