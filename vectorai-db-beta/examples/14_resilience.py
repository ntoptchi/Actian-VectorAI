############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Resilience — Circuit Breaker + Retry Configuration.

Demonstrates the resilience primitives that protect the client
from cascading failures:

  CircuitBreaker:
    - States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (probing)
    - record_success / record_failure / reset
    - Automatic OPEN when failure_threshold exceeded
    - Automatic HALF_OPEN after recovery_timeout

  RetryConfig:
    - Configurable max_retries, initial_delay, max_delay, backoff_factor
    - compute_delay(attempt) with exponential backoff

  BackpressureController:
    - Semaphore-based concurrency limiting
    - Dynamic adjustment via server signals

Usage::

    python examples/14_resilience.py
"""

from __future__ import annotations

import time

from actian_vectorai.resilience.backpressure import (
    BackpressureConfig,
    BackpressureController,
)
from actian_vectorai.resilience.circuit_breaker import CircuitBreaker, CircuitState
from actian_vectorai.resilience.retry import RetryConfig

fmt = "\n=== {:50} ==="


def demo_circuit_breaker() -> None:
    """Demonstrate CircuitBreaker state transitions."""
    print(fmt.format("CircuitBreaker"))

    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=2.0, success_threshold=1)
    print(f"  Initial state: {cb.state.name}")
    assert cb.state == CircuitState.CLOSED

    # Record some failures → trips to OPEN
    for i in range(3):
        cb.record_failure()
        print(f"  After failure {i + 1}: state={cb.state.name}, failures={cb.failure_count}")

    assert cb.state == CircuitState.OPEN
    print("  Circuit is OPEN — requests will be rejected")

    # ensure_closed() would raise CircuitBreakerOpenError here
    try:
        cb.ensure_closed()
    except Exception as e:
        print(f"  ensure_closed() raised: {type(e).__name__}")

    # Wait for recovery timeout → transitions to HALF_OPEN
    print(f"  Waiting {cb._recovery_timeout}s for recovery timeout...")
    time.sleep(2.1)
    print(f"  After timeout: state={cb.state.name}")
    assert cb.state == CircuitState.HALF_OPEN

    # A successful call in HALF_OPEN → back to CLOSED
    cb.record_success()
    print(f"  After success: state={cb.state.name}")
    assert cb.state == CircuitState.CLOSED

    # Reset manually
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()
    cb.reset()
    print(f"  After reset(): state={cb.state.name}, failures={cb.failure_count}")


def demo_retry_config() -> None:
    """Demonstrate RetryConfig exponential backoff."""
    print(fmt.format("RetryConfig"))

    config = RetryConfig(
        max_retries=5,
        initial_backoff_ms=100,
        max_backoff_ms=10000,
        backoff_multiplier=2.0,
        jitter_factor=0.25,
    )
    print(
        f"  Config: max_retries={config.max_retries}, "
        f"initial={config.initial_backoff_ms}ms, max={config.max_backoff_ms}ms, "
        f"multiplier={config.backoff_multiplier}, jitter={config.jitter_factor}"
    )

    for attempt in range(config.max_retries):
        delay = config.compute_delay(attempt)
        print(f"  Attempt {attempt}: delay = {delay:.3f}s")

    # Default config
    default = RetryConfig()
    print(
        f"\n  Default config: max_retries={default.max_retries}, "
        f"initial={default.initial_backoff_ms}ms"
    )


def demo_backpressure() -> None:
    """Demonstrate BackpressureController."""
    print(fmt.format("BackpressureController"))

    import asyncio

    config = BackpressureConfig(
        max_concurrent_requests=64,
        initial_concurrency=16,
        min_concurrency=1,
        max_concurrency=64,
    )
    controller = BackpressureController(config=config)
    print(f"  Initial limit: {controller.current_limit}")

    async def _demo() -> None:
        # Acquire / release semaphore
        await controller.acquire()
        print(f"  After acquire: limit={controller.current_limit}")

        controller.release()
        print(f"  After release: limit={controller.current_limit}")

        # Process server signals (simulate backpressure from server)
        await controller.process_server_signals({"rate_limit": 5})
        print(f"  After server signal (rate_limit=5): limit={controller.current_limit}")

    asyncio.run(_demo())


def main() -> None:
    demo_circuit_breaker()
    demo_retry_config()
    demo_backpressure()
    print("\n✓ All resilience demos complete")


if __name__ == "__main__":
    main()
