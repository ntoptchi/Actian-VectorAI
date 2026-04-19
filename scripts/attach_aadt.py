"""Build the AADT spatial index AND back-fill AADT on FARS rows in VDB.

Two modes (both default-on):

  1. ``--build``: build the FDOT AADT spatial index from the shapefile
     under ``data/raw/aadt/aadt.shp`` and pickle it to
     ``data/processed/aadt_index.pkl``. Run after every shapefile refresh.

  2. ``--snap``: scroll the VDB collection for ``source == "FARS"``
     points whose ``aadt`` is missing, look each up via the index, and
     re-upsert with the resolved AADT + segment_id. FDOT rows already
     have AADT pre-attached from the GeoJSON properties so we skip them.

Usage::

    python scripts/attach_aadt.py            # both modes
    python scripts/attach_aadt.py --no-snap  # build only
    python scripts/attach_aadt.py --no-build # snap only (re-use existing pkl)
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


def _build(shp: Path, out: Path, max_match_m: float) -> AadtIndex:
    logger.info("building AADT index from %s", shp)
    index = AadtIndex.build(shp, max_match_m=max_match_m)
    out.parent.mkdir(parents=True, exist_ok=True)
    index.save(out)
    logger.info("wrote %s", out)
    return index


def _snap(index: AadtIndex) -> int:
    """Walk FARS points in the VDB; back-fill AADT where missing.

    Returns the number of points updated.
    """
    try:
        from backend.vdb import get_client
        from backend.config import get_settings as _gs
    except Exception as exc:  # noqa: BLE001
        logger.warning("VDB import failed; skipping snap step: %s", exc)
        return 0

    client = get_client()
    name = _gs().vdb_collection

    n_updated = 0
    n_seen = 0
    offset = None

    while True:
        try:
            page = client.points.scroll(name, limit=512, offset=offset)
        except Exception as exc:  # noqa: BLE001
            logger.warning("scroll failed (collection empty?): %s", exc)
            return n_updated

        # The actian VectorAI client returns (points, next_offset) in
        # most builds; tolerate either tuple or list shape.
        if isinstance(page, tuple) and len(page) == 2:
            points, offset = page
        else:
            points = page
            offset = None

        if not points:
            break

        updates = []
        for pt in points:
            n_seen += 1
            payload = getattr(pt, "payload", None) or {}
            if payload.get("source") != "FARS":
                continue
            if payload.get("aadt"):
                continue
            lat = payload.get("lat")
            lon = payload.get("lon")
            if lat is None or lon is None:
                continue
            match = index.lookup(float(lat), float(lon))
            if match is None:
                continue
            new_payload = dict(payload)
            new_payload["aadt"] = match.aadt
            new_payload["aadt_segment_id"] = match.segment_id
            updates.append((pt.id, new_payload))

        if updates:
            try:
                # Newer client API: set_payload per point.
                for pid, np in updates:
                    client.points.set_payload(name, point_id=pid, payload=np)
                n_updated += len(updates)
            except Exception as exc:  # noqa: BLE001
                logger.warning("set_payload failed: %s", exc)

        if offset is None:
            break

    logger.info("snap complete: %d FARS rows updated (out of %d seen)", n_updated, n_seen)
    return n_updated


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    default_shp_dir = settings.raw_dir / "aadt"
    default_out = settings.processed_dir / "aadt_index.pkl"

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--shapefile",
        type=Path,
        default=None,
        help=f"Path to aadt.shp (default: first .shp under {default_shp_dir})",
    )
    p.add_argument("--out", type=Path, default=default_out)
    p.add_argument("--max-match-m", type=float, default=50.0)
    p.add_argument("--build", dest="build", action="store_true", default=True)
    p.add_argument("--no-build", dest="build", action="store_false")
    p.add_argument("--snap", dest="snap", action="store_true", default=True)
    p.add_argument("--no-snap", dest="snap", action="store_false")
    args = p.parse_args(argv)

    shp = args.shapefile
    if shp is None:
        candidates = sorted(default_shp_dir.glob("*.shp"))
        if not candidates:
            logger.error(
                "no .shp under %s — drop the FGDL AADT bundle there first.",
                default_shp_dir,
            )
            return 1
        shp = candidates[0]

    if args.build:
        index = _build(shp, args.out, args.max_match_m)
    else:
        if not args.out.exists():
            logger.error("--no-build given but no pickled index at %s", args.out)
            return 1
        logger.info("loading cached AADT index from %s", args.out)
        index = AadtIndex.load(args.out)

    if args.snap:
        _snap(index)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
