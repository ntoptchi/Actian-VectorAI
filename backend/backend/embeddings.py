"""Embedding wrapper.

Wraps sentence-transformers behind a tiny stable interface so the rest of the
pipeline never imports the heavy dependency directly. A deterministic mock is
provided for offline / unit-test mode (set ``USE_MOCK_EMBEDDINGS=true``).
"""

from __future__ import annotations

import hashlib
import math
from functools import lru_cache
from typing import Iterable, Protocol

import numpy as np

from .config import get_settings


class Embedder(Protocol):
    """Anything that turns strings into unit-length float vectors."""

    dim: int

    def encode(self, texts: list[str]) -> list[list[float]]: ...

    def encode_one(self, text: str) -> list[float]: ...


class _MiniLMEmbedder:
    """Lazy wrapper around a sentence-transformers model."""

    def __init__(self, model_name: str, dim: int) -> None:
        from sentence_transformers import SentenceTransformer  # noqa: WPS433

        self._model = SentenceTransformer(model_name)
        self.dim = dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        arr = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vec.tolist() for vec in np.asarray(arr, dtype=np.float32)]

    def encode_one(self, text: str) -> list[float]:
        return self.encode([text])[0]


class _MockEmbedder:
    """Deterministic hash-based embedder for offline use.

    Produces unit-length vectors so cosine search behaves sanely. Quality is
    miles below MiniLM, but the pipeline shape is identical which is all we
    need for the scaffold.
    """

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.encode_one(t) for t in texts]

    def encode_one(self, text: str) -> list[float]:
        seed = int.from_bytes(
            hashlib.sha256(text.encode("utf-8")).digest()[:8],
            "big",
            signed=False,
        )
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self.dim).astype(np.float32)
        norm = float(np.linalg.norm(vec))
        if norm == 0.0 or math.isnan(norm):
            vec = np.ones(self.dim, dtype=np.float32) / math.sqrt(self.dim)
        else:
            vec = vec / norm
        return vec.tolist()


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """Return the process-wide embedder, honouring settings."""
    settings = get_settings()
    if settings.use_mock_embeddings:
        return _MockEmbedder(dim=settings.embedding_dim)
    return _MiniLMEmbedder(
        model_name=settings.embedding_model,
        dim=settings.embedding_dim,
    )


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    """Convenience: encode an iterable of strings."""
    return get_embedder().encode(list(texts))


def embed(text: str) -> list[float]:
    """Convenience: encode a single string."""
    return get_embedder().encode_one(text)
