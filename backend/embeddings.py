"""Local offline wrapper around the bundled MiniLM sentence-transformer.

Loads ``models/all-MiniLM-L6-v2/`` once per process, exposes ``embed`` for
batch encoding. The model produces 384-d cosine-friendly vectors, matching
the VectorAI DB collection definition in ``backend.vdb``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

from backend.config import get_settings


@lru_cache(maxsize=1)
def _model():  # type: ignore[no-untyped-def]
    """Lazily load SentenceTransformer; cached for the process lifetime."""
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    model_dir: Path = settings.model_dir
    if not model_dir.exists():
        raise FileNotFoundError(
            f"MiniLM model not found at {model_dir}. "
            "Run `python scripts/download_model.py` (or ./install.sh)."
        )
    return SentenceTransformer(str(model_dir))


def embed(texts: list[str]) -> np.ndarray:
    """Encode a batch of strings into L2-normalized 384-d float32 vectors.

    Cosine distance in VectorAI DB is monotonic with dot product on
    L2-normalized vectors, so we always normalize.
    """
    if not texts:
        return np.zeros((0, get_settings().vdb_vector_size), dtype=np.float32)

    model = _model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vectors.astype(np.float32, copy=False)


def embed_one(text: str) -> list[float]:
    """Convenience wrapper for query-time single-string embedding."""
    arr = embed([text])
    return arr[0].tolist()
