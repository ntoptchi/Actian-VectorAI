# RouteWise

**A safer-route finder for new drivers on unfamiliar long-distance drives, powered by Actian VectorAI DB.**

> **Pivot (April 2026):** RouteWise is now a route-finder. We fetch
> several candidate routes from OpenRouteService, then re-rank them by
> safety using crash data semantically retrieved from the VectorAI DB.
> The chosen route is rendered on a Leaflet map with **per-segment
> color coding** by risk band, hover tooltips that explain why each
> segment is flagged, and pop-out hotspot briefings. The original
> hotspot/coaching/conditions/fatigue features are preserved and now
> hang off the chosen route.
>
> The VDB is still load-bearing — every alternate gets a VDB search
> filtered by its H3 cells; per-segment risk and per-route aggregate
> risk both come from those retrievals; turn the VDB off and every
> route renders neutral and the chosen route collapses to "fastest".
> Concretely:
>
> 1. ORS returns 3 alternates.
> 2. Build one conditions-only ``SituationDoc``, embed once.
> 3. For each alternate: slice into ~40 segments, attach AADT,
>    similarity-search the VDB filtered by the alternate's H3 cells,
>    bucket retrieved crashes back onto segments, score per-segment
>    risk against the FL baseline, aggregate to a per-route risk score.
> 4. Pick the chosen route by ``argmin(duration_norm + 0.4 * risk_norm)``.
> 5. Surface chosen route + alternates + segments + hotspots in a
>    single ``/trip/brief`` response.
>
> See ``backend/routers/trip.py`` for the orchestration and
> ``backend/services/scoring.py`` for the VDB-driven scoring.

> You're a teen with your first solo long drive ahead — Miami to Tampa
> tonight, or Jacksonville to Pensacola tomorrow. You've never driven it.
> RouteWise takes your route and the conditions you'll be driving in,
> pulls the real crashes that happened on roads like yours in weather
> like yours, clusters them into the 3-6 places on your trip that
> *actually* deserve attention, and briefs you on each — in the voice of
> a driving instructor, grounded in real investigator narratives rather
> than model predictions.

This document is both the pitch and the engineering spec.

---

## 1. Problem

New drivers (16-22) have the fewest miles, the least situational
intuition, and the highest crash rate per mile of any age group in the
U.S. They know how to operate a car; they do not yet know **how roads
fail in context** — that the same on-ramp is safe in daylight and
lethal during light rain after dark, that following distances that work
at 45 mph collapse at 70, that curves drain water outward and leave
standing puddles on the inside line, that I-75 through Alligator Alley
has almost no services for 80 miles and a lane-departure crash there
has no witnesses.

### 1.1 The moment we target

A specific scene: a 17-year-old has a 4-hour drive ahead to a cousin's
house, a college visit, or a spring-break beach trip. They have driven
to school and to the mall. They have **never** driven this route. They
leave in the afternoon; they'll arrive after dark. They have 20
minutes before they get in the car.

That 20 minutes is when RouteWise is used. The teen pastes the route
in, reads the briefing, closes the tab, and starts the drive better
informed than they would have been otherwise. No in-car anything. No
account. No friction.

### 1.2 Why this knowledge gap exists

The knowledge to drive an unfamiliar 4-hour route well used to come
from two sources:

- **A parent in the passenger seat**, briefing the kid on the specific
  road: *"Watch the merge here, it's short and the truck drivers don't
  check."*
- **Accumulated experience** over hundreds of hours driving the same
  commute.

Both sources fail exactly when the trip is unfamiliar and long. The
parent hasn't driven I-10 through the Panhandle either. Experience
doesn't transfer between Miami traffic and Everglades interstate.
Navigation apps — Google Maps, Waze — optimize for travel time and
surface live hazards (accidents, cameras). They never surface the
**latent character** of the road: the way I-4 between Orlando and
Tampa earned the nickname "Florida's deadliest interstate" not from any
single crash but from a decades-long pattern of rear-ends at specific
mile markers in afternoon thunderstorms.

Public crash data encodes that latent character. It's fragmented:

- **FARS** (NHTSA fatalities) is nationally consistent but fatal-only
  and has no free-text narrative.
- **CISS** (NHTSA crash investigation sample) has rich investigator
  narratives but is small (~4-5K cases/year nationally).
- **FDOT Open Data crash layers** have broad non-fatal Florida
  coverage, structured only — no narratives.
- **AADT volumes** (FDOT, per-segment traffic counts) give us the
  denominator — how many cars actually pass each point. Most crash
  maps are missing this, which is why they mislead.

No single source combines rich narrative, broad coverage, **and
exposure data**. Joining them in a relational model is painful.
Embedding them into a single vector index makes them queryable
together; attaching AADT gives every retrieved crash a proper
denominator. That combination is where the database earns its keep.

### 1.3 Who this is for

Primary user: a teen driver (16-22) self-briefing in the ~20 minutes
before an unfamiliar long drive. Secondary user: a parent or older
sibling who wants to skim the same briefing and spend 2 minutes
talking through it with them.

### 1.4 What it is not

RouteWise is **not a nav app**. We don't compete with Google Maps or
Waze. No turn-by-turn, no voice, no in-car anything. The product is
consumed in the ~20 minutes before the drive, on a laptop or a
phone browser, then closed.

What we *do* that nav apps don't: when there are multiple reasonable
routes to the same destination, we tell you **which route has the
fewest crash-matched segments for tonight's conditions**, and brief
you on every hotspot along the way. *We don't just tell you when to
leave — we tell you which route carries the lowest risk match for
tonight, and show you why we picked it.*

---

## 2. Solution

**A pre-trip briefing page.** The user enters origin, destination, and
the time they're leaving. We produce a single scrollable page with:

1. **Trip header** — the route drawn on a map (one route, one color),
   distance, duration, departure and arrival times. Context, not
   product.
2. **Tonight's-conditions banner** — a single strip summarizing what
   the driver is actually heading into: *"4h 15min · Thunderstorms
   along I-75 between 19:30-21:00 · Sunset at 19:42 near Naples · You
   will drive the last 2 hours in the dark."*
