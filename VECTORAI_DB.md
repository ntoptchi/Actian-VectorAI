# RouteWise × Actian VectorAI DB

**For the judges.** This is a walk-through of exactly how RouteWise uses
Actian VectorAI DB, why it's load-bearing rather than a bolt-on, the
differentiators vs a stock RAG integration, and what we would ship next
if we had another week. Everything below is grounded in the code that's
actually in this repo — every claim has a file-and-line citation.

---

## 1. Where the vector DB sits in the product

RouteWise is a pre-trip briefing for a teen about to do an unfamiliar
long drive. Paste **Miami → Tampa, 6:30pm tonight**; get back:

- the route (re-ranked across ORS alternates by crash risk, not just
  duration);
- per-segment risk coloring on the map;
- 3–6 hotspot cards ("Near Fort Myers", "83K vehicles/day, 2.4× the FL
  interstate rate in rain at night");
- a **coaching line** and a **real crash lesson** on each hotspot,
  retrieved from a separate enriched-news collection;
- a "Lessons from the road" right-rail, deduped across hotspots.

Two of those five deliverables — **route re-ranking** and **every
coaching card** — are literally powered by VectorAI DB retrieval. Turn
the VDB off and every briefing card goes blank *and* the chosen route
collapses to "fastest". That's our honesty test on stage. See the
degradation contract in

```17:18:backend/services/scoring.py
Retrieval is wrapped in try/except: if the VDB is empty/down, every
score collapses to 0 and segments render as neutral. That's the
```

and

```15:17:backend/routers/trip.py
If the VDB is unreachable or the collection is empty, every score
collapses to 0 and the chosen route is just the fastest alternate.
```

---

## 2. The two collections (and why we run two)

We don't use "one index with everything." We run two collections with
very different shapes, because they serve two very different jobs.

### 2.1 `routewise_crashes` — the big geographic corpus

- ~140,000 FDOT crash records + 510 NEWS articles.
- **One dense vector per point**, 384-d cosine (MiniLM-L6-v2).
- Payload carries `h3_cell`, `hour_bucket`, `weather`, `surface`,
  `lighting`, `severity`, `crash_type`, `aadt`, plus the full
  `SituationDoc` (`backend/schemas.py`).
- Used by **route safety scoring** — `backend/services/scoring.py`.

Created in `backend/vdb.py`:

```71:82:backend/vdb.py
    if not client.collections.exists(name):
        client.collections.create(
            name,
            vectors_config=VectorParams(
                size=settings.vdb_vector_size,
                distance=Distance.Cosine,
            ),
        )
        logger.info("created VDB collection %s", name)
    else:
        logger.info("VDB collection %s already exists", name)
```

### 2.2 `routewise_coaching` — the small, high-signal lesson corpus

- 518 LLM-enriched crash lessons built from Florida news reporting.
- **Three dense named vectors** — `lesson`, `incident`, `factors_text`
  — *plus* a **sparse `factors` vector** over a frozen 40-term
  vocabulary. Example 29 (named vectors) and example 33 (sparse
  vectors) from the library, combined.
- Used by **hotspot lesson retrieval** and **route-wide insights** —
  `backend/services/coaching_retrieval.py`.

Created + probed in `backend/coaching_vdb.py`:

```71:94:backend/coaching_vdb.py
    dense_config = {
        v: VectorParams(size=settings.vdb_vector_size, distance=Distance.Cosine)
        for v in DENSE_VECTORS
    }

    # Attempt dense + sparse; verify via roundtrip; fall back if needed.
    try:
        client.collections.create(
            name,
            vectors_config=dense_config,
            sparse_vectors_config={VEC_SPARSE: SparseVectorParams()},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "sparse create raised; falling back to dense-only: %s", exc,
        )
        if client.collections.exists(name):
            client.collections.delete(name)
        client.collections.create(name, vectors_config=dense_config)
```

The point of splitting is that the two corpora have genuinely different
latency/recall/shape tradeoffs. Jamming them into one collection would
either force the big crash corpus to carry three vectors it doesn't
use, or force the coaching collection to lose its named/sparse
structure. We run them apart and rebuild them independently via
`scripts/ingest_fdot_crash.py`, `scripts/ingest_news.py`, and
`scripts/ingest_coaching.py`.

---

## 3. Write path — how data gets in

### 3.1 One schema, two uses

`SituationDoc` (`backend/schemas.py`) is a single Pydantic model used
at **both index time and query time**. Indexed docs fill in identity,
location, outcome, and narrative fields; query docs fill in only
environmental + temporal fields. A shared narrative renderer
(`backend/ingest/situation_doc.py:render_narrative`) writes both in
the same English template, so a query and a historical crash produce
comparable embeddings by construction. This is the contract that makes
similarity actually mean "this trip resembles this crash's situation."

### 3.2 Deterministic point IDs

All three ingest scripts use `uuid5(namespace, source + case_id)`
(`backend/ingest/upsert.py` + `scripts/ingest_coaching.py`). That buys
us idempotent retry — a resumed ingest upserts the same point IDs, so
duplicate writes are harmless.

### 3.3 Batched embed + upsert with timeout retry

```58:85:backend/ingest/upsert.py
def _upsert_with_retry(client, collection: str, points: list) -> None:
    """Wrap ``client.points.upsert`` with linear-backoff retry on timeout.

    The VDB server occasionally exceeds the (now 120 s) gRPC deadline
    under sustained write pressure as it flushes its index. A single
    blip shouldn't tank an hour-long ingest — re-upserting is safe
    because point IDs are deterministic ``uuid5(source, case_id)``, so
    retries are idempotent.
    """
    from actian_vectorai.exceptions import TimeoutError as VdbTimeoutError

    for attempt in range(1, _UPSERT_MAX_RETRIES + 1):
        try:
            client.points.upsert(collection, points)
            return
        except VdbTimeoutError as exc:
            if attempt == _UPSERT_MAX_RETRIES:
                logger.error(
                    "upsert timed out after %d attempts; giving up: %s",
                    _UPSERT_MAX_RETRIES, exc,
                )
                raise
            sleep_s = _UPSERT_RETRY_SLEEP_S * attempt
```

The 120 s client timeout is a deliberate bump from the library's 30 s
default, documented at the call site:

```40:46:backend/vdb.py
    ``timeout`` is bumped from the library's 30 s default to 120 s because
    bulk ingestion upserts 256-point batches and the local VDB
    occasionally pauses 30-60 s for internal index flushing once the
    collection passes ~10K points. A 30 s deadline caused mid-ingest
    DEADLINE_EXCEEDED on laptops running MiniLM on CPU alongside the
    Docker VDB. Query-side calls stay well under this ceiling, so the
    bump is a "max" not a normal latency.
```

### 3.4 Multi-vector + sparse upserts

The coaching ingest builds three dense vectors per point (one for each
facet) and one sparse vector over the frozen factor vocabulary:

```192:209:scripts/ingest_coaching.py
    for i, it in enumerate(items):
        vec: dict = {
            VEC_LESSON: lesson_vecs[i].tolist(),
            VEC_INCIDENT: incident_vecs[i].tolist(),
            VEC_FACTORS_TEXT: factor_vecs[i].tolist(),
        }
        if sparse_enabled:
            indices, values = encode_tags(it["payload"]["factor_tags"])
            if indices:
                vec[VEC_SPARSE] = SparseVector(indices=indices, values=values)
        points.append(
            PointStruct(
                id=_insight_id(it["payload"]["crash_id"]),
                vector=vec,
                payload=it["payload"],
            )
        )
```

### 3.5 Prebuilt snapshot so judges don't re-embed

Rebuilding the crash corpus from raw FDOT + AADT is a ~1 hour CPU job.
We ship a manifest pointing at a signed release artifact
(`vdb_snapshot.manifest.json`, `scripts/fetch_vdb_snapshot.py`) so
`install.sh` can drop a pre-built `vdb_snapshot.tar.gz` into the
container's data dir. Version-bumped when the ingest pipeline
meaningfully changes so stale snapshots never get re-seeded silently.

---

## 4. Read path — how retrieval drives the product

### 4.1 Route re-ranking (the `routewise_crashes` path)

`POST /trip/brief` (`backend/routers/trip.py`):

1. Pull N route alternates from ORS (fallback OSRM).
2. For each alternate: slice into ~40 segments, attach AADT, compute
   the **union of H3 cells** covering the entire corridor.
3. Build a single conditions query `SituationDoc` from tonight's
   weather + lighting + hour (`scoring.build_query_doc`) and embed
   once (so all alternates share the same query vector).
4. Retrieve crashes for each alternate filtered to its H3-cell union
   and a ±2-hour window around the trip's hour bucket
   (`scoring.retrieve_crashes_for_cells`). Bucket hits back onto
   segments via the cell-to-segment map.
5. **Per-segment intensity** = route-relative crash density (capped at
   5× so one tiny segment can't dominate the mean). **Per-route risk**
   = crashes per km across the whole route.
6. Chosen route = `argmin(duration_norm + λ · risk_norm)`, `λ = 0.4`.

```207:231:backend/routers/trip.py
def _pick_chosen(scored: list[_ScoredAlt]) -> int:
    """Cost = duration_norm + SAFETY_LAMBDA * risk_norm.

    Both terms are normalised to [0, 1] across the candidate set so the
    weight is comparable.
    """
    if len(scored) == 1:
        return 0
    durations = [s.alt.duration_s for s in scored]
    risks = [s.risk_score for s in scored]
    d_min, d_max = min(durations), max(durations)
    r_min, r_max = min(risks), max(risks)
    d_span = max(1e-6, d_max - d_min)
    r_span = max(1e-6, r_max - r_min)

    best_i = 0
    best_cost = float("inf")
    for i, s in enumerate(scored):
        d_norm = (s.alt.duration_s - d_min) / d_span
        r_norm = (s.risk_score - r_min) / r_span
        cost = d_norm + SAFETY_LAMBDA * r_norm
        if cost < best_cost:
            best_cost = cost
            best_i = i
    return best_i
```

### 4.2 In-memory filter (honest note on server-side indexes)

Our dev server doesn't implement `create_field_index` — it returns
UNIMPLEMENTED — so a `scroll(filter=h3_cell IN (...))` degrades to a
sequential scan and times out around 30 s. The honest engineering
answer is documented and bypassed, not ignored:

```1:17:backend/services/crash_cache.py
"""In-memory copy of the crash corpus, used for hot-path filtering.

The Actian VectorAI server in our dev environment does not implement
payload-field indexes (``create_field_index`` returns 501), so any
``points.scroll`` call with a payload filter (e.g. ``h3_cell IN (...)``
plus ``hour_bucket IN (...)``) does a full sequential scan inside the
engine and times out around the 30 s default RPC deadline. With ~5
filter chunks per request and several timeouts each, a single
``/trip/brief`` was taking 90–160 seconds.

The corpus is small enough to hold entirely in process memory
(140K rows × ~30 fields ≈ a few hundred MB). Loading it once at
startup turns the geographic filter into a list comprehension —
microseconds — and brings the total request well under the 8 s
budget.
```

We still `ensure_collection()` tries to create the indexes at
startup (`backend/vdb.py:86–91`) so when the server ships
`create_field_index`, we drop the cache and go straight to server-side
filtered search without code changes. The whole flow is designed to
graduate cleanly.

### 4.3 Three-channel hybrid retrieval (the `routewise_coaching` path)

This is where we get the most out of the library. For each hotspot we
run three parallel searches against the *same* collection, each using
a different named vector space, and fuse the rankings with RRF.

```174:199:backend/services/coaching_retrieval.py
    try:
        results_lesson = client.points.search(
            collection,
            vector=embed_one(lesson_query),
            using=VEC_LESSON,
            limit=PER_CHANNEL_LIMIT,
            with_payload=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("lesson search failed: %s", exc)
        results_lesson = []

    try:
        results_incident = client.points.search(
            collection,
            vector=embed_one(incident_query),
            using=VEC_INCIDENT,
            limit=PER_CHANNEL_LIMIT,
            with_payload=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("incident search failed: %s", exc)
        results_incident = []

    results_factors = _search_factors(
        client, collection, tag_list, tag_query_text, has_sparse
    )
```

- **`lesson` channel** — query: *"What should a driver do on a segment
  with following_too_close, rain under night with streetlights, rain,
  wet pavement?"* Matches against the LLM's `lesson_advice` field.
- **`incident` channel** — query: *"A crash on a segment with
  following_too_close, rain under night, wet pavement."* Matches
  against the LLM's `retelling` (incident summary) field.
- **`factors` sparse channel** — BM25-style keyword match over the
  frozen factor vocabulary (`backend/ingest/factor_vocab.py`).
  Degrades to a dense `factors_text` lookup if the server doesn't
  honour sparse.

Fusion uses the library's built-in reciprocal rank fusion with a local
fallback — the pattern shown in `examples/15_hybrid_fusion.py` of the
library:

```354:363:backend/services/coaching_retrieval.py
    try:
        from actian_vectorai import reciprocal_rank_fusion

        return reciprocal_rank_fusion(
            channel_results,
            limit=PER_CHANNEL_LIMIT,
            ranking_constant_k=RRF_K,
        )
    except Exception:  # noqa: BLE001
        return _local_rrf(channel_results)
```

RRF is specifically the right fusion here because the three channels
have different score scales (cosine vs sparse dot product); RRF
normalises by rank, not score, so we don't have to tune per-channel
weights that would drift the moment the corpus changed.

### 4.4 Coarse-to-rich vocabulary bridge

The segment scorer computes `top_factors` from crash payloads in a
coarse vocabulary (`rear_end`, `wet`, `dark_unlighted`,
`severity:fatal`, etc.). The LLM enrichment emits a richer vocabulary
(`following_too_close`, `impaired_alcohol`, `lane_departure`). A
frozen bridge keeps query and index on the same vocabulary without
either side having to drift:

```102:128:backend/ingest/factor_vocab.py
COARSE_TO_RICH: dict[str, tuple[str, ...]] = {
    # Surface / weather
    "wet": ("wet", "rain"),
    "rain": ("rain", "wet"),
    "fog": ("rain",),  # fog doesn't have its own tag; rain is the closest proxy
    "snow": ("wet",),
    "ice": ("wet",),
    # Lighting
    "dark_lighted": ("dark_lighted",),
    "dark_unlighted": ("dark_unlighted",),
    "daylight": ("daylight",),
    "dusk": ("dark_lighted",),
    "dawn": ("daylight",),
    # Crash types
    "rear_end": ("rear_end", "following_too_close"),
    "head_on": ("head_on", "wrong_way"),
    "angle": ("angle", "intersection"),
    "rollover": ("rollover",),
    "single_vehicle": ("single_vehicle", "ran_off_road"),
    "sideswipe_same": ("sideswipe", "improper_lane_change"),
    "sideswipe_opp": ("sideswipe", "improper_lane_change"),
    "pedestrian": ("pedestrian",),
    "bicycle": ("bicycle",),
    # Severity bumps (used when `severity:fatal` shows up in top_factors)
    "severity:fatal": ("speeding", "impaired_alcohol"),
    "severity:serious": ("speeding",),
}
```

This is a small thing, but it's the difference between "sparse
retrieval quietly returns nothing because the vocabularies mismatch"
and "sparse retrieval actually fires."

### 4.5 Pin placement — lesson retrieved, not lesson-transcribed

When the retrieved lesson reaches the map, we don't pin it at the
article's originally-reported latitude/longitude. We pin it at the
**midpoint of tonight's matching segment**, so the user sees the
lesson where they will actually encounter the pattern tonight. The
payload's original lat/lon is the fallback only:

```431:447:backend/services/coaching_retrieval.py
def _segment_midpoint(segment: "RouteSegment", payload: dict) -> LatLon:
    """Nearest-segment placement: pin sits where the lesson applies tonight.

    Falls back to the payload's original lat/lon only when the segment has
    no polyline (shouldn't happen in practice — segments always have at
    least two points — but we guard so ingestion quirks don't 500 the API).
    """
    poly = segment.polyline or []
    if poly:
        mid = poly[len(poly) // 2]
        if len(mid) >= 2:
            return LatLon(lat=mid[1], lon=mid[0])
    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is None or lon is None:
        return LatLon(lat=0.0, lon=0.0)
    return LatLon(lat=float(lat), lon=float(lon))
```

### 4.6 Dedupe across surfaces

A single trip shows the top-6 hotspot cards *and* a right-rail
"Lessons from the road" list. The two surfaces share the same VDB
backend, so we explicitly dedupe insight IDs across them so the same
lesson doesn't appear twice:

```323:350:backend/routers/trip.py
def _insights_for(
    scored: _ScoredAlt,
    hotspots: list[HotspotSummary],
    query_doc,
) -> list[CrashInsight]:
    """Route-wide insights, deduping against anecdotes already attached to hotspots.

    Hotspot anecdotes already consume the highest-similarity pulls, so
    we pass their IDs as the initial dedupe set to avoid pinning the
    exact same lesson twice (once on the hotspot card, once on the
    "Lessons from the road" list).
    """
    used = {h.insight.insight_id for h in hotspots if h.insight is not None}
    existing = [h.insight for h in hotspots if h.insight is not None]

    # Retrieve for segments not already represented via hotspots.
    fresh = coaching_retrieval.retrieve_for_route(scored.segments, query_doc)
    merged: list[CrashInsight] = list(existing)
    for ins in fresh:
        if ins.insight_id in used:
            continue
        merged.append(ins)
        used.add(ins.insight_id)
```

---

## 5. How we're differentiating

A staff engineer skimming this section will see four things that
aren't in a default "paste your docs into a vector DB" integration:

### 5.1 The vector DB is load-bearing, not a ragbolt-on

The test is literally documented in the brief: *"Turn off the vector
database, every briefing card goes blank. That's our honesty test."*
The code honours it — `coaching_retrieval` wraps every call in
try/except and returns `None` / `[]` on failure, the routers accept
that gracefully, and the UI renders neutral. But without the VDB
there's no re-ranking, no hotspot pins, and no lesson copy at all. It
is the product.

### 5.2 Two collections with deliberately different shapes

One is a big cosine-only dense corpus for geographic + conditions
filtering. The other is a small named-dense + sparse hybrid for
lesson matching across three semantic facets. They're rebuilt
independently, indexed independently, and queried with entirely
different code paths. We picked the collection shape for the query
pattern, not for convenience.

### 5.3 Multi-vector + sparse + RRF is actually wired up

Plenty of demos show one of these features. We run all three in one
query path:

- three named dense vectors (`lesson`, `incident`, `factors_text`)
  from `examples/29_named_vectors.py`;
- a sparse factor vector from `examples/33_sparse_vectors.py`;
- reciprocal rank fusion from `examples/15_hybrid_fusion.py`.

Each was picked because a single-channel search failed an actual
failure mode we hit while testing. (Dense-only missed specific
behavioural factors; sparse-only missed situations described in prose;
lesson-only missed the narrative structure of a retelling.) Three
channels, fused, recovers all of it.

### 5.4 Operational honesty

- **Server-level capability probing.** We don't trust the server's
  self-reported sparse support. `ensure_coaching_collection` does a
  real round-trip upsert of a probe point and only treats sparse as
  available when the point actually survives
  (`backend/coaching_vdb.py:114–146`). If the server lies, we recreate
  the collection dense-only.
- **Graceful degradation.** Every retrieval is wrapped in try/except
  and the surfaces all know how to render without the VDB. The only
  UI state that requires the VDB *and* isn't clearly marked is
  "chosen route" — by design, because that's our honesty test.
- **Idempotent retries.** `uuid5` point IDs plus linear-backoff retry
  on `DEADLINE_EXCEEDED` means bulk ingest survives the server's
  periodic 30–60 s index-flush pauses without hand-holding.
- **Pre-built snapshot + marker files.** Teammates and judges don't
  re-embed; they pull a signed release artifact. Version strings in
  the manifest match a marker file, so stale snapshots trigger a
  rebuild automatically.
- **Library-fallback redundancy.** The RRF path tries the library's
  helper first (`reciprocal_rank_fusion`), falls back to a local
  implementation on any ImportError. We never let a minor version
  skew break retrieval.

### 5.5 The schema is the contract

`SituationDoc` is the single Pydantic model used at index time and
query time. `render_narrative` writes the same English template for
both, with a `for_query=True` flag that strips outcome + road context
that the query doesn't carry. That's how cosine similarity actually
means what you want it to mean — the two vectors are coming from the
same sentence generator, not "my dense embedding of a query" vs "my
dense embedding of a row of SQL". This is the thing that most
vector-DB demos quietly get wrong.

---

## 6. Things we'd add next

These are real improvements, ordered by expected impact × lift.

### 6.1 Native async client + connection pool

We currently wrap the sync client in `asyncio.to_thread` inside the
FastAPI handlers (`backend/routers/trip.py`). `examples/02_async.py`
and `examples/20_connection_pool.py` show the native async path. At
concurrent-request scale this drops a thread hop per retrieval and
lets `/trip/brief` fan out its three channels in parallel instead of
sequentially. Expected: -100–200 ms per request under load.

### 6.2 Server-side payload filters (drop the in-memory cache)

The in-memory crash cache is a workaround for a server that doesn't
yet implement `create_field_index` (UNIMPLEMENTED). Once payload
indexes land, a `scroll(filter=h3_cell IN corridor AND hour_bucket IN
window)` goes directly at the server, we get rid of
`backend/services/crash_cache.py`, cold starts lose ~3–5 s of
crash-cache warmup, and memory drops ~300 MB. The startup hook
(`backend/vdb.py:86–91`) already tries to create those indexes —
we're ready for the day they stick.

### 6.3 Scalar / binary quantization on `routewise_crashes`

140K × 384-d float32 = ~200 MB on disk today (reflected in the
239 MB tar.gz snapshot). `examples/34_quantization.py` shows scalar
quantization at ~4× compression with <1% recall loss for cosine on
normalised MiniLM vectors. The snapshot drops to ~60 MB and the
cold-start fetch is noticeably faster. No code changes elsewhere.

### 6.4 Add a `conditions` named vector to `routewise_crashes`

Right now, the big crash corpus is single-vector. A second named
vector dedicated to *conditions-only* text (what
`render_narrative(for_query=True)` already emits at query time) would
let us do a two-stage search on that collection too:

1. dense match on `conditions` for corridor-wide "situations tonight"
   filtering;
2. dense match on `narrative` to re-rank the shortlist by the
   investigator's actual description.

This mirrors the coaching collection's named-vector strategy and is
where we'd go next once the big corpus gets an obvious "noisy
retrieval" failure mode.

### 6.5 Filter-by-payload on the coaching collection

The current coaching retrieval is unfiltered: we ask for the
semantically closest lessons without constraining by severity, county,
or time-of-day. `examples/06_filtered_search.py` +
`examples/11_advanced_filters.py` show how to add
`Filter(must=[FieldCondition(key="severity", match=...)]`. Obvious
wins:

- Filter teen-specific trips against `driver_demographic ∈ {"teen",
  "young"}` so the right lesson surfaces.
- Filter hotspots inside a given county + recent year so "recency" is
  a first-class retrieval axis rather than a post-filter on RRF.
- Filter out `preventability="low"` if the user marked themselves as
  already cautious.

### 6.6 MMR / diversity re-rank on the insight list

On a foggy, rainy-night route our RRF output correctly returns five
fog-related lessons. That's technically relevant and experientially
boring. A maximum-marginal-relevance pass over the fused results —
still cheap, runs client-side, takes `factor_tags` as the diversity
axis — keeps relevance high but diversifies the visible five down the
list.

### 6.7 Smart-batch streaming ingest for live news

`examples/30_smart_batcher.py` shows buffered upserts with automatic
flushing. Wiring a RSS pull of Florida crash news into the coaching
collection (same enrichment pipeline, same uuid5 namespace, same
sparse vocabulary) gives us a always-on refresh — lessons from last
week's crashes show up tonight. No rebuild needed; the sparse
vocabulary is frozen and unknown tags are silently dropped at query
time by design (`backend/ingest/factor_vocab.py:encode_tags`).

### 6.8 REST transport + TLS for demos

`examples/13_rest_transport.py` + `examples/19_tls_connection.py` —
useful once we host the VDB somewhere judges can `curl` it during the
demo. Not a performance change, but a "let's show our work" change.

### 6.9 Larger retrieval model behind the same 384-d interface

The whole system is keyed on 384-d cosine. Swapping MiniLM for BGE-
small-en-v1.5 (also 384-d) is a literal model-path change in
`backend/embeddings.py` and we'd rebuild the snapshot — no schema
changes, no collection-config changes. On evaluation we'd expect
measurable gains on the `lesson` channel in particular, which is where
the query is most abstract ("what should a driver do on a segment with
following_too_close, rain under night…").

### 6.10 Evaluation harness

The honest gap in the current system is that retrieval quality is
measured by eyeballing demo trips. We'd add:

- a small labelled set of (segment, expected_lesson_id) pairs;
- a recall@k / MRR harness per channel and for the fused result;
- a per-PR diff so tuning `RRF_K`, `PER_CHANNEL_LIMIT`, or the tag
  bridge is a numbers-driven change, not a vibes-driven one.

---

## 7. File map — where to look if you're reading along

| Concern | File |
|---|---|
| Settings, collection names, vector size | `backend/config.py` |
| Embedding model wrapper (MiniLM, 384-d) | `backend/embeddings.py` |
| Unified doc schema (index + query) | `backend/schemas.py` (`SituationDoc`) |
| Narrative template (shared between ingest + query) | `backend/ingest/situation_doc.py` |
| Sparse vocab + coarse-to-rich tag bridge | `backend/ingest/factor_vocab.py` |
| `routewise_crashes` collection wiring | `backend/vdb.py` |
| `routewise_coaching` collection wiring | `backend/coaching_vdb.py` |
| Batched ingest with retry | `backend/ingest/upsert.py` |
| Coaching-collection ingest (multi-vector + sparse) | `scripts/ingest_coaching.py` |
| Pre-built snapshot fetch | `scripts/fetch_vdb_snapshot.py`, `vdb_snapshot.manifest.json` |
| Safety scoring (retrieval → per-segment risk → route risk) | `backend/services/scoring.py` |
| In-memory corpus cache (workaround for missing server-side indexes) | `backend/services/crash_cache.py` |
| Three-channel hybrid retrieval + RRF | `backend/services/coaching_retrieval.py` |
| Orchestration + route re-ranking | `backend/routers/trip.py` |
| Rule-based coaching fallback (when VDB returns nothing) | `backend/services/coaching.py` |

---

## 8. TL;DR for the panel

RouteWise uses Actian VectorAI DB as the **reasoning layer** of a
safety product, not as a glorified embeddings key-value store. Two
collections, one dense + one named-multi-vector-plus-sparse, drive
both the route re-ranking and every piece of coaching copy the user
sees. The query schema is shared with the index schema by design, the
retrieval fuses three channels with RRF, and the whole pipeline
degrades gracefully when the VDB is unavailable — because we literally
don't want to fake the result. If you turn the DB off, the screen
tells you the truth.
