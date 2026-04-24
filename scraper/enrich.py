"""
LLM enrichment stage for linked semantic crashes.
"""

from __future__ import annotations

import copy
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError, field_validator

from factor_vocab import (
    DRIVER_DEMOGRAPHIC_VALUES,
    EXTRACTION_CONFIDENCE_VALUES,
    FACTOR_TAGS,
    DriverDemographic,
    ExtractionConfidence,
    FactorTag,
    OutcomeSeverity,
    PREVENTABILITY_VALUES,
    PRIMARY_DRIVER_ACTION_VALUES,
    Preventability,
    PrimaryDriverAction,
)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
INPUT_PATH = os.path.join(DATA_DIR, "semanticCrashes.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "semanticCrashesEnriched.json")
VOCAB_VERSION = 1
FLUSH_EVERY_SUCCESS = 10


class EnrichmentResult(BaseModel):
    context_conditions: str
    context_road: str
    lesson_cause: str
    lesson_advice: str
    lesson_teen: str
    retelling: str
    factor_tags: list[FactorTag] = Field(min_length=2, max_length=6)
    preventability: Preventability
    primary_driver_action: PrimaryDriverAction
    driver_demographic: DriverDemographic
    outcome_severity: OutcomeSeverity
    extraction_confidence: ExtractionConfidence

    @field_validator("lesson_advice")
    @classmethod
    def _validate_lesson_advice_words(cls, value: str) -> str:
        if len(value.split()) > 30:
            raise ValueError("lesson_advice must be <= 30 words")
        return value


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: str, fallback: Any) -> Any:
    if not os.path.exists(path):
        return fallback
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _atomic_write_json(path: str, payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _build_system_prompt() -> str:
    return f"""
You extract structured driving-safety insights from a crash news article.
Return only fields from the provided JSON schema.

Rules:
- Use only facts from the input article text. If not present, use "NOT_STATED"
  for free-text fields and "not_stated"/"unknown" enum values where applicable.
- Keep `lesson_advice` concise and action-oriented, max 30 words.
- Select 2-6 `factor_tags` from the frozen list only.
- Do not invent locations, demographics, intoxication, or speeds.
- Keep language neutral and factual.

Frozen vocab:
- factor_tags: {", ".join(FACTOR_TAGS)}
- preventability: {", ".join(PREVENTABILITY_VALUES)}
- primary_driver_action: {", ".join(PRIMARY_DRIVER_ACTION_VALUES)}
- driver_demographic: {", ".join(DRIVER_DEMOGRAPHIC_VALUES)}
- outcome_severity: fatal, serious, minor, pdo, unknown
- extraction_confidence: {", ".join(EXTRACTION_CONFIDENCE_VALUES)}
""".strip()


def _article_payload(entry: dict[str, Any]) -> dict[str, Any]:
    article = entry.get("article", {}) or {}
    return {
        "title": article.get("title"),
        "publishedDate": article.get("publishedDate"),
        "source": article.get("source"),
        "text": (article.get("text") or "")[:8000],
    }


def _enrich_once(client: OpenAI, model: str, entry: dict[str, Any]) -> EnrichmentResult:
    user_content = {
        "article": _article_payload(entry),
        "crash_id": entry.get("crash_id"),
        "matchScore": entry.get("matchScore"),
    }
    completion = client.beta.chat.completions.parse(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)},
        ],
        response_format=EnrichmentResult,
    )
    message = completion.choices[0].message
    if message.parsed is not None:
        return message.parsed
    if getattr(message, "refusal", None):
        raise RuntimeError(f"model refusal: {message.refusal}")
    raise RuntimeError("structured output parse failed: empty parsed payload")


def _enrich_with_retry(client: OpenAI, model: str, entry: dict[str, Any], retries: int = 2) -> dict[str, Any]:
    attempt = 0
    while True:
        attempt += 1
        try:
            parsed = _enrich_once(client, model, entry)
            return parsed.model_dump()
        except Exception as exc:  # noqa: BLE001
            if attempt > retries + 1:
                return {
                    "error": str(exc),
                    "attempts": attempt,
                    "extractedAt": _utc_now_iso(),
                }
            time.sleep(0.75 * (2 ** (attempt - 1)))


def _is_valid_enrichment(payload: Any) -> bool:
    if not isinstance(payload, dict) or "error" in payload:
        return False
    try:
        EnrichmentResult.model_validate(payload)
        return True
    except ValidationError:
        return False


