############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Exception Handling — full error hierarchy + utilities.

Extends 18_error_handling.py with complete coverage of the
exception hierarchy and error-handling utilities:

  Exception tree:
    VectorAIError
    ├── ConnectionError → ConnectionRefusedError, ConnectionTimeoutError,
    │                      ChannelClosedError
    ├── AuthenticationError → InvalidCredentialsError, PermissionDeniedError
    ├── CollectionError → CollectionNotFoundError, CollectionExistsError,
    │                      CollectionNotReadyError
    ├── PointError → PointNotFoundError, DimensionMismatchError
    ├── ValidationError
    ├── IndexError
    ├── ServerError → UnimplementedError
    ├── TimeoutError
    ├── RateLimitError
    ├── BatchError
    ├── CircuitBreakerOpenError
    ├── MaxRetriesExceededError
    ├── ClientClosedError
    ├── PayloadError → PayloadKeyNotFoundError

  Utilities:
    from_grpc_error()   — convert gRPC errors to typed exceptions
    from_http_error()   — convert HTTP errors to typed exceptions
    is_retryable()      — check if an error is retryable
    get_retry_delay()   — compute retry delay with backoff

Usage::

    python examples/27_exception_handling.py
"""

from __future__ import annotations

from actian_vectorai.exceptions import (
    BatchError,
    CircuitBreakerOpenError,
    ClientClosedError,
    CollectionExistsError,
    CollectionNotFoundError,
    CollectionNotReadyError,
    ConnectionRefusedError,
    ConnectionTimeoutError,
    DimensionMismatchError,
    InvalidCredentialsError,
    MaxRetriesExceededError,
    PayloadKeyNotFoundError,
    PermissionDeniedError,
    PointNotFoundError,
    RateLimitError,
    TimeoutError,
    UnimplementedError,
    ValidationError,
    VectorAIError,
    from_grpc_error,
    from_http_error,
    get_retry_delay,
    is_retryable,
)

fmt = "\n=== {:50} ==="


def demo_exception_hierarchy() -> None:
    """Show the exception class hierarchy."""
    print(fmt.format("Exception Hierarchy"))

    # All exceptions inherit from VectorAIError
    errors = [
        ConnectionRefusedError("localhost:50051"),
        ConnectionTimeoutError("localhost:50051", timeout=30.0),
        InvalidCredentialsError(),
        PermissionDeniedError(operation="delete"),
        CollectionNotFoundError("missing_collection"),
        CollectionExistsError("existing_collection"),
        CollectionNotReadyError("loading_collection", reason="index building"),
        PointNotFoundError(ids=[1, 2], collection="test"),
        DimensionMismatchError(expected=128, actual=256),
        ValidationError("invalid field", field="name"),
        UnimplementedError(operation="scroll"),
        TimeoutError(operation="search", timeout=5.0),
        RateLimitError(retry_after=2.5),
        BatchError(total=100, failed=5, errors=[]),
        CircuitBreakerOpenError(recovery_time=30.0, failure_count=10),
        MaxRetriesExceededError(attempts=5, last_error=None),
        ClientClosedError(),
        PayloadKeyNotFoundError(key="missing_key", collection="test"),
    ]

    for err in errors:
        class_name = type(err).__name__
        parent = type(err).__bases__[0].__name__
        print(f"  {class_name:35s} (parent: {parent})")
        assert isinstance(err, VectorAIError), f"{class_name} must be VectorAIError"


def demo_error_attributes() -> None:
    """Show error attributes used for programmatic handling."""
    print(fmt.format("Error Attributes"))

    # VectorAIError has: message, code, details, operation
    err = CollectionNotFoundError("my_collection")
    print("  CollectionNotFoundError:")
    print(f"    message = {err.message!r}")
    print(f"    code    = {err.code!r}")

    # ConnectionError has: address
    err2 = ConnectionRefusedError("localhost:50051")
    print("  ConnectionRefusedError:")
    print(f"    address = {err2.address!r}")

    # RateLimitError has: retry_after
    err3 = RateLimitError(retry_after=2.5)
    print("  RateLimitError:")
    print(f"    retry_after = {err3.retry_after}")

    # BatchError has: total, failed, errors
    err4 = BatchError(total=100, failed=5, errors=["err1", "err2"])
    print("  BatchError:")
    print(f"    total={err4.total}, failed={err4.failed}, errors={len(err4.errors)}")

    # CircuitBreakerOpenError
    err5 = CircuitBreakerOpenError(recovery_time=30.0, failure_count=10)
    print("  CircuitBreakerOpenError:")
    print(f"    recovery_time={err5.recovery_time}, failure_count={err5.failure_count}")


def demo_retryable() -> None:
    """Demonstrate is_retryable() and get_retry_delay()."""
    print(fmt.format("is_retryable() + get_retry_delay()"))

    retryable_errors = [
        ConnectionTimeoutError("localhost", timeout=5.0),
        RateLimitError(retry_after=1.0),
        TimeoutError(operation="search", timeout=5.0),
    ]

    non_retryable_errors = [
        CollectionNotFoundError("missing"),
        ValidationError("bad input"),
        UnimplementedError(operation="scroll"),
    ]

    for err in retryable_errors:
        retry = is_retryable(err)
        delay = get_retry_delay(err)
        print(f"  {type(err).__name__:35s} retryable={retry}  delay={delay:.2f}s")

    for err in non_retryable_errors:
        retry = is_retryable(err)
        print(f"  {type(err).__name__:35s} retryable={retry}")


def demo_from_grpc_error() -> None:
    """Demonstrate from_grpc_error() conversion."""
    print(fmt.format("from_grpc_error()"))

    # Simulate a gRPC error object
    class FakeGrpcError:
        def code(self):
            return type("Code", (), {"value": (14, "UNAVAILABLE")})()

        def details(self):
            return "Connection refused"

    try:
        result = from_grpc_error(FakeGrpcError(), operation="search")
        print(f"  Converted to: {type(result).__name__}")
    except Exception as e:
        print(f"  from_grpc_error: {type(e).__name__}: {e}")
        print("  (Expected — fake gRPC error may not match expected format)")


def demo_from_http_error() -> None:
    """Demonstrate from_http_error() conversion."""
    print(fmt.format("from_http_error()"))

    # 404 → CollectionNotFoundError
    err = from_http_error(404, body={"error": "not found"}, operation="get_collection")
    print(f"  HTTP 404 → {type(err).__name__}: {err.message}")

    # 401 → AuthenticationError
    err = from_http_error(401, body="unauthorized", operation="list")
    print(f"  HTTP 401 → {type(err).__name__}: {err.message}")

    # 429 → RateLimitError
    err = from_http_error(429, headers={"retry-after": "5"}, operation="search")
    print(f"  HTTP 429 → {type(err).__name__}: {err.message}")

    # 500 → ServerError
    err = from_http_error(500, body="internal error", operation="upsert")
    print(f"  HTTP 500 → {type(err).__name__}: {err.message}")

    # 503 → ConnectionError (service unavailable)
    err = from_http_error(503, body="service unavailable", operation="health")
    print(f"  HTTP 503 → {type(err).__name__}: {err.message}")


def demo_catch_patterns() -> None:
    """Common exception catching patterns."""
    print(fmt.format("Common Catch Patterns"))

    print("""
  # Catch any VectorAI error
  try:
      client.points.search(...)
  except VectorAIError as e:
      print(f"Error: {e.message}")

  # Catch connection issues specifically
  try:
      client.connect()
  except ConnectionError as e:
      print(f"Cannot connect to {e.address}")

  # Catch retryable errors with backoff
  try:
      results = client.points.search(...)
  except VectorAIError as e:
      if is_retryable(e):
          delay = get_retry_delay(e)
          time.sleep(delay)
          # retry...

  # Circuit breaker pattern
  try:
      results = client.points.search(...)
  except CircuitBreakerOpenError as e:
      print(f"Circuit open, retry in {e.recovery_time}s")
""")


def main() -> None:
    demo_exception_hierarchy()
    demo_error_attributes()
    demo_retryable()
    demo_from_grpc_error()
    demo_from_http_error()
    demo_catch_patterns()
    print("\n✓ All exception handling demos complete")


if __name__ == "__main__":
    main()
