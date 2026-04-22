# News Integration Spec

## Decision: Same collection

News articles go into `routewise_crashes` with `source: "NEWS"` alongside FARS, CISS, and FDOT records.

Rationale:
- Retrieval path (`retrieve_crashes_for_cells`) already filters by H3 cell + hour_bucket ±2h across the entire corpus. News articles with the same h3_cell and timestamp surface automatically — zero plumbing changes.
- `render_narrative()` already templates narrative text into embeddings. A news headline + excerpt is just a richer narrative.
- `Source` literal is currently `"FARS" | "CISS" | "FDOT"`. Add `"NEWS"`. One line.
- Post-filter by source when building the UI response (show crash records vs. news separately) without needing separate queries.
- A separate collection means double the cache warming, a second query path, and merging results.

---

## Linking: H3 cell + date ±3 days

No explicit foreign-key linking needed. The retrieval pipeline already groups by co-location. For display purposes ("this article covers this crash"):

- **H3 cell match** (resolution 9) — same cell = same ~175m hex
- **Date ±3 days** — news coverage typically lags the crash by 1-2 days
- **Optional tiebreak**: if multiple crashes share the cell+window, pick the one with matching severity (fatal article → fatal crash)

Add `linked_crash_ids: list[str]` to the news article's payload. Populate at ingest time by querying the in-memory corpus. If no match, leave empty — the article still surfaces via H3 cell proximity at query time.

Don't use semantic similarity for linking. The embeddings are tuned for conditions matching (weather, lighting, time-of-day), not for matching "a news article about a crash" to "the crash record." H3+date is more reliable and cheaper.

---

## News severity: simple count, display-only

`news_mention_count` on the hotspot, not a scoring multiplier.

Why not extract severity from article text: NLP side-quest (keyword lists, tone scoring, false positives). Not worth the time.

Why not use it as a scoring multiplier: scoring pipeline (`score_segments`) is already debuggable — density / route mean → intensity_ratio → risk_band. Injecting a media-derived weight makes it opaque.

Instead: when building hotspots from segments, count how many `source=="NEWS"` payloads landed in that segment. Surface as **"Covered by N news reports"** in the briefing card. Makes the hotspot feel real and current without distorting the crash-rate math.

---

## Dashboard: news excerpts inside BriefingCard

Add a **"Media Coverage"** section to `BriefingCard.tsx`, below the existing "Investigator Field Notes" block. Each entry shows:

- **Headline** (bold, linked to source URL)
- **1-2 sentence excerpt** from the article body
- **Source + date** (e.g., "Miami Herald · March 14, 2011")

Co-location with crash data in the same card makes each hotspot more visceral. The LARP framing: "Here's what the news reported about crashes at this location."

---

## News JSON schema

Extend `SituationDoc` with 6 optional fields (defaults to None/empty so existing crash records are unaffected):

```python
# --- News-specific (source == "NEWS" only) ---
headline: str = ""
article_excerpt: str = ""        # 2-3 sentence pull quote
publisher: str = ""              # "Miami Herald", "WFTV", etc.
article_url: str = ""
publish_date: date | None = None
linked_crash_ids: list[str] = Field(default_factory=list)
```

### Embedding strategy

Update `render_narrative()` to handle `source == "NEWS"`:

```python
if doc.source == "NEWS":
    parts.append(f"News report: {doc.headline}")
    parts.append(doc.narrative)  # full article body or long excerpt
else:
    # existing crash narrative template
```

Conditions fields (weather, lighting, h3_cell, hour_bucket) should still be populated from the article's content or from the linked crash record — this is what makes the article retrievable by the same H3+time filter.

### Example ingest mapping

```python
SituationDoc(
    source="NEWS",
    case_id="news-miami-herald-2011-03-14-001",  # stable ID for uuid5
    lat=26.12, lon=-80.34,
    h3_cell=h3.latlng_to_cell(26.12, -80.34, 9),
    timestamp=datetime(2011, 3, 14, 18, 0),
    hour_bucket=18,
    day_of_week=0,
    month=3,
    weather="rain",
    lighting="dark_lighted",
    severity="fatal",
    headline="Two killed in I-75 pileup near Fort Myers",
    narrative="Full article text here...",
    article_excerpt="A chain-reaction crash during heavy rain...",
    publisher="Miami Herald",
    article_url="https://...",
    publish_date=date(2011, 3, 14),
    linked_crash_ids=["FDOT-2011-123456"],
)
```

---

## Implementation order (1-2 days)

| Step | Time | What |
|------|------|------|
| 1 | 30 min | Add `"NEWS"` to `Source` literal, add 6 optional fields to `SituationDoc` |
| 2 | 30 min | Update `render_narrative()` with NEWS branch |
| 3 | 1-2 hr | Write `normalize_news()` adapter (scraper JSON → SituationDoc), H3+date crash linking |
| 4 | 30 min | Run upsert on 2-3 test articles, verify they appear in the corpus |
| 5 | 1 hr | Update `hotspots_from_segments` to count `source=="NEWS"` and attach excerpts |
| 6 | 1-2 hr | Add "Media Coverage" section to `BriefingCard.tsx` |
| 7 | 30 min | Test end-to-end with a demo corridor |

~5-7 hours of actual work. Remainder is buffer for scraper issues and polish.
