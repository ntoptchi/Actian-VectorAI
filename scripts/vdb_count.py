"""Print the number of points in the configured VDB collection.

Returns exit code 0 if the collection has >= ``--min`` points, 1 otherwise.
Used by install.sh / start.sh to decide whether seeding has already
happened (so re-runs are cheap).

Usage::

    python scripts/vdb_count.py                  # just print count
    python scripts/vdb_count.py --min 10000      # exit 1 if fewer
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _count() -> int:
    from backend.config import get_settings
    from backend.vdb import ensure_collection, get_client

    ensure_collection()
    client = get_client()
    name = get_settings().vdb_collection

    # The actian_vectorai client exposes ``points.count`` on most builds,
    # but some older wheels only have ``collections.info(name).points_count``.
    # Try both before falling back to a scrolled total.
    try:
        return int(client.points.count(name))  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        info = client.collections.info(name)  # type: ignore[attr-defined]
        for attr in ("points_count", "vectors_count", "count"):
            v = getattr(info, attr, None)
            if v is not None:
                return int(v)
    except Exception:
        pass

    # Last resort: scroll the whole collection. Slow on large data, but
    # only ever invoked by the bootstrap scripts.
    total = 0
    offset = None
    while True:
        try:
            page = client.points.scroll(name, limit=1024, offset=offset)
        except Exception:
            return total
        if isinstance(page, tuple) and len(page) == 2:
            pts, offset = page
        else:
            pts = page
            offset = None
        total += len(pts) if pts else 0
        if not pts or offset is None:
            return total


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--min", type=int, default=0, help="Exit 1 if count < min")
    args = p.parse_args(argv)

    try:
        n = _count()
    except Exception as exc:
        print(f"[vdb_count] failed: {exc}", file=sys.stderr)
        return 1

    print(n)
    return 0 if n >= args.min else 1


if __name__ == "__main__":
    raise SystemExit(main())
