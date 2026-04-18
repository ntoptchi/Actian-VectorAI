# RouteWise — team brief

*One-page version. Full spec: `ROUTEWISE.md`.*

## The idea

**A pre-trip briefing for teens about to do their first unfamiliar long drive.**

Picture a 17-year-old with a 4-hour drive to a cousin's house, college
visit, or spring break. They've driven to school and the mall. They've
**never** driven this route. They've got 20 minutes before they get in
the car.

They paste the route into RouteWise. We show them: the route on a map,
the weather they'll actually hit, when they'll lose daylight, where
they should stop for a break, and — the core — **3-6 places along the
route where real crashes have happened in conditions like tonight's**,
each with a short "what this means for you" coaching line and 2-3 real
investigator-narrative excerpts from those crashes.

They read it in 2 minutes, close the tab, drive better informed. No
in-car anything, no account, no friction.

## Why it's interesting

- **We are not a router.** We don't compete with Google Maps. We take
  the route the user already planned and brief them on it. This is a
  massive scope win — no turn-by-turn, no live nav, no voice.
- **The vector DB is load-bearing, not a bolt-on.** Every briefing
  card is built from retrieved crashes. Turn off the VDB, every card
  goes blank. That's our honesty test on stage.
- **We fix survivorship bias with AADT.** We use FDOT's traffic-volume
  data to rank hotspots by crash rate per vehicle-pass, not raw count.
  "2.4× the Florida interstate average for this segment in rain at
  night" is the kind of claim a thoughtful judge will actually respect.

## Stack

- **Vector DB**: Actian VectorAI DB (same setup as our RigSense build).
- **Embeddings**: `all-MiniLM-L6-v2`, bundled locally, offline.
- **Backend**: FastAPI, Python. Reuses chunks of the RigSense backend
  (config, embedding wrapper, VDB client).
- **Frontend**: Vite + React + Leaflet.
- **Data**: FARS (fatalities), FDOT Open Data crash layers (FL
  non-fatals), CISS (national, narrative text), FDOT AADT shapefile
  (exposure).
- **Routing / weather**: OSRM + Open-Meteo + `pysolar`. Free, no keys.
- **Scope**: Florida only. Three demo corridors: Miami→Tampa,
  Jacksonville→Pensacola, Orlando↔Tampa.

## The demo (90 seconds)

1. Open RouteWise. Paste **Miami → Tampa**, departing 18:30 tonight.
2. Page renders: map with route, conditions banner
   (*"Thunderstorms along I-75 · Sunset at 19:42 · You'll drive 2
   hours in the dark"*), fatigue plan (*"Stop at Fort Myers ~2h in"*),
   5 hotspot pins.
3. Click the Fort Myers pin. Briefing card opens:
   - Location + road feature ("I-75 NB approaching Exit 136").
   - Aggregate: *"5 crashes here matched your conditions. 4 were
     rear-ends. This segment sees 83K vehicles/day — crash rate is
     2.4× the FL interstate average in these conditions."*
   - Real CISS investigator excerpt verbatim.
   - Coaching line: *"Right lane bunches up here. Move left by Exit
     138, or brake earlier than you think if you're exiting."*
4. Pitch line: *"Turn off the vector database, every briefing card
   goes blank. That's our honesty test."*

## Week plan at a glance

| Day | Who owns it | What ships |
|---|---|---|
| 1 | Data person | Crash + AADT ingestion into VDB, ≥50K docs, AADT attached |
| 2 | Backend | `/trip/brief` returns route + conditions + raw top-k |
| 3 | Backend + Data | Clustering + AADT ranking + coaching rules → hotspots |
| 4 | Frontend | Map, pins, briefing card skeleton, conditions banner |
| 5 | Everyone | Excerpts, severity chips, weather presets, checklist |
| 6 | Everyone | Pre-cache demos, pitch deck, dress rehearsal |
| 7 | Buffer | Bugs, record backup video |

**Feature freeze end of Day 5.** Days 6-7 are polish only.

## Work streams (roughly)

- **Data & ingestion**: FARS + FDOT + CISS download/normalize, AADT
  snap, H3 cells, embed + upsert. Python + shapely + scikit-learn.
- **Backend API**: orchestrate OSRM/Open-Meteo/VDB, DBSCAN cluster,
  AADT intensity, rule-based coaching lines. FastAPI + async httpx.
- **Frontend**: Leaflet map, briefing card component, conditions
  banner, fatigue plan, checklist. React + Leaflet.
- **Demo & pitch**: pre-cached JSON for three demo trips × three
  weather presets, 10-slide deck, 90-second backup video.

## What's explicitly out of scope

No alternate routes. No risk coloring on the route line. No real-time
anything. No mobile app. No user accounts. No LLM-generated coaching
(rule-based; LLM is a stretch goal if Day 5 arrives early).

## Read next

- **`ROUTEWISE.md`** — full engineering spec with schemas, API
  shapes, data flow, and product-integrity section.
- Existing **`backend/`** folder — RigSense, which we'll fork the
  skeleton from.
