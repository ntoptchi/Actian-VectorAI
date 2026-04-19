"""Diagnostic: dump hour-of-day distribution + a sample VDB query so we
can see why 5pm doesn't surface the expected crash density.

Run with: .venv\\Scripts\\python.exe scripts\\_diag_hour_distribution.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings  # noqa: E402
from backend.vdb import get_client  # noqa: E402


def main() -> int:
    client = get_client()
    name = get_settings().vdb_collection

    # Pull a generous sample by paging through the collection. We don't
    # need every row — 8K is enough to see the shape.
    sample_n = 0
    hours: Counter[int] = Counter()
    cells: Counter[str] = Counter()
    weather: Counter[str] = Counter()
    lighting: Counter[str] = Counter()
    states: Counter[str] = Counter()

    # Use scroll-style: search with a zero vector + huge limit. If that's
    # not supported, fall back to small batched search.
    try:
        page = client.points.search(name, [0.0] * 384, limit=8000)
    except Exception as exc:
        print(f"VDB sample failed: {exc}")
        return 1

    for r in page:
        payload = getattr(r, "payload", None) or {}
        h = payload.get("hour_bucket")
        if isinstance(h, int):
            hours[h] += 1
        cell = payload.get("h3_cell")
        if cell:
            cells[cell[:6]] += 1  # bucket by H3 prefix
        weather[payload.get("weather", "?") or "?"] += 1
        lighting[payload.get("lighting", "?") or "?"] += 1
        states[payload.get("state", "?") or "?"] += 1
        sample_n += 1

    print(f"sampled {sample_n} crashes from VDB '{name}'")
    print("\nHour-of-day histogram (raw counts):")
    for h in range(24):
        n = hours.get(h, 0)
        bar = "#" * min(60, n // max(1, sample_n // 600))
        print(f"  {h:02d}: {n:5d} {bar}")
    print(f"\nUnique H3 cell prefixes (geographic spread): {len(cells)}")
    print(f"Top 5 prefixes: {cells.most_common(5)}")
    print(f"\nWeather mix: {dict(weather)}")
    print(f"Lighting mix: {dict(lighting)}")
    print(f"State mix: {dict(states)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
