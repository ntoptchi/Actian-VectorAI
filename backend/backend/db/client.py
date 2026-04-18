"""VectorAI client lifecycle.

A thin wrapper so the rest of the backend never imports ``actian_vectorai``
directly. That keeps mocking easy and isolates SDK upgrades.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from actian_vectorai import VectorAIClient

from ..config import get_settings


@contextmanager
def get_client() -> Iterator[VectorAIClient]:
    """Open a VectorAI client connected to the configured host."""
    settings = get_settings()
    with VectorAIClient(settings.vectorai_host) as client:
        yield client
