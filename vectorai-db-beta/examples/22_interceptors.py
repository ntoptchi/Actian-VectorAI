############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Interceptor Stack — all gRPC interceptor types.

The interceptor chain wraps every gRPC call with cross-cutting
concerns.  This example shows how to configure each interceptor:

  AuthInterceptor          — inject API key / bearer token
  RetryInterceptor         — automatic retry with backoff
  TracingInterceptor       — request / response timing
  LoggingInterceptor       — structured request logging
  MetadataInterceptor      — inject custom gRPC metadata
  UserAgentInterceptor     — set User-Agent header
  CircuitBreakerInterceptor — circuit-breaker protection

Usage::

    python examples/22_interceptors.py
"""

from __future__ import annotations

from actian_vectorai.resilience.circuit_breaker import CircuitBreaker
from actian_vectorai.transport.interceptors import (
    AuthInterceptor,
    CircuitBreakerInterceptor,
    LoggingInterceptor,
    MetadataInterceptor,
    RetryInterceptor,
    TracingInterceptor,
    UserAgentInterceptor,
)

fmt = "\n=== {:50} ==="


def main() -> None:
    # ── AuthInterceptor ─────────────────────────────────
    print(fmt.format("AuthInterceptor"))
    auth = AuthInterceptor(api_key="my-secret-key")
    print(f"  Created: {auth}")
    print("  Injects 'authorization: Bearer my-secret-key' into gRPC metadata")

    # ── RetryInterceptor ────────────────────────────────
    print(fmt.format("RetryInterceptor"))
    retry = RetryInterceptor(
        max_retries=5,
        initial_backoff_ms=100,
        max_backoff_ms=10000,
        backoff_multiplier=2.0,
    )
    print(f"  Created: {retry}")
    print("  Retries UNAVAILABLE/ABORTED/RESOURCE_EXHAUSTED up to 5 times")

    # ── TracingInterceptor ──────────────────────────────
    print(fmt.format("TracingInterceptor"))
    tracing = TracingInterceptor()
    print(f"  Created: {tracing}")
    print("  Logs timing for each gRPC call")

    # ── LoggingInterceptor ──────────────────────────────
    print(fmt.format("LoggingInterceptor"))
    logging_int = LoggingInterceptor()
    print(f"  Created: {logging_int}")
    print("  Logs request/response details at DEBUG level")

    # ── MetadataInterceptor ─────────────────────────────
    print(fmt.format("MetadataInterceptor"))
    metadata = MetadataInterceptor(metadata=[("x-request-id", "abc-123"), ("x-tenant", "acme")])
    print(f"  Created: {metadata}")
    print("  Injects custom key-value pairs into every gRPC call")

    # ── UserAgentInterceptor ────────────────────────────
    print(fmt.format("UserAgentInterceptor"))
    ua = UserAgentInterceptor()
    print(f"  Created: {ua}")
    print("  Sets User-Agent: actian-vectorai-python/<version>")

    # ── CircuitBreakerInterceptor ───────────────────────
    print(fmt.format("CircuitBreakerInterceptor"))
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
    cb_int = CircuitBreakerInterceptor(breaker=cb)
    print(f"  Created: {cb_int}")
    print(f"  Trips after {cb._failure_threshold} failures, recovers in {cb._recovery_timeout}s")

    # ── Using interceptors with the client ──────────────
    print(fmt.format("Using interceptors with AsyncVectorAIClient"))
    print("""
  Interceptors are automatically configured based on client parameters:

    from actian_vectorai import AsyncVectorAIClient

    client = AsyncVectorAIClient(
        "localhost:50051",
        api_key="my-key",      # → AuthInterceptor
        max_retries=5,         # → RetryInterceptor
        enable_tracing=True,   # → TracingInterceptor
        enable_logging=True,   # → LoggingInterceptor
        metadata={"x-tenant": "acme"},  # → MetadataInterceptor
    )

  The interceptor chain runs in order:
    UserAgent → Auth → Metadata → CircuitBreaker → Retry → Tracing → Logging
""")

    print("✓ All interceptor demos complete")


if __name__ == "__main__":
    main()