def run(
    limit: int | None = None,
    min_score: int | None = None,
    workers: int = 10,
    model: str | None = None,
    retry_failed: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    source = _read_json(INPUT_PATH, {"semanticCrashes": []})
    source_items = source.get("semanticCrashes", [])
    existing = _read_json(OUTPUT_PATH, {"semanticCrashes": []})
    existing_map: dict[str, dict[str, Any]] = {}
    for item in existing.get("semanticCrashes", []):
        cid = str(item.get("crash_id") or "")
        if cid:
            existing_map[cid] = item

    output_doc: dict[str, Any] = {
        "generatedAt": _utc_now_iso(),
        "dateRange": source.get("dateRange"),
        "model": model or os.getenv("OPENAI_MODEL", "gpt-5.4"),
        "vocabVersion": VOCAB_VERSION,
        "counts": {
            "enriched": 0,
            "failed": 0,
            "skipped_low_confidence": 0,
        },
        "semanticCrashes": [],
    }

    work: list[tuple[int, dict[str, Any]]] = []
    for src_item in source_items:
        item = copy.deepcopy(src_item)
        cid = str(item.get("crash_id") or "")
        old = existing_map.get(cid, {})
        old_enrichment = old.get("enrichment")
        if old_enrichment is not None:
            item["enrichment"] = old_enrichment
        output_doc["semanticCrashes"].append(item)

    for idx, item in enumerate(output_doc["semanticCrashes"]):
        score = item.get("matchScore")
        if min_score is not None and isinstance(score, (int, float)) and score < min_score:
            output_doc["counts"]["skipped_low_confidence"] += 1
            continue
        enrichment = item.get("enrichment")
        if _is_valid_enrichment(enrichment):
            continue
        if isinstance(enrichment, dict) and "error" in enrichment and not retry_failed:
            continue
        work.append((idx, item))
        if limit is not None and len(work) >= limit:
            break

    if dry_run and len(work) > 3 and limit is None:
        work = work[:3]

    if not work:
        if not dry_run:
            _atomic_write_json(OUTPUT_PATH, output_doc)
        return {
            "processed": 0,
            "enriched": 0,
            "failed": 0,
            "skipped_low_confidence": output_doc["counts"]["skipped_low_confidence"],
            "already_done": len(source_items) - output_doc["counts"]["skipped_low_confidence"],
        }

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-5.4")
    lock = threading.Lock()
    stats = {"processed": 0, "enriched": 0, "failed": 0}

    def _worker(entry: dict[str, Any]) -> dict[str, Any]:
        return _enrich_with_retry(client=client, model=model_name, entry=entry, retries=2)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(_worker, item): (idx, item) for idx, item in work}
        for future in as_completed(futures):
            idx, item = futures[future]
            result = future.result()
            with lock:
                stats["processed"] += 1
                output_doc["semanticCrashes"][idx]["enrichment"] = result
                if "error" in result:
                    stats["failed"] += 1
                else:
                    stats["enriched"] += 1
                    print(
                        ">>> ENRICHED "
                        f"#{stats['processed']:04d}  crash_id={item.get('crash_id')}  "
                        f"sev={result.get('outcome_severity')}  "
                        f"conf={result.get('extraction_confidence')}  "
                        f"tags={result.get('factor_tags')}"
                    )
                    if not dry_run and stats["enriched"] % FLUSH_EVERY_SUCCESS == 0:
                        output_doc["generatedAt"] = _utc_now_iso()
                        output_doc["model"] = model_name
                        output_doc["counts"]["enriched"] = stats["enriched"]
                        output_doc["counts"]["failed"] = stats["failed"]
                        _atomic_write_json(OUTPUT_PATH, output_doc)

    output_doc["generatedAt"] = _utc_now_iso()
    output_doc["model"] = model_name
    output_doc["counts"]["enriched"] = stats["enriched"]
    output_doc["counts"]["failed"] = stats["failed"]

    if not dry_run:
        _atomic_write_json(OUTPUT_PATH, output_doc)

    return {
        "processed": stats["processed"],
        "enriched": stats["enriched"],
        "failed": stats["failed"],
        "skipped_low_confidence": output_doc["counts"]["skipped_low_confidence"],
        "already_done": max(0, len(source_items) - len(work) - output_doc["counts"]["skipped_low_confidence"]),
    }

