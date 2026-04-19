"""Diagnostic: walk the same code path /trip/brief takes, but instrument
each step so we can see where the retrieval pipeline is starving.

Specifically we want to know, for a Miami->Tampa 5pm trip:
  - how many H3 cells the route covers
  - how many crashes the VDB holds in those cells (ground truth, no
    embedding filter)
  - how many the actual semantic search returns when post-filtered
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings  # noqa: E402
from backend.embeddings import embed_one  # noqa: E402
from backend.ingest.situation_doc import render_narrative  # noqa: E402
from backend.schemas import LatLon, SituationDoc  # noqa: E402
from backend.services import routing, segments as segments_svc  # noqa: E402
from backend.services.scoring import build_query_doc  # noqa: E402
from backend.vdb import get_client  # noqa: E402


async def _get_route_cells():
    origin = LatLon(lat=25.7617, lon=-80.1918)
    dest = LatLon(lat=27.9506, lon=-82.4572)
    departure = datetime(2026, 4, 19, 21, 0, tzinfo=timezone.utc)  # 5pm ET = 9pm UTC
    alts = await routing.alternates(origin, dest, departure)
    seg_geoms = segments_svc.slice_route(alts[0].polyline)
    cell_union: set[str] = set()
    for s in seg_geoms:
        cell_union |= s.cells
    return cell_union, departure


def main() -> int:
    import asyncio

    cell_union, departure = asyncio.run(_get_route_cells())
    print(f"Route covers {len(cell_union)} unique H3 cells (res 9)")

    client = get_client()
    name = get_settings().vdb_collection

    # ground truth: how many crashes total across the corpus fall in the
    # route's cells? Use the post-filter trick: search with zero vector +
    # huge limit, then filter client-side.
    print("\nGround-truth: pulling 20K random sample to see overlap with route cells...")
    sample = client.points.search(name, [0.0] * 384, limit=20000)
    sample_payloads = [getattr(r, "payload", None) or {} for r in sample]
    in_route = [p for p in sample_payloads if p.get("h3_cell") in cell_union]
    print(f"  {len(in_route)}/{len(sample_payloads)} sampled crashes ({len(in_route) * 100 // max(1, len(sample_payloads))}%) fall on the route")
    if in_route:
        from collections import Counter
        hours = Counter(p.get("hour_bucket") for p in in_route if isinstance(p.get("hour_bucket"), int))
        print("  hour distribution of route crashes:")
        for h in sorted(hours):
            print(f"    {h:02d}: {hours[h]}")

    # Now what does the semantic search actually return?
    print("\nSemantic retrieval (the production code path):")
    query = build_query_doc(
        departure=departure,
        weather_segments=[],
        sunset_iso=None,
    )
    text = render_narrative(query, for_query=True)
    print(f"  query text: {text!r}")
    vec = embed_one(text)

    # 1) server-side H3 filter (what the code prefers)
    try:
        from actian_vectorai import Condition, FieldCondition, Filter, Match
        flt = Filter(
            must=[Condition(field=FieldCondition(key="h3_cell", match=Match(keywords=list(cell_union)[:1024])))]
        )
        results_filtered = client.points.search(name, vec, limit=2000, filter=flt)
        print(f"  server-side h3 filter (top_k=2000): {len(results_filtered)} hits")
    except Exception as exc:
        print(f"  server-side h3 filter raised: {exc}")
        results_filtered = []

    # 2) client-side post-filter (what the code falls back to)
    results_unfiltered = client.points.search(name, vec, limit=10000)
    matched = [r for r in results_unfiltered if (getattr(r, "payload", None) or {}).get("h3_cell") in cell_union]
    print(f"  unfiltered top-10000 -> {len(matched)} on route after post-filter")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