3. **3-6 hotspot pins** along the route. Each represents a cluster of
   real historical crashes that resemble tonight's conditions, ranked
   by **crash rate per vehicle-pass** (not raw count — see §3.4).
4. A **briefing card per hotspot**, opened by clicking a pin:
   - Location and road feature ("I-75 SB approaching Exit 136, Fort
     Myers", "I-4 EB at the Lakeland curve before Exit 33").
   - A **coaching line** — the "what this means for you" sentence an
     instructor would give.
   - Aggregate pattern: *"In the last 5 years, 4 crashes at this
     location matched conditions like yours. 3 were rear-ends. All
     involved wet pavement. The segment sees ~82,000 vehicles a day —
     the crash rate here in rain at night is about 2.6× the Florida
     interstate average."*
   - **2-3 real narrative excerpts** from CISS investigator reports,
     redacted to protect PII but otherwise verbatim.
   - Severity distribution bar (fatal / serious / minor).
5. **Fatigue & rest-stop plan** — rule-based, long-drive-aware:
   *"Plan to stop at ~2h and ~3h 30min in. Fort Myers service plaza
   (mile 131) and Bee Ridge rest area (mile 201) are your two best
   options on this route."*
6. **Pre-departure checklist** — 5 items, generic: tires & fuel,
   phone mount and offline maps cached, water, headlights on before
   sunset, nobody rides shotgun texting. Anchor the briefing in
   something actionable.

That's the product. The entire UI is subordinate to the briefing
cards — the map is a backdrop, the conditions banner is a framing
strip, the checklist is table stakes. If the vector database is
disconnected, every briefing card goes blank and §2.4 below is what's
left on screen. That's the honesty test.

### 2.1 Example briefing card (Miami → Tampa, Friday 18:30, thunderstorms near Naples)

> **Hotspot 3 — I-75 NB approaching Exit 136, Fort Myers**
> *Elevated risk tonight (wet pavement, dusk, heavy merge volume)*
>
> In the last 5 years, **5 crashes at this location matched conditions
> like tonight's.** 4 of the 5 were rear-ends on the merge approach.
> All involved wet pavement. 3 happened between 17:00-20:00.
>
> This segment sees **~83,000 vehicles per day**. The crash rate here
> in rain during the evening rush is **~2.4× the Florida interstate
> average** — not because the road is unusual, but because the merge
> geometry is short and the right lane collects standing water before
> the exit.
>
> > *"Vehicle 1 northbound on I-75 decelerating in the right lane
> > approaching the Colonial Boulevard exit under light rain. Vehicle
> > 2 following at estimated 70 mph, failed to maintain following
> > distance when Vehicle 1 braked for traffic queued at the exit
> > ramp. Unit 2 attempted evasive maneuver left, struck Unit 1's
> > right rear..."* — CISS 2022FL00218
>
> **What this means for you:** the right lane bunches up approaching
> this exit, and drivers behind don't always see the queue until late.
> If you're staying on I-75, move to the middle lane by Exit 138 and
> stay there through the exit. If you're exiting, brake earlier than
> you think you need to and double your following distance from the
> previous exit onward.

The coaching line is the thing a regression model cannot produce. It's
derived from the retrieved evidence, not from the inputs.

### 2.2 Pre-trip, not in-trip

The product is consumed **before** the drive, not during it. No
in-car integration, no live nav. The user reads the page in ~2
minutes, closes the tab, and starts the car better informed.

This is a meaningful scope choice. It eliminates every hard problem
of real-time nav (turn-by-turn, voice, latency, distraction) and
focuses the build on what makes the product unique: the retrieval and
the briefing.

### 2.3 Why the briefing is long-trip-shaped, not commute-shaped

RouteWise is specifically tuned for **unfamiliar long drives**. That
shapes the design:

- The fatigue plan and sunset-during-drive banner are load-bearing.
  For a commute they'd be noise; for a 4-hour drive they are where
  half the actual risk lives.
- 3-6 hotspots is the right number for a 4-hour route. Fewer, and the
  user feels the product didn't find anything. More, and it becomes a
  scary laundry list they ignore.
- The map shows the whole route, not a 10-mile zoom. The user needs
  to see *where* on the trip the hard parts cluster — often front- or
  back-loaded, which changes how they pace themselves.
- Rural stretches with few crashes still get coverage via the
  conditions banner ("no services for 80 miles past Alligator Alley")
  and fatigue plan, so we don't pretend they're safe just because the
  dataset is thin there.

### 2.4 What shows when the VDB is off

Deliberately load-bearing to make the demo test legible: if we
disconnect VectorAI DB, what remains is the route polyline, the
tonight's-conditions banner, the fatigue plan, and the pre-departure
checklist. **Zero briefing cards. Zero hotspots.** That's the pitch's
honesty test — the VDB isn't a supporting component, it's where the
product's unique value lives.

---

## 3. Why Vector DBs are essential

The sharpest question about this pivot: *"Why not just a regression
model scoring (segment, conditions) → risk? Or a SQL query over
accident counts weighted by weather and AADT? Vector DB is
over-engineered."*

Fair question. The answer has four parts.

### 3.1 The product is retrieval, not scoring

A regression model outputs a number. The number alone is useless to a
new driver; "0.72 risk" doesn't tell a 17-year-old what to **do**.
RouteWise's deliverable is the briefing card, and the briefing card
is composed almost entirely of fields that exist only because
retrieval happened:

- Narrative excerpts → only accessible via semantic search over CISS
  text.
- Aggregate factor patterns → computed over the *retrieved* set, not
  the total corpus.
- Coaching line → derived from the top-N factor pattern of the
  retrieved set.
- Severity distribution → a histogram of the retrieved crashes'
  severities.
- Exposure-normalized rate ("2.4× Florida average") → computed over
  the retrieved cluster, normalized by the segment AADT from §3.4.

**If you swap the VDB for a regression model, every one of those
fields is empty.** The product doesn't exist. That's the litmus
test, and RouteWise passes it decisively.

### 3.2 Categorical filters miss situational joint patterns

A SQL `WHERE` clause on (road_type, weather, hour_bucket) returns
crashes matching those three fields independently. It cannot surface:

- "Wet curve approaches where following distance collapsed after the
  lead driver slowed for standing water" — because "situation where
  X because Y" is not a column.
- "Post-sunset multi-vehicle pile-ups at interchange merges in
  afternoon thunderstorms on I-4" — because the joint pattern is
  the signal, not the fields.

A 384-dimensional embedding of a `SituationDoc` (structured features
templated into sentences + narrative where available) captures those
joint patterns, and nearest-neighbor search retrieves them. The
specific narrative phrases — *"following distance collapsed,"
"hydroplaned on the expansion joint," "lost traction exiting the
cloverleaf"* — carry predictive weight that will never be columns.
Embedding them is the only practical way to use them.

### 3.3 The corpus is heterogeneous text

FARS has 170+ coded fields. CISS has paragraph narratives. FDOT's open
crash data has its own schema. Reconciling them into a relational
model is a 2-3 day cleanup job. Rendering every record into a single
`SituationDoc` template + free-text narrative (where present) and
embedding it sidesteps schema reconciliation entirely. Each record
contributes a document; retrieval blends them by similarity, not by
join key.

### 3.4 AADT as exposure denominator — why it matters for retrieval

Raw crash counts mislead. A stretch of I-95 through Miami that sees
200,000 vehicles a day will "appear" more dangerous than a
hair-raising rural curve on US-27 that sees 8,000 — simply because
more cars produces more crashes. Any product that surfaces "dangerous
places" using raw counts will point drivers at the wrong hazards and
deserve to be ignored.

**FDOT publishes Annual Average Daily Traffic (AADT) per road
segment.** At ingestion we snap every crash to its AADT segment and
store the volume on the payload. At query time we compute hotspot
intensity as an **exposure-normalized rate**:

```
intensity = (crashes_in_cluster_matching_conditions)
          / (segment_AADT × years_in_window × 365)
```

Hotspots are ranked by intensity, not by raw count. "5 crashes at
82,000 AADT" is a genuinely elevated rate; "5 crashes at 195,000
AADT" may be boringly average. The briefing card can state this
honestly: *"2.4× the Florida interstate average for this type of
segment in these conditions."*

This is the move that turns RouteWise from "map of scary dots" into
something a thoughtful user can trust. And **it's the VDB that makes
it possible** — we need semantic retrieval to find the cluster
conditionally (rain, evening, merge), then AADT to rate it. Neither
piece alone tells the story.

---

## 4. Data sources

| Source | Role | Records (FL subset) | Narrative? | License | URL |
|---|---|---|---|---|---|
| **FARS** 2018-2022 | Fatal-crash structured backbone (FL) | ~15-18K | No | Public | https://www.nhtsa.gov/file-downloads?p=nhtsa%2Fdownloads%2FFARS%2F |
| **CISS** 2017-present (national, Southeast subset) | Rich narrative enrichment | ~300-800 | **Yes** (investigator narratives) | Public | https://www.nhtsa.gov/file-downloads?p=nhtsa%2Fdownloads%2FCISS%2F |
| **FDOT Open Data Hub — crash layers** | Non-fatal FL coverage, geocoded | ~1-1.5M (5-year window) | Coded only | Public | https://gis-fdot.opendata.arcgis.com/ |
| **FGDL AADT shapefile** (FDOT) | **Exposure denominator** — per-segment vehicle volume | ~20K polylines statewide | N/A | Public | https://fgdl.org/ (`aadt_*`) |
| **OSRM** (public or self-hosted container) | Routing between origin and destination | On-demand | N/A | BSD-2 | https://project-osrm.org/ |
| **Open-Meteo** | Historical + current weather lookup along route | On-demand | N/A | Free tier, no key | https://open-meteo.com/en/docs |
| **pysolar** (local library) | Sunset / dawn computation along the route | N/A | N/A | GPL-3 | https://pysolar.org |

**Restricted access that we are deliberately NOT using:**

- Signal Four Analytics (S4A) — gated to FL government agencies /
  consultants.
- FDOT CAR system — gated via Automated Access Request Form.

We stay in the public lane. Everything above is downloadable with no
credentials.

**CISS is national, not Florida-specific** — and that's fine. The VDB
retrieves by situational similarity (wet evening merge on a rural
interstate), not by state. A Georgia or Texas rural-interstate rainy
rear-end is still a valid exemplar for a Florida rural-interstate
rainy rear-end. The H3-cell geographic filter is applied to the
structured (FARS + FDOT) corpus; CISS narratives surface by
similarity regardless of state, which is exactly the retrieval value
a SQL join would destroy.

### 4.1 Why Florida

- Dense crash data; I-95, I-75, I-4, and I-10 are the spine of
  Florida driving and each is a distinct character.
- FDOT publishes clean open data — crash layers, AADT shapefiles,
  roadway characteristics — with no access request required.
- Supports **three strong long-drive demo corridors** that map
  naturally to the teen-first-long-drive use case:
  - **Miami → Tampa** via I-75 / Alligator Alley (~280 mi, ~4h).
    Urban → Everglades rural interstate → Gulf-coast metro.
    Afternoon thunderstorm corridor.
  - **Jacksonville → Pensacola** via I-10 (~360 mi, ~5h 30m).
    Long rural interstate, high fatigue signature, limited
    services, wildlife strikes.
  - **Orlando ↔ Tampa** via I-4 (~85 mi, ~1h 30m). The "deadliest
    interstate" reputation makes this a sharp *verification* demo —
    show that retrieval surfaces what locals already know.
- Single-state pipeline dodges cross-jurisdiction schema
  reconciliation for non-fatal data.

---

## 5. Technical data flow

```
                         one-time ingestion                              query-time (per trip brief)
  ┌──────────────────┐      ┌────────────────┐      ┌─────────────┐      ┌──────────────────┐
  │ FARS / CISS /    │──►   │ normalize to   │──►   │ embed with  │──►   │ VectorAI DB      │
  │ FDOT crashes     │      │ SituationDoc,  │      │ MiniLM L6   │      │ routewise_crash  │
  │ (CSV / Shp / FTP)│      │ attach H3 cell │      │ (384-dim)   │      │ + payload index  │
  └──────────────────┘      │ + AADT volume  │      └─────────────┘      └────────┬─────────┘
                            └────────────────┘                                    │
                                                                                  │
       user submits: (origin, destination, time)                                  │
                           │                                                      │
                           ▼                                                      │
                  ┌─────────────────┐                                             │
                  │ /trip/brief     │                                             │
                  └────────┬────────┘                                             │
                           │                                                      │
              ┌────────────┼────────────┬──────────────┬──────────────┐           │
              ▼            ▼            ▼              ▼              ▼           │
       OSRM route     Open-Meteo   pysolar sun    H3 cells along   compute        │
       polyline       conditions   position       route (res 9)    fatigue &      │
       + duration     (per hour    (sunset time   with 1-ring      rest-stop      │
                      along route)  along route)   buffer           plan          │
              │            │            │              │              │           │
              └────────────┴────┬───────┴──────────────┴──────────────┘           │
                                ▼                                                 │
                       build query SituationDoc                                   │
                       (conditions only, no road_type)                            │
                                │                                                 │
                                ▼                                                 │
                      embed query → VDB similarity search ────────────────────────┘
                      + payload filter: h3_cell IN route_cells
                      top-k = 40-60 crashes
                                │
                                ▼
                      cluster retrieved crashes by geography
                      (DBSCAN on lat/lon, eps ≈ 300m)
                                │
                                ▼
                      for each cluster:
                        - keep if n≥2 AND mean_similarity ≥ τ
                        - attach segment AADT (from cluster centroid)
                        - compute exposure-normalized intensity
                                │
                                ▼
                      rank by intensity, keep top 3-6 → hotspots
                                │
                                ▼
                      for each hotspot:
                        - snap to nearest named road feature
                        - compute aggregate factors
                        - compose coaching line (rule-based)
                        - select 2-3 narrative excerpts
                                │
                                ▼
                      assemble response:
                        { route, duration, conditions_banner,
                          sunset_during_trip, fatigue_plan,
                          hotspots[], pre_trip_checklist }
```

### 5.1 Ingestion pipeline (once per dataset refresh)

1. **Download** raw FARS, CISS, FDOT crash exports, and FDOT AADT
   shapefile for the target years.
2. **Normalize** each crash record into a common `SituationDoc` (§6.1).
3. **Attach H3 cell** to every crash from its lat/lon at resolution 9
   (~150 m hex). This is the spatial join key used at query time.
4. **Attach AADT volume** by snapping each crash lat/lon to the
   nearest AADT segment polyline (KDTree over segment midpoints, then
   point-to-line distance check with a 50m threshold; unmatched
   crashes get `aadt=None` and are still indexed).
5. **Render narrative**: concatenate a deterministic template built
   from structured fields with the free-text investigator narrative
   where present (CISS only). Records without narratives still get a
   coherent situation paragraph from the template alone.
6. **Embed** with `sentence-transformers/all-MiniLM-L6-v2` (same model
   as RigSense — bundled locally in `models/`, runs offline).
7. **Upsert** into VectorAI DB collection `routewise_crashes` with
   the full payload (§6.2). Use `uuid5(namespace, source + case_id)`
   for deterministic point IDs.

### 5.2 Query pipeline (per trip brief)

1. Client `POST /trip/brief` with `{origin, destination, timestamp?}`.
2. Backend orchestrates four lookups in parallel:
   - **OSRM** → route polyline as GeoJSON LineString + distance +
     duration.
   - **Open-Meteo** → weather at 3-4 sample points along the route,
     interpolated to departure time + driving progress. Cached by
     `(rounded_lat, rounded_lon, hour_bucket)`.
   - **pysolar** → sunset time at the route midpoint; derive the
     fraction of the trip after sunset.
   - Compute **fatigue plan**: rest-stop suggestions at ~2h and
     ~3.5h into the trip, snapped to nearest highway service
     plaza/rest area (hard-coded lookup for FL interstates is fine;
     corpus is small).
3. Compute the set of **H3 cells** the polyline crosses at resolution
   9. Buffer by one H3 ring (neighbors) so crashes just off the
   polyline still surface. Typical cell count for a 280-mile route:
   ~1,800-2,400 cells.
4. Build a query `SituationDoc` from conditions only (weather,
   precipitation, visibility, lighting, surface, hour_bucket,
   day_of_week). No road_type — we let the retrieved crashes' own
   road types emerge from the results.
5. Embed the query doc with the same MiniLM model.
6. **VDB similarity search** with payload filter
   `h3_cell IN {route_cells}`, top-k = 40-60. If VectorAI DB's filter
   support on 2K-element IN-lists is weak, fall back to retrieving
   top-300 globally and post-filtering in memory. Still sub-second.
7. **Cluster** the retrieved crashes by geography (DBSCAN,
   `eps ≈ 300m`, `min_samples=2`). Discard singletons; keep clusters
   whose mean similarity ≥ τ (tuned, ~0.55 with MiniLM).
8. For each surviving cluster:
   - Pick the **cluster centroid** (median lat/lon).
   - Look up **segment AADT** at the centroid.
   - Compute **intensity** = `cluster_size / (AADT × years × 365)`,
     convert to "crashes per million vehicle-passes in matching
     conditions".
   - Compute the ratio against the Florida same-road-class baseline
     (precomputed per road class during ingestion).
9. **Rank clusters by intensity**, keep top 3-6 → hotspots.
10. For each hotspot:
    - Snap to the nearest OSM named feature for the label
      ("I-75 NB Exit 136", "I-4 EB at Lakeland").
    - Compute **aggregate factors**: fraction-of-cluster for each
      tagged factor (wet surface, nighttime, rear-end, multi-vehicle,
      curve, merge, construction).
    - Compose the **coaching line** via rule lookup keyed on the
      top-2 factor tuple (e.g., `(wet, rear_end) → "double following
      distance through the curve"`, `(dark_rural, single_vehicle) →
      "scan the shoulders for wildlife, headlights don't reach far
      enough at highway speed"`). ~15 rules total covers the long
      tail; catch-all falls through to a generic "stay alert through
      this segment" line.
    - Pick the **2-3 best narrative excerpts** (highest similarity +
      has CISS narrative text, prefer diversity of severity).
11. Return `{ route, duration, conditions_banner, sunset_during_trip,
    fatigue_plan, hotspots[], pre_trip_checklist }`.
12. **`GET /hotspots/{id}`** returns the full briefing card payload
    when the user clicks a pin.

---

## 6. Schemas

### 6.1 `SituationDoc`

Used for both indexed crashes and query construction. Making indexing
and querying share the template is what makes retrieval sensible.

```python
class SituationDoc:
    # Identity (indexed docs only; None on queries)
    source: Literal["FARS", "CISS", "FDOT"]
    case_id: str
    state: str
    county: str | None

    # Location (indexed docs only)
    lat: float
    lon: float
    h3_cell: str               # resolution 9
    road_type: Literal[
        "interstate", "us_highway", "state_route",
        "arterial", "ramp", "local", "unknown"
    ]
    road_function: str | None
    speed_limit_mph: int | None

    # Exposure (indexed docs only) — denominator for intensity
    aadt: int | None               # annual avg daily traffic at this segment
    aadt_segment_id: str | None

    # Time (both; derived for queries)
    timestamp: datetime | None
    hour_bucket: int           # 0-23
    day_of_week: int           # 0-6
    month: int                 # 1-12

    # Environmental state (both — this is what a query carries)
    weather: Literal[
        "clear", "rain", "snow", "fog", "sleet",
        "severe_wind", "unknown"
    ]
    precipitation_mm_hr: float | None
    visibility_m: float | None
    lighting: Literal[
        "daylight", "dawn_dusk", "dark_lighted", "dark_unlighted"
    ]
    surface: Literal["dry", "wet", "icy", "snowy", "unknown"]

    # Outcome (indexed docs only)
    crash_type: Literal[
        "rear_end", "head_on", "angle", "sideswipe_same",
        "sideswipe_opp", "rollover", "single_vehicle",
        "pedestrian", "bicycle", "other", "unknown"
    ] | None
    num_vehicles: int | None
    num_injuries: int | None
    num_fatalities: int | None
    severity: Literal["fatal", "serious", "minor", "pdo", "unknown"]

    # Narrative (indexed docs only)
    has_narrative: bool        # True iff CISS provided text
    narrative: str             # template rendering + CISS text (if present)
```

### 6.2 VectorAI DB collection layout

```
Collection: routewise_crashes
  point_id:   UUID (uuid5 of source + case_id)
  vector:     float32[384]                 # MiniLM L6 v2
  payload:    <SituationDoc as JSON>
```

Payload indexes we want (exact filters needed at query time):

- `h3_cell` (exact — **primary spatial filter**, required)
- `state` (exact — for multi-state futures)
- `source` (exact — UI badges CISS narratives differently)
- `severity` (exact — for aggregate factor computation)

### 6.3 API request / response

**`POST /trip/brief`**

```jsonc
// request
{
  "origin":      { "lat": 25.7617, "lon": -80.1918 },    // Miami
  "destination": { "lat": 27.9506, "lon": -82.4572 },    // Tampa
  "timestamp":   "2026-04-20T18:30:00-04:00"             // optional, defaults to now
}
```

```jsonc
// response
{
  "trip_id":          "t_01HX...",
  "route": {
    "polyline_geojson": { "type": "LineString", "coordinates": [[lon,lat], ...] },
    "distance_m":       454000,
    "duration_s":       15300,
    "departure_iso":    "2026-04-20T18:30:00-04:00",
    "arrival_iso":      "2026-04-20T22:45:00-04:00"
  },
  "conditions_banner": {
    "summary":            "Thunderstorms along I-75 between 19:30-21:00. Sunset at 19:42 near Naples. You will drive the last 2 hours in the dark.",
    "weather_segments": [
      { "from_km": 0,   "to_km": 120, "weather": "clear",         "surface": "dry" },
      { "from_km": 120, "to_km": 240, "weather": "rain",          "surface": "wet" },
      { "from_km": 240, "to_km": 454, "weather": "scattered_rain","surface": "wet" }
    ],
    "sunset_iso":         "2026-04-20T19:42:00-04:00",
    "dark_drive_minutes": 183
  },
  "fatigue_plan": {
    "total_drive_minutes": 255,
    "suggested_stops": [
      { "label": "Naples-Collier Service Plaza", "km_into_trip": 180, "eta_iso": "2026-04-20T20:18:00-04:00" },
      { "label": "Port Charlotte rest area",     "km_into_trip": 310, "eta_iso": "2026-04-20T21:42:00-04:00" }
    ]
  },
  "hotspots": [
    {
      "hotspot_id":     "h_01HX...",
      "label":          "I-75 NB approaching Exit 136, Fort Myers",
      "road_name":      "I-75",
      "centroid":       { "lat": 26.6102, "lon": -81.8234 },
      "km_into_trip":   275,
      "n_crashes":      5,
      "mean_similarity": 0.79,
      "aadt":            83000,
      "intensity_ratio": 2.4,          // vs FL interstate same-conditions baseline
      "severity_mix":   { "fatal": 1, "serious": 3, "minor": 1 },
      "top_factors":    [
        { "factor": "wet surface",  "fraction": 1.00 },
        { "factor": "rear-end",     "fraction": 0.80 },
        { "factor": "dusk_to_dark", "fraction": 0.60 }
      ],
      "coaching_line":  "The right lane bunches up approaching this exit. If you're staying on I-75, move left by Exit 138. If exiting, brake earlier than you think you need to."
    }
    // ... 2-5 more, ranked by intensity
  ],
  "pre_trip_checklist": [
    "Tires and fuel checked",
    "Offline maps cached (I-75 loses cell signal near Alligator Alley)",
    "Water and a snack in reach",
    "Headlights on by 18:45, earlier if cloud cover",
    "Phone mounted; passenger handles texts"
  ]
}
```

**`GET /hotspots/{hotspot_id}`**

```jsonc
// response (briefing-card payload)
{
  "hotspot_id":   "h_01HX...",
  "label":        "I-75 NB approaching Exit 136, Fort Myers",
  "road_name":    "I-75",
  "centroid":     { "lat": 26.6102, "lon": -81.8234 },
  "summary": {
    "n_crashes":       5,
    "mean_similarity": 0.79,
    "aadt":            83000,
    "intensity_ratio": 2.4,
    "severity_mix":    { "fatal": 1, "serious": 3, "minor": 1 },
    "top_factors":     [
      { "factor": "wet surface",  "fraction": 1.00 },
      { "factor": "rear-end",     "fraction": 0.80 },
      { "factor": "dusk_to_dark", "fraction": 0.60 }
    ]
  },
  "coaching_line": "The right lane bunches up approaching this exit. If you're staying on I-75, move left by Exit 138. If exiting, brake earlier than you think you need to.",
  "excerpts": [
    {
      "crash_id":   "c_ciss_2022FL00218",
      "source":     "CISS",
      "similarity": 0.84,
      "when":       "2022-08-14T18:40:00",
      "severity":   "serious",
      "snippet":    "Vehicle 1 northbound on I-75 decelerating in the right lane approaching the Colonial Boulevard exit under light rain. Vehicle 2 following at estimated 70 mph failed to maintain following distance..."
    }
    // ... 1-2 more, diverse in severity / source
  ]
}
```

**`GET /health`** — standard liveness probe.

---

## 7. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│             Frontend (Vite + React + Leaflet)                   │
│  Origin/dest form · Map with polyline · Hotspot pins            │
│  Conditions banner · Fatigue plan · Briefing card modal         │
│  Pre-trip checklist                                             │
└─────────────────────────────────┬────────────────────────────────┘
                                  │  REST + JSON
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                   routewise-api (FastAPI)                        │
│  /trip/brief  ·  /hotspots/:id  ·  /health                       │
│   - orchestrate: OSRM + Open-Meteo + pysolar + VDB in parallel   │
│   - embed query SituationDoc (local MiniLM)                      │
│   - DBSCAN cluster → AADT normalize → rank hotspots              │
│   - coaching-line rule lookup                                    │
│   - fatigue / rest-stop plan composition                         │
└───────────┬──────────────┬───────────────┬───────────────────────┘
            │              │               │
            ▼              ▼               ▼
    ┌──────────────┐  ┌────────────┐  ┌──────────────────────────┐
    │ OSRM HTTP    │  │ Open-Meteo │  │ Actian VectorAI DB       │
    │ (routing)    │  │ (weather)  │  │ routewise_crashes        │
    └──────────────┘  └────────────┘  │ ~500K-1M points          │
                                      └──────────────────────────┘

            ▲ (one-time ingestion jobs)
            │
  ┌─────────┴─────────────────────┐
  │  scripts/ingest_fars.py       │
  │  scripts/ingest_ciss.py       │
  │  scripts/ingest_fdot_crash.py │
  │  scripts/attach_aadt.py       │
  └───────────────────────────────┘
```

**Reused from RigSense** (saves real time):

- `models/all-MiniLM-L6-v2/` — same model, bundled, offline.
- `backend/backend/embeddings.py` — local offline wrapper.
- `backend/backend/config.py` — Settings pattern.
- VectorAI DB client wrapper.
- `vectorai-db-beta/docker-compose.yml`.
- `install.sh` / `start.sh` structure.
- FastAPI project skeleton, deterministic `uuid5` point IDs.

**New dependencies:**

- `h3` (Python) — hex cell indexing.
- `scikit-learn` — DBSCAN for hotspot clustering, KDTree for AADT snap.
- `shapely`, `pyproj` — AADT segment geometry handling.
- `pysolar` — sunset / sunrise computation.
- `httpx` — OSRM + Open-Meteo clients (async).
- Frontend: `leaflet`, `react-leaflet`.

**Explicitly not new:** NetworkX, OSMnx, a full road graph. We route
via OSRM (public API or a one-shot self-hosted container) and never
load Florida's drivable graph into memory ourselves.

---

## 8. Scope

### 8.1 In scope (must ship)

- Florida only, 2018-2022 crash window.
- Vector index of **FARS + FDOT open crashes (templated)** + **CISS
  narratives** (national, retrieved by similarity).
- **AADT exposure normalization** on every indexed crash and in
  hotspot ranking.
- Single-route retrieval: one route per trip, no alternates, no
  lambda.
- H3-filtered similarity search with DBSCAN hotspot clustering,
  intensity-ranked.
- Three pre-verified demo trips:
  - **Miami → Tampa** (the hero demo; classic teen first-long-drive)
  - **Jacksonville → Pensacola** (the fatigue-and-rural demo; I-10
    shows off the long-trip framing)
  - **Orlando ↔ Tampa** on I-4 (the verification demo; retrieval
    surfaces what locals already call "Florida's deadliest
    interstate")
- Briefing card UI: label, coaching line, aggregate factors, AADT
  context, intensity ratio, 2-3 narrative excerpts, severity mix.
- Conditions banner (weather segments + sunset + dark-drive minutes).
- Fatigue plan (rest-stop suggestions).
- Pre-departure checklist.
- Weather presets (clear day / thunderstorm evening / fog morning) so
  the demo is not dependent on real weather at demo time.
- Demo is resilient offline: pre-cached `/trip/brief` responses for
  the three demo trips under each weather preset.

### 8.2 Out of scope (explicitly rejected)

- Multi-objective routing, alternate routes, risk-colored route
  overlay.
- Turn-by-turn nav, any mobile form factor, any in-car integration.
- Real-time traffic.
- Live weather at demo time (use presets — see 8.1).
- Map-matching crashes to road graph edges via HMM (H3 nearest-cell +
  AADT snap is sufficient).
- Multi-state routing.
- User accounts, trip history, personalization.
- LLM-synthesized coaching lines (rule-based only; LLM is a
  descope-restore item).
- Pedestrian / bicycle crash retrieval (trips go interstate → we're
  not surfacing urban-arterial pedestrian risk; scope it out
  explicitly).

### 8.3 Descope-first list

Pull in this order if the week runs tight:

1. Orlando ↔ Tampa I-4 verification demo (ship two trips instead of
   three).
2. Intensity ratio vs. road-class baseline (show absolute crashes-per-
   million-passes instead; simpler, still honest).
3. Fog-morning weather preset.
4. Diverse-excerpt selection (take top 3 by similarity regardless of
   source).
5. Aggregate "top factors" computation (show excerpts only).
6. CISS ingestion (ship with FARS + FDOT templated narratives only —
   this is the heaviest descope; pull last).

### 8.4 Descope-restore list (if time is ahead)

Add in this order if Day 5 arrives with nothing burning:

1. **LLM-synthesized coaching lines** (call GPT-4 or a local
   Llama-3-8B; 5-10 calls per trip, trivially cheap, makes the demo
   feel crafted).
2. Second state (e.g., GA I-75 continuation) so judges see the
   pattern isn't hard-coded to FL.
3. A "why this hotspot?" expander that lists the top 5 retrieval
   terms that drove the cluster's similarity — peek behind the
   curtain, reinforces the VDB story.
4. Route-level severity chart (histogram of hotspot severities
   across the whole trip, front/back-loaded visualization).

---

## 9. One-week execution plan

| Day | Deliverable | Definition of done |
|---|---|---|
| **1** | Data ingestion end-to-end | `routewise_crashes` holds ≥50K embedded docs from FARS + FDOT; CISS narratives sample-inspected. H3 cells and AADT volumes populated on every payload where geometry allows. |
| **2** | Query orchestration | `POST /trip/brief` returns route polyline + conditions banner + fatigue plan + raw top-k crashes for Miami → Tampa. No clustering yet. |
| **3** | Clustering + hotspot composition + AADT ranking | Same endpoint now returns 3-6 hotspots ranked by intensity, with labels, factor aggregates, and rule-based coaching lines. |
| **4** | Frontend: map + pins + briefing card skeleton + conditions banner | Leaflet map renders the route, pins drop at hotspot centroids, clicking a pin opens a briefing card with real data, banner and fatigue plan render. |
| **5** | Polish: excerpts, severity chips, weather presets, checklist | Briefing cards have diverse narrative excerpts, severity bars, intensity ratio shown plainly, three weather presets toggle, checklist in place. |
| **6** | Pre-cache, pitch, full dress rehearsal | All three demo trips × all presets pre-cached to disk, served from cache at demo time. Pitch deck done. |
| **7** | Buffer | Bug fixes; record 90-second backup video of the hero demo. |

### 9.1 Non-negotiable checkpoints

- **End of Day 1**: if the index isn't populated and queryable with
  H3 filters, and ≥80% of crashes have AADT attached, stop and
  re-plan. Everything downstream assumes this works.
- **End of Day 3**: if `/trip/brief` isn't returning at least 3
  plausible hotspots for Miami → Tampa, pull descope items #5 and
  #4.
- **End of Day 5**: feature freeze. Days 6-7 are polish only.

---

## 10. Risks and known unknowns

| Risk | Mitigation |
|---|---|
| CISS narratives are heavily PII-redacted | Sample-inspect 50 on Day 1. If redaction ratio ≥40%, switch focus to templated-narrative quality and treat CISS as "bonus" text. Corpus is still viable without CISS text quality. |
| FDOT Open Data crash layer has unexpected shape / encoding | Budget half of Day 1 for FDOT crash ingestion. Have the template renderer ready to ship on FARS + CISS alone as a fallback. |
| AADT snap fails for off-interstate crashes (local roads missing from FGDL layer) | Crashes with `aadt=None` are still indexed and retrievable; we just don't show intensity ratio for clusters over unmatched segments. State it honestly in the briefing card. |
| CISS is national, not FL-heavy; risk that excerpts feel "wrong state" | Narratives retrieve by situational similarity anyway; but guard by preferring CISS hits whose `state` is FL or adjacent (GA/AL) when available. |
| OSRM public API rate-limits at demo time | Use OSRM for data prep, cache polylines for the three demo routes, serve from cache at demo time. |
| VectorAI DB payload filter on large IN-lists (2K+ H3 cells for 300-mile routes) underperforms | Fall back: global top-300 retrieval + in-memory H3 post-filter. Still sub-second. |
| Hotspot clusters are noisy on first pass | Day 3-4 tuning session on the hero trip: inspect clusters, adjust DBSCAN eps and similarity threshold τ, curate 2-3 labeled hotspots per demo trip to guarantee demo quality. |
| Coaching lines sound robotic | Rule table hand-crafted for the 10-15 most common factor tuples. Descope-restore: swap to LLM synthesis on Day 6. |
| Demo WiFi fails at venue | Serve from pre-cached JSON on disk. Record the 90-second backup video on Day 7 regardless. |

---

## 11. Product integrity

This section exists because the concerns below are obvious to any
thoughtful judge and pretending they don't exist is the worst move we
can make. Each concern gets named, gets a mitigation, and gets
reflected in the UI so we're not over-claiming.

### 11.1 Survivorship bias — "where crashes happened" ≠ "where it's unsafe"

Crash-only data misleads in two ways: (a) it counts incidents but
not exposure, so high-traffic roads always "look" worst, and
(b) it ignores near-misses and silent safety — a segment with zero
crashes because nobody drives it is not the same as a segment with
zero crashes because it's well-designed.

**What we do about it:**

- **Exposure normalization** is the headline fix. Every hotspot is
  ranked by crash rate per vehicle-pass (§3.4), not raw count. The
  briefing card surfaces the AADT and the intensity ratio in plain
  copy: *"This segment sees ~82,000 vehicles per day. The crash rate
  here in these conditions is about 2.4× the Florida interstate
  average."*
- **We do not claim "this is dangerous."** We claim: "these are the
  crashes that have happened here in conditions like yours." The
  distinction is load-bearing.
- Clusters over segments with `aadt=None` get no intensity ratio and
  get a disclosed softer label (e.g., "Historical cluster — limited
  exposure data"). We show the card, but honestly.

### 11.2 The unmarked-segment false-confidence trap

A driver sees 4 hotspots on their route and infers the rest of the
route is safe. That's wrong. The unmarked 95% of the route may
simply lack retrievable matches in our corpus — not all risk maps
neatly to "in a 300m cluster under these conditions."

**What we do about it:**

- The **conditions banner** spans the entire route, not just
  hotspots. *"You will drive 2 hours in the dark. Thunderstorms for
  much of the drive. The whole route is wet."* These are universal
  hazards, applied across the full route, not pinned to a place.
- The **fatigue plan** applies to the entire route.
- The **pre-departure checklist** applies to the entire route.
- UI copy (explicit, not buried): *"The pins mark where historical
  crashes cluster in tonight's conditions. Every part of this route
  deserves attention — these are the places where it especially
  deserves it."*
- We **do not** color the route green or safe-looking anywhere. The
  polyline is one neutral color end-to-end.

### 11.3 CISS is a sample, not a census

CISS is an investigator-narrative sample of ~4-5K cases/year
nationally. It isn't representative of all crashes in any
jurisdiction. Narratives we retrieve may come from a crash in
Georgia or Texas, not Florida.

**What we do about it:**

- The pitch frames this as a feature: *"real crashes on roads like
  yours in weather like yours"* — similarity-by-situation is the
  product.
- The briefing card labels every excerpt with its source, case id,
  and state. *"CISS 2021GA00417"* is clearly not *"FARS 2020FL..."*.
- We prefer FL/GA/AL cases first when available and have national
  fallback.

### 11.4 Rural coverage is thinnest where fatality rate is highest

Florida's fatal crash rate per vehicle-mile is much higher on rural
two-lane roads than on interstates. We intentionally focus on
interstates — that's where the long-trip use case lives.

**What we do about it:**

- Named scope limit in the README and in §8: "Interstates and
  primary US/state routes only. Unsigned rural roads are out of
  scope." A teen taking US-27 south-to-north is not our user in v1.
- Demo corridors are entirely interstate by design.

### 11.5 Fear-of-death is not pedagogy

Reading about 4 fatal crashes before getting in a car can make a
teen *more* anxious without making them *more* skilled. Bad.

**What we do about it:**

- **Coaching lines are actionable**, not descriptive. *"Double your
  following distance from Exit 6 onward"* is a behavior. *"This is
  where people die"* is not.
- Severity distribution is shown as a small chip, not as the
  headline.
- We prefer excerpts that describe *what the driver did* over
  excerpts that describe *what the outcome was*.
- Tone of voice is driving-instructor, not local-news.

### 11.6 We show our work — recommendation, not absolute claim

Now that we re-rank routes, the old honesty claim ("we're not a
router") doesn't apply. The new claim is tighter:

> *We show you why we recommended it — every segment's crash count,
> AADT, and condition match is visible. We don't hide the reasoning.*

**What we do about it:**

- The chosen route is labeled **"Recommended"**, not "Safest".
  *Safest* is absolute language we can't honor — we can honor
  "fewest matched crash segments under tonight's conditions," which
  is what a recommendation means here.
- Route headlines are the road name the network gave them (*"Via
  Coastal Hwy 101"*), not invented brand names. We didn't name the
  route, the road network did.
- The alternates panel shows, for every candidate: duration, number
  of crash-matched segments, and the "no crash history matching
  tonight's conditions" disclosure when the match count is zero.
  The user can see *why* we picked one route over another.
- Per-segment color coding on the chosen route (§2 pivot block)
  means every risk-scored segment is hoverable. Hover a flagged
  segment and you see the matched crashes, the AADT, and the
  condition match — not just a score.
- Turn the VDB off and the alternates panel collapses to "fastest,"
  every segment renders neutral, and the chosen route is picked by
  duration alone (§2.4). The reasoning stops being visible because
  there's nothing real to show.

---

## 12. Deliverables

1. **Live demo** — the hero trip (Miami → Tampa), thunderstorm-evening
   preset. Show the map, read the conditions banner (*"2 hours of
   dark driving tonight"*), drop pins, click the Fort Myers hotspot,
   read the coaching line aloud, read one CISS excerpt, show the
   AADT intensity ratio. Total: ~90 seconds on stage.
2. **Repo** — documented, seeded, reproducible with `./install.sh` +
   `./start.sh`, same pattern as RigSense.
3. **Pitch deck** (≤10 slides) — problem (teen, unfamiliar long
   drive, 20 minutes before keys), the pitch center (*"we don't just
   tell you when to leave — we tell you which route has the fewest
   crash-matched segments for tonight, and brief you on every
   hotspot"*), why vector DB, exposure denominators via AADT, the
   briefing card as the centerpiece, data architecture, product
   integrity slide (§11), the ask.
4. **Backup video** (90 s) — same flow, recorded locally for the
   wifi-fails-on-stage scenario.

### 12.1 The pitch's money line

> *"RouteWise is the pre-trip briefing a teen never gets before their
> first long drive. We don't just tell you **when** to leave — we
> tell you **which route has the fewest crash-matched segments for
> tonight's conditions**, and brief you on every hotspot along the
> way. We pull the actual crashes that happened on roads like yours
> in weather like yours, normalize by how many cars actually pass
> each place, and show our work: every segment's crash count, AADT,
> and condition match is visible. Turn off the vector database and
> every briefing card goes blank — that's our honesty test."*
