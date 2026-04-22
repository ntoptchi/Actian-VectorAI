"""Local offline wrapper around the bundled MiniLM sentence-transformer.

Loads ``models/all-MiniLM-L6-v2/`` once per process, exposes ``embed`` for
batch encoding. The model produces 384-d cosine-friendly vectors, matching
the VectorAI DB collection definition in ``backend.vdb``.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

from backend.config import get_settings

logger = logging.getLogger(__name__)


def _resolve_device() -> str:
    """Pick the best torch device available at import time.

    Order: CUDA (NVIDIA) → MPS (Apple Silicon) → CPU. We don't try to
    auto-wire torch-directml for AMD-on-Windows because DirectML isn't
    always in the venv and silently failing transformer ops are worse
    than a predictable CPU run. If you want DirectML, set the env
    ``ROUTEWISE_EMBED_DEVICE=dml`` after ``pip install torch-directml``.
    """
    override = os.environ.get("ROUTEWISE_EMBED_DEVICE", "").strip().lower()
    if override:
        return override
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        mps = getattr(torch.backends, "mps", None)
        if mps is not None and mps.is_available():
            return "mps"
    except Exception:  # noqa: BLE001
        pass
    return "cpu"


def _batch_size() -> int:
    """Encoder batch size. Default 128 is a comfortable CPU sweet spot
    for MiniLM on 384-d output (roughly 1.5-2x the HF default of 32
    without running into L2 cache thrash). Override with the env
    ``ROUTEWISE_EMBED_BATCH_SIZE`` if you're on a GPU or a small box.
    """
    raw = os.environ.get("ROUTEWISE_EMBED_BATCH_SIZE")
    if raw:
        try:
            n = int(raw)
            if n > 0:
                return n
        except ValueError:
            pass
    return 128


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
    device = _resolve_device()
    logger.info("loading embedding model on device=%s (batch_size=%d)",
                device, _batch_size())
    return SentenceTransformer(str(model_dir), device=device)


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
        batch_size=_batch_size(),
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vectors.astype(np.float32, copy=False)


def embed_one(text: str) -> list[float]:
    """Convenience wrapper for query-time single-string embedding."""
    arr = embed([text])
    return arr[0].tolist()
