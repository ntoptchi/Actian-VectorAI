"""
Stage 5 — orchestrator.

For each candidate crash:
  1. Brave Search (1 rps, rate-limited token bucket)
  2. Fetch up to N article URLs in parallel via curl_cffi
  3. Score each with matcher.score_match
  4. If best >= threshold, append to semanticCrashes.json
  5. Else append to unmatched.json (with top-3 candidates for review)

Resumable: at start, the already-linked + already-unmatched crash_ids are
skipped.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from article import SessionPool, extract_article, fetch_html, should_skip_url
from brave import BraveClient, build_queries
from candidates import (
    CANDIDATES_PATH,
    DATE_END,
    DATE_START,
    TIER_ORDER,
    load_candidates,
)
from matcher import DEFAULT_THRESHOLD, pick_best

log = logging.getLogger("nextup.linker")

HERE = os.path.dirname(os.path.abspath(__file__))
SEMANTIC_PATH = os.path.join(HERE, "data", "semanticCrashes.json")
UNMATCHED_PATH = os.path.join(HERE, "data", "unmatched.json")

ARTICLE_FETCH_CAP = 5
FLUSH_EVERY_LINKED = 10
FLUSH_EVERY_PROCESSED = 50


def _atomic_write(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _load_json(path: str, default: Dict[str, Any]) -> Dict[str, Any]:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        log.warning("could not parse %s, starting fresh", path)
        return default


def _empty_semantic() -> Dict[str, Any]:
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "dateRange": {"start": DATE_START.isoformat(), "end": DATE_END.isoformat()},
        "filter": "serious_only",
        "counts": {"linked": 0, "unmatched": 0},
        "semanticCrashes": [],
    }


def _empty_unmatched() -> Dict[str, Any]:
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "unmatched": [],
    }


def run(
    *,
    limit: Optional[int] = None,
    tier: str = "all",
    threshold: int = DEFAULT_THRESHOLD,
    workers: int = 20,
    dry_run: bool = False,
    candidates_path: str = CANDIDATES_PATH,
    semantic_path: str = SEMANTIC_PATH,
    unmatched_path: str = UNMATCHED_PATH,
) -> Dict[str, Any]:
    cand_doc = load_candidates(candidates_path)
    all_candidates: List[Dict[str, Any]] = cand_doc.get("candidates") or []

    if tier != "all":
        all_candidates = [c for c in all_candidates if c.get("tier") == tier]

    all_candidates.sort(key=lambda c: (TIER_ORDER.index(c.get("tier", TIER_ORDER[-1])), c.get("crash_date", "")))

    semantic = _load_json(semantic_path, _empty_semantic())
    unmatched = _load_json(unmatched_path, _empty_unmatched())

    done_ids = {e.get("crash_id") for e in semantic.get("semanticCrashes", [])}
    done_ids |= {e.get("crash_id") for e in unmatched.get("unmatched", [])}

    work: List[Dict[str, Any]] = [c for c in all_candidates if c.get("crash_id") not in done_ids]
    if limit is not None:
        work = work[:limit]

    log.info(
        "linker start: total_candidates=%d already_done=%d will_process=%d tier=%s threshold=%d dry_run=%s",
        len(all_candidates), len(done_ids), len(work), tier, threshold, dry_run,
    )
    if not work:
        log.info("nothing to do")
        return {"linked": 0, "unmatched": 0, "processed": 0}

    brave = BraveClient()
    pool = SessionPool(rotate_every=25)

    lock = threading.Lock()
    stats = {"linked": 0, "unmatched": 0, "processed": 0, "errors": 0}

    def flush() -> None:
        if dry_run:
            return
        semantic["counts"] = {
            "linked": len(semantic.get("semanticCrashes", [])),
            "unmatched": len(unmatched.get("unmatched", [])),
        }
        semantic["generatedAt"] = datetime.now(timezone.utc).isoformat()
        unmatched["generatedAt"] = semantic["generatedAt"]
        _atomic_write(semantic_path, semantic)
        _atomic_write(unmatched_path, unmatched)

    def process(crash: Dict[str, Any]) -> Tuple[str, str, Optional[Dict[str, Any]]]:
        cid = crash.get("crash_id") or ""
        queries = build_queries(crash)
        all_hits: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()

        for q in queries:
            try:
                hits = brave.search(q, count=10)
            except Exception as exc:
                log.warning("[%s] brave search failed: %s", cid, exc)
                with lock:
                    stats["errors"] += 1
                continue
            for h in hits:
                u = h.get("url")
                if not u or u in seen_urls:
                    continue
                seen_urls.add(u)
                all_hits.append(h)
            if len(all_hits) >= ARTICLE_FETCH_CAP:
                break

        if not all_hits:
            return cid, "unmatched", {"reason": "no_search_results", "queries": queries, "hits": []}

        usable_hits: List[Dict[str, Any]] = []
        for h in all_hits:
            skip_reason = should_skip_url(h["url"])
            if skip_reason:
                continue
            usable_hits.append(h)
            if len(usable_hits) >= ARTICLE_FETCH_CAP:
                break

        if not usable_hits:
            return cid, "unmatched", {
                "reason": "no_fetchable_hits",
                "queries": queries,
                "hits": [{"url": h["url"], "title": h["title"]} for h in all_hits[:3]],
            }

        articles: List[Dict[str, Any]] = []
        for h in usable_hits:
            try:
                html = fetch_html(pool, h["url"])
            except Exception as exc:
                log.debug("[%s] fetch failed %s: %s", cid, h["url"], exc)
                continue
            if not html:
                continue
            try:
                art = extract_article(html, h["url"])
            except Exception as exc:
                log.debug("[%s] extract failed %s: %s", cid, h["url"], exc)
                continue
            if not art.get("text"):
                continue
            art["searchDescription"] = h.get("description")
            articles.append(art)

        if not articles:
            return cid, "unmatched", {
                "reason": "no_extractable_articles",
                "queries": queries,
                "hits": [{"url": h["url"], "title": h["title"]} for h in usable_hits[:3]],
            }

        best, scored = pick_best(articles, crash, threshold=threshold)

        if best is not None:
            linked_entry = {
                "crash_id": cid,
                "matchScore": best["matchScore"],
                "matchReasons": best["matchReasons"],
                "queries": queries,
                "article": {
                    "title": best.get("title") or "",
                    "text": best.get("text") or "",
                    "link": best.get("link") or "",
                    "publishedDate": best.get("publishedDate"),
                    "author": best.get("author"),
                    "source": best.get("source") or "",
                },
                "crash": crash.get("properties") or {},
                "crashGeometry": crash.get("geometry"),
                "crashTier": crash.get("tier"),
                "crashDate": crash.get("crash_date"),
            }
            return cid, "linked", linked_entry

        top3 = [
            {
                "url": a.get("link"),
                "title": a.get("title"),
                "publishedDate": a.get("publishedDate"),
                "matchScore": a.get("matchScore"),
                "matchReasons": a.get("matchReasons"),
                "disqualifyReason": a.get("disqualifyReason"),
            }
            for a in scored[:3]
        ]
        return cid, "unmatched", {
            "reason": "below_threshold",
            "threshold": threshold,
            "queries": queries,
            "topCandidates": top3,
        }

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="linker") as pool_ex:
        futures = {pool_ex.submit(process, c): c for c in work}
        for fut in as_completed(futures):
            crash = futures[fut]
            cid = crash.get("crash_id")
            try:
                cid_out, status, payload = fut.result()
            except Exception as exc:
                log.error("[%s] unhandled: %s", cid, exc)
                with lock:
                    stats["errors"] += 1
                    stats["processed"] += 1
                continue

            with lock:
                stats["processed"] += 1
                if status == "linked":
                    semantic["semanticCrashes"].append(payload)
                    stats["linked"] += 1
                    title = (payload["article"].get("title") or "").strip()
                    if len(title) > 110:
                        title = title[:107] + "..."
                    print(
                        f">>> FOUND #{stats['linked']:04d}  "
                        f"[{crash.get('tier', '?'):<10}] "
                        f"score={payload['matchScore']:3d}  "
                        f"{cid_out}  {crash.get('crash_date', '')}  "
                        f"{payload['article'].get('source', '')}\n"
                        f"     title : {title}\n"
                        f"     link  : {payload['article']['link']}",
                        flush=True,
                    )
                    if stats["linked"] % FLUSH_EVERY_LINKED == 0:
                        flush()
                        print(
                            f"     [flush] saved state after {stats['linked']} found candidates "
                            f"(processed={stats['processed']}, unmatched={stats['unmatched']})",
                            flush=True,
                        )
                else:
                    unmatched["unmatched"].append({
                        "crash_id": cid_out,
                        "tier": crash.get("tier"),
                        "crash_date": crash.get("crash_date"),
                        **(payload or {}),
                    })
                    stats["unmatched"] += 1
                    reason = (payload or {}).get("reason", "?")
                    log.info("[%s] unmatched (%s)  [%d processed]", cid_out, reason, stats["processed"])

                if stats["processed"] % FLUSH_EVERY_PROCESSED == 0:
                    flush()

    flush()

    log.info(
        "linker done: processed=%d linked=%d unmatched=%d errors=%d",
        stats["processed"], stats["linked"], stats["unmatched"], stats["errors"],
    )
    return stats
