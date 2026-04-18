# RouteWise data layout

This directory holds raw downloads, intermediate artifacts, and the
pre-cached `/trip/brief` payloads we serve at demo time. Everything
under `raw/`, `processed/`, and `cache/` is git-ignored — only this
README is tracked.

```
data/
  raw/          # downloaded FARS / CISS / FDOT / FGDL files (you put them here)
  processed/    # built artifacts: aadt_index.pkl, baselines.json, ...
  cache/        # pre-cached /trip/brief responses for the three demo trips
```

The ingestion CLIs (`scripts/ingest_*.py`, `scripts/attach_aadt.py`)
all read from `data/raw/<source>/...` by default; override with the
`--shapefile` / `--years` flags if you put files elsewhere.

---

## What you need to download

All sources are public and require **no credentials**. You handle the
fetch; the pipeline handles everything else.

### 1. FARS — NHTSA fatal crashes (FL subset, 2018-2022)

Backbone of the structured fatal-crash corpus.

- **Source:** <https://www.nhtsa.gov/file-downloads?p=nhtsa%2Fdownloads%2FFARS%2F>
- **Files per year:** the `National_*.zip` (or `FL_*.zip` if NHTSA
  publishes the per-state zip) — at minimum we need `accident.csv`.
- **Where to put it:** `data/raw/FARS/<year>/accident.csv`
- **Filter applied at ingest:** `STATE == 12` (Florida).

```
data/raw/FARS/
  2018/accident.csv
  2019/accident.csv
  2020/accident.csv
  2021/accident.csv
  2022/accident.csv
```

Run: `python scripts/ingest_fars.py --years 2018,2019,2020,2021,2022`

### 2. CISS — NHTSA Crash Investigation Sample (national, 2017-present)

Source of investigator narratives. Small (~4-5K cases/year nationally),
but high-value for the briefing card excerpts (ROUTEWISE.md s4).

- **Source:** <https://www.nhtsa.gov/file-downloads?p=nhtsa%2Fdownloads%2FCISS%2F>
- **Where to put it:** `data/raw/CISS/<year>/cases.jsonl`
  (one merged case per line; merge of the case-header / scene /
  narrative tables — see the docstring in `backend/ingest/normalize.py`
  for the join plan.)

Run: `python scripts/ingest_ciss.py --years 2018,2019,2020,2021,2022`

### 3. FDOT Open Data — FL non-fatal crash layer

Broad FL non-fatal coverage, geocoded.

- **Source:** <https://gis-fdot.opendata.arcgis.com/>
  Search for the most recent **Crash** layer (e.g., "Crashes 2019" /
  "Crashes 2020" / ...). Download as **GeoJSON** (preferred) or
  **Shapefile**.
- **Where to put it:** `data/raw/FDOT/crash/*.geojson` (any number).

Run: `python scripts/ingest_fdot_crash.py`

### 4. FGDL AADT shapefile — exposure denominator

Annual Average Daily Traffic per road segment. The single most
important non-crash dataset (ROUTEWISE.md s3.4).

- **Source:** <https://fgdl.org/> — search for `aadt_*` (the most
  recent year). Download the **shapefile** (zip).
- **Where to put it:** unzip into `data/raw/FGDL/aadt/` so you have at
  least an `aadt_<year>.shp` (and its `.dbf`, `.shx`, `.prj`).

Then build the spatial index once:

```
python scripts/attach_aadt.py
```

This writes `data/processed/aadt_index.pkl`. After it exists, re-run
`scripts/ingest_*` and every indexed crash gets `aadt` /
`aadt_segment_id` populated where its lat/lon snaps within 50 m of a
segment (ROUTEWISE.md s5.1.4).

---

## Demo-time cache (`data/cache/`)

ROUTEWISE.md s8.1 says the demo serves pre-cached `/trip/brief`
responses for the three demo trips (Miami<->Tampa, Jacksonville<->
Pensacola, Orlando<->Tampa) under each weather preset. Day-6 work
populates this directory; it's empty for now.

Suggested layout:

```
data/cache/
  miami_tampa__thunderstorm_evening.json
  miami_tampa__clear_day.json
  jax_pensacola__fog_morning.json
  ...
```

---

## Out of scope (deliberately not used)

- **Signal Four Analytics (S4A)** — gated to FL gov/consultants.
- **FDOT CAR system** — gated via Automated Access Request Form.

We stay in the public lane. See ROUTEWISE.md s4 for the full
"why we picked these sources" rationale.
