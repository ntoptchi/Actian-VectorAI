"""Diagnose the wide unfiltered search: how many results actually come back,
how many fall on a Miami-Tampa corridor, and what payload keys exist.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from datetime import datetime, timezone

from backend.embeddings import embed_one
from backend.ingest.situation_doc import render_narrative
from backend.services.scoring import build_query_doc
from backend.vdb import get_client
from backend.config import get_settings


def main() -> None:
    client = get_client()
    name = get_settings().vdb_collection

    print(f"collection={name}")
    print(f"  client.collections methods: {[m for m in dir(client.collections) if not m.startswith('_')]}")

    miami = (25.7617, -80.1918)
    tampa = (27.9506, -82.4572)
    departure = datetime(2026, 4, 19, 17, 0, 0, tzinfo=timezone.utc)

    from backend.schemas import WeatherSegment
    ws = WeatherSegment(from_km=0.0, to_km=400.0, weather="clear", surface="dry")
    qd = build_query_doc(departure=departure, weather_segments=[ws], sunset_iso=None)
    text = render_narrative(qd, for_query=True)
    print(f"query: {text!r}")

    vec = embed_one(text)

    for limit in [1000, 5000, 20_000, 50_000, 100_000]:
        try:
            res = client.points.search(name, vec, limit=limit)
            n = len(list(res))
            print(f"  search(limit={limit:>6}) -> {n} results")
        except Exception as e:
            print(f"  search(limit={limit}) -> ERROR: {e}")

    print(f"\nclient.points methods: {[m for m in dir(client.points) if not m.startswith('_')]}")

    # Try the filter directly with a small known set
    try:
        from actian_vectorai import Condition, FieldCondition, Filter, Match
        # Get one known h3_cell from the corpus
        sample = list(client.points.search(name, vec, limit=10))
        sample_cell = (getattr(sample[0], 'payload', None) or {}).get('h3_cell')
        print(f"\ntrying filter with single known cell {sample_cell}")
        flt = Filter(must=[Condition(field=FieldCondition(key='h3_cell', match=Match(keywords=[sample_cell])))])
        r = list(client.points.search(name, vec, limit=2000, filter=flt))
        print(f"  -> {len(r)} hits with filter on 1 cell")
    except Exception as e:
        print(f"  filter probe ERROR: {e}")

    # Check distribution of h3_cell values in a 5K sample
    res = list(client.points.search(name, vec, limit=5000))
    have_cell = sum(1 for r in res if (getattr(r, 'payload', None) or {}).get('h3_cell'))
    print(f"\nout of 5000 results, {have_cell} have h3_cell key set")
    if res:
        sample = res[0]
        print(f"sample payload keys: {list((getattr(sample, 'payload', None) or {}).keys())}")


if __name__ == "__main__":
    main()
