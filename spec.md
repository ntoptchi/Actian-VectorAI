# News Integration Spec

## Current status: WORKING END-TO-END

308 real news articles from `semantic_crashes.json` are ingested into VDB and surfacing on the frontend as blue map pins + sidebar cards + slide-out briefing panels. Verified on Orlando→Tampa corridor (7 articles returned).

---

## Architecture summary

```
Scraper JSON (semantic_crashes.json)
  → normalize.py::from_news_article()   # inherits conditions from paired FDOT crash
  → embed via render_narrative()         # "News report: {headline} {body[:2000]}"
  → upsert into routewise_crashes        # source="NEWS", same collection as FDOT/FARS
  → crash_cache loads at backend startup

Query time:
  → retrieve_crashes_for_cells()         # standard H3 + hour filter (catches nearby news)
  → _wider_news_search()                 # ring-3 (~500m) buffer, no hour filter (catches corridor news)
  → trip.py separates source=="NEWS"     # news excluded from risk scoring
  → news_articles[] in TripBriefResponse # sent to frontend as separate array
```

---

## What was built (files changed)

### Backend

| File | What changed |
|------|-------------|
| `backend/schemas.py` | Added `"NEWS"` to `Source` literal. Added 6 news fields to `SituationDoc` (headline, article_excerpt, publisher, article_url, publish_date, linked_crash_ids). Added `NewsArticleResponse` model. Added `news_articles` field to `TripBriefResponse`. |
| `backend/ingest/normalize.py` | Added `from_news_article()` adapter. Handles two scraper formats: GeoJSON Feature (mock) and flat properties + `crashGeometry` (real data from `semantic_crashes.json`). Inherits weather/lighting/surface/severity from paired FDOT crash. Truncates narrative to 2000 chars (VDB payload limit). Accepts `crashTier` as severity override. |
| `backend/ingest/situation_doc.py` | `render_narrative()` now has a NEWS branch: prepends `"News report: {headline}"` + article body, then returns early (skips crash-outcome template). |
| `backend/routers/trip.py` | `_score_alternate()` separates `source=="NEWS"` payloads from crash docs so news doesn't inflate risk scores. Added `_wider_news_search()` — expands route H3 cells by ring-3 (~500m buffer) with no hour filter to catch corridor news. Added `_news_articles_for()` to build `NewsArticleResponse` list. `_ScoredAlt` now carries `news_payloads`. Response includes `news_articles=news_articles`. |

### Frontend

| File | What changed |
|------|-------------|
| `routewise/src/lib/types.ts` | Added `NewsArticle` interface. Added `news_articles` to `TripBriefResponse`. |
| `routewise/src/lib/api.ts` | Added `news_articles: []` defensive default in `fetchTripBrief`. |
| `routewise/src/components/RouteMap.tsx` | Added `newsArticles` + `onNewsClick` props. Renders news as **blue CircleMarkers** (distinct from red hotspot pins) with headline + publisher tooltip. |
| `routewise/src/app/trip/TripView.tsx` | Extended `Selection` union with `kind: "news"`. Added `newsArticles` memo. Passes `newsArticles` + `onNewsClick` to RouteMap. Added **"Media Coverage"** section in right sidebar with `NewsRow` component (shows headline, publisher, date, severity badge). Added `NewsIcon` SVG. |
| `routewise/src/components/BriefingCard.tsx` | Added `kind: "news"` to `CardSubject`. Early-returns to `NewsBriefingCard` for news selection. `NewsBriefingCard` renders: blue-accented status bar, headline, publisher/date, article excerpt in quote card, reported location coordinates, linked crash IDs, "Read Original Article" link button. Added `NewsCardIcon` and `ExternalLinkIcon` SVGs. |

### Ingestion scripts & data

| File | What it does |
|------|-------------|
| `scripts/ingest_news.py` | CLI to ingest news JSON. Reads `*news*.json` and `semantic_crashes*.json` patterns. Supports `--file`, `--limit`, `--batch-size`. Same upsert pipeline as FDOT/FARS. |
| `data/raw/news_mock.json` | 2 mock articles (Miami-Dade + Fort Myers) with coordinates placed directly on the Miami→Tampa I-75 route for guaranteed visibility. |
| `data/raw/semantic_crashes.json` | 308 real scraped articles. Pulled by teammate. Flat FDOT properties + `crashGeometry` format. |

---

## How to ingest news

```bash
# All news files (mock + real):
.venv/bin/python scripts/ingest_news.py

# Specific file:
.venv/bin/python scripts/ingest_news.py --file data/raw/semantic_crashes.json --batch-size 16

# After ingesting, RESTART THE BACKEND so the crash cache reloads:
# Kill uvicorn, then re-run start.sh or:
.venv/bin/python -m uvicorn backend.main:app --reload --port 8080
```

---

## How to test

**Best demo route:** Orlando → Tampa (evening departure)
- Origin: `lat=28.54, lon=-81.38`
- Destination: `lat=27.95, lon=-82.45`
- Returns ~7 news articles along the I-4 corridor

**What to look for:**
- Blue pins on the map (news) vs red pins (crash hotspots)
- "Media Coverage" section in right sidebar with article rows
- Click a blue pin or news row → slide-out card with headline, excerpt, publisher, link

**Other corridors with coverage:** Miami→Tampa, any route through Hillsborough/Orange/Broward/Palm Beach counties.

---

## Design decisions

### Same collection, not separate
News articles live in `routewise_crashes` with `source: "NEWS"`. They flow through the same embed → upsert → cache → retrieve pipeline. At scoring time, they're filtered out so they don't inflate crash counts or risk bands. Display-only layer.

### Conditions inherited from paired crash
Weather, lighting, surface, severity, AADT, speed limit, timestamp — all pulled from the linked FDOT crash record's properties, not parsed from article text. This keeps the embedding accurate and avoids NLP extraction.

### Wider retrieval for news
Crash retrieval uses H3 ring-1 (~175m) + ±2h hour filter. News articles are on nearby roads (US 301, SR 50, etc.) not pinpoint on the route polyline, so they need a wider net: ring-3 (~500m) with no hour filter. This is done in `_wider_news_search()` in `trip.py`.

### Narrative truncation
Article bodies can be 200K+ chars. VDB payload limit causes 500 errors on large batches. Narrative is truncated to 2000 chars at ingest time. The `article_excerpt` (300 chars) is what the frontend displays.

### matchScore threshold
Scraper provides `matchScore` (55–100). Articles with `matchScore >= 70` get `linked_crash_ids` populated. Below 70, the article still ingests but without a crash link. All 308 articles ingest regardless of score.

---

## What's NOT done yet (possible next steps)

1. **News count on hotspot cards** — spec says show "Covered by N news reports" on hotspot briefing cards. Not wired yet — would need to cross-reference news article locations with hotspot segments.
2. **Deduplication** — some articles appear with slightly different coordinates (same article, different crash link). Could deduplicate by headline similarity.
3. **Custom map icon** — currently news pins are blue circles. Could use a newspaper/article SVG marker for visual distinction.
4. **News in hotspot detail** — when viewing a crash hotspot, show related news articles from the same area inline below the factors.
5. **Severity-based pin color** — fatal news = red-blue, serious = orange-blue, etc.
