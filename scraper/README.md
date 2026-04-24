# Scraper — crash ↔ news article linker

Pipeline that takes the Florida FDOT crash GeoJSON in `data/raw/crash*.json`,
filters to newsworthy crashes in the June 11 – Nov 7, 2011 window, queries
Brave Search for each, fetches and extracts the article body, scores the
match, and writes `{ article, crash }` pairs to `data/semanticCrashes.json`.

## Setup

```bash
cd accscent/scraper/nextup
pip install -r requirements.txt
cp .env.example .env
# paste your Brave API key into .env
```

## Usage

```bash
# 1. build the candidate crash subset (fast, runs once)
python main.py candidates

# 2. dry run against 20 fatal crashes to sanity-check the pipeline
python main.py link --limit 20 --tier fatal

# 3. full run (resumable — safe to re-run after interruption)
python main.py link
```

CLI flags:

- `--limit N`         stop after processing N crashes
- `--tier TIER`       only process a given tier: `fatal`, `serious`, `vulnerable`, `wrongway`, or `all` (default)
- `--threshold N`     match score threshold (default 55)
- `--dry-run`         run the full pipeline but don't write outputs
- `--workers N`       article-fetch worker count (default 20)

## Output

`data/semanticCrashes.json` schema:

```json
{
  "semanticCrashes": [
    { "article": { "title": "...", "text": "...", "link": "..." }, "crash": { ... } }
  ]
}
```

`data/unmatched.json` holds crashes with no confident match, including the
top 3 candidate URLs + scores for manual review.

## Architecture

```
candidates.py  -> filter crash*.json -> candidates.json
brave.py       -> Brave Search API client (1 rps token bucket)
article.py     -> curl_cffi + trafilatura article fetch/extract
matcher.py     -> weighted article<->crash scoring (0-100)
linker.py      -> ThreadPoolExecutor orchestrator, resumable
main.py        -> CLI wiring the stages together
```
