# Lessons

Running log of non-obvious mistakes and the patterns that prevent them. Review at session start.

## Actian VectorAI SDK

- **Named-vector searches use `using=`, not `vector_name=`.** The example file at
  `vectorai-db-beta/examples/29_named_vectors.py` is the source of truth. A silent-return
  bug (empty results, no exception) was the first symptom.
- **Sparse vectors pass through `vector=SparseVector(indices=…, values=…)` with `using=VEC_SPARSE`**,
  not as separate `sparse_indices=` / `values=` kwargs. See
  `examples/33_sparse_vectors.py` and `examples/15_hybrid_fusion.py`.
- **Sparse support must be probed with a round-trip upsert, not inferred from create-time
  config.** The dev server accepts `sparse_vectors_config` on `collections.create()` but
  then 422s on the first real sparse upsert with *"Unknown vector name"*. Pattern:
  `_probe_sparse_support()` in `backend/coaching_vdb.py` upserts+deletes a dummy point
  and caches the result. Fall back to dense-only when the probe fails.

## Pydantic schemas

- **`SituationDoc.source` is a `Literal` of `FARS | CISS | FDOT | NEWS`** — ad-hoc strings like
  `"QUERY"` will ValidationError. When building query docs, reuse one of the allowed values
  (`FDOT` is the safe default for synthetic queries).

## LLM-enriched payloads

- **Filter placeholder strings (`NOT_STATED`, `unknown`, `n/a`, `none`) before surfacing LLM
  fields as UI.** Do this at the retrieval boundary (`_clean_llm_field`) rather than the
  ingest layer so we don't have to re-ingest when we discover new placeholders.

## Windows / PowerShell

- Pipeline to `Select-Object -First N` / `-Last N`, not `head -N` / `tail -N`.
- The project venv is at `.venv\Scripts\python.exe`; a bare `python` falls back to system Python
  and will miss `pydantic_settings` and other deps.

## Process

- When a tool call returns empty/zero results silently, suspect an API shape mismatch before
  assuming "no matches". Verify against the SDK's own example files before writing more code.
