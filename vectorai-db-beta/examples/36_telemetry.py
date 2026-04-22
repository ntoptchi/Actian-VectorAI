############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Telemetry & Observability — structured logging, tracing, metrics, user-agent.

The ``actian_vectorai.telemetry`` sub-package provides four observability
utilities.  None of them require a running server — they operate at the
client/SDK layer.

  1. build_user_agent()
     ─────────────────
     Builds a RFC 9110-compliant User-Agent string that identifies the SDK,
     runtime, and transport versions.  Useful when attaching SDK identity to
     gRPC metadata headers or HTTP request headers.

  2. configure_structured_logging()   +   StructuredJsonFormatter
     ───────────────────────────────────────────────────────────────
     Attaches a JSON-line formatter to the ``actian_vectorai`` Python logger.
     Every log record emitted by the SDK (inside client.py, _points.py, etc.)
     is then written as a single-line JSON object — ready for ingestion by
     Datadog, Splunk, ELK, or any log aggregator.

     JSON fields emitted:
       ts          – ISO-8601 UTC timestamp
       level       – DEBUG / INFO / WARNING / ERROR
       logger      – dotted logger name (e.g. "actian_vectorai.client")
       msg         – human-readable message
       operation   – RPC method name          (when set via extra={})
       collection  – collection name          (when set via extra={})
       duration_ms – round-trip time in ms    (when set via extra={})
       request_id  – correlation ID           (when set via extra={})
       status      – Acknowledged / Completed (when set via extra={})
       transport   – "grpc" or "rest"         (when set via extra={})
       error       – exception message        (on exc_info=True)
       error_type  – exception class name     (on exc_info=True)

  3. trace_operation(operation, collection=None, **attrs)
     ──────────────────────────────────────────────────────
     A context manager that opens an OpenTelemetry span for the duration of
     a block.  If the ``opentelemetry-api`` / ``opentelemetry-sdk`` packages
     are not installed, every call silently becomes a no-op — zero overhead,
     no crash.

     Span attributes always set:
       db.system      = "actian_vectorai"
       db.operation   = <operation>
       db.collection  = <collection>  (when provided)
       <any **attrs>                  (e.g. limit=10, filter_count=2)

     The yielded span object supports:
       span.set_attribute(key, value)   – add/update an attribute mid-span
       span.record_exception(exc)       – attach an exception to the span
       span.set_status(status, msg)     – mark span success / error

  4. record_request(operation, duration_ms, success)
     ──────────────────────────────────────────────────
     Records three OpenTelemetry metrics instruments:
       actian.client.requests           – counter   (incremented per call)
       actian.client.request.duration_ms– histogram (millisecond latency)
       actian.client.errors             – counter   (incremented when success=False)

     Like trace_operation, all instruments are no-ops when OTel is absent.

Usage::

    python examples/36_telemetry.py
"""

from __future__ import annotations

import io
import json
import logging
import time

from actian_vectorai import Distance, PointStruct, VectorAIClient, VectorParams
from actian_vectorai.exceptions import CollectionNotFoundError, VectorAIError
from actian_vectorai.telemetry import (
    StructuredJsonFormatter,
    build_user_agent,
    configure_structured_logging,
    record_request,
    trace_operation,
)

SERVER = "localhost:50051"
COLLECTION = "telemetry_demo"
DIM = 8
fmt = "\n=== {:55} ==="


# ─── Part 1: build_user_agent ────────────────────────────────────────────────


def demo_build_user_agent() -> None:
    """build_user_agent() — RFC 9110 compliant SDK identity string.

    What it does
    ────────────
    Reads the installed SDK version, Python runtime, OS/architecture, and
    grpcio version, then assembles them into the format:

        ActianVectorAI-PythonSDK/<sdk_ver> (<OS> <arch>; Python <py_ver>) grpcio/<grpc_ver>

    When to use it
    ──────────────
    Pass this string as a gRPC metadata header or HTTP User-Agent so that
    server logs and APM dashboards can identify which SDK version made a
    request.  Useful in multi-client environments (Java SDK, REST client,
    Python SDK) to distinguish traffic sources.
    """
    print(fmt.format("build_user_agent()"))

    ua = build_user_agent()
    print(f"  User-Agent: {ua}")

    # Verify expected segments are present
    assert "ActianVectorAI-PythonSDK/" in ua, "missing SDK prefix"
    assert "Python" in ua, "missing Python version"
    assert "grpcio/" in ua, "missing grpcio version"
    print("  ✓ Contains SDK version, Python version, and grpcio version")

    # Practical usage — attach to gRPC metadata on every call
    print("\n  Practical usage (attach as gRPC metadata header):")
    print('    metadata = [("user-agent", build_user_agent())]')
    print('    VectorAIClient(SERVER, metadata=[("user-agent", build_user_agent())])')


# ─── Part 2: StructuredJsonFormatter (direct / manual use) ───────────────────


def demo_structured_json_formatter() -> None:
    """StructuredJsonFormatter — JSON-line log records.

    What it does
    ────────────
    A custom logging.Formatter subclass that serialises every LogRecord to a
    single JSON line.  It always includes ts, level, logger, and msg, and
    optionally promotes six extra fields when they are passed via the
    ``extra={}`` kwarg: operation, collection, duration_ms, request_id,
    status, and transport.  When exc_info=True is set, it also adds
    error and error_type fields.

    When to use it
    ──────────────
    Use directly when you already manage your own logger hierarchy and just
    want the Actian JSON format without calling configure_structured_logging().
    """
    print(fmt.format("StructuredJsonFormatter (direct)"))

    # Build a logger with the formatter attached to an in-memory buffer
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(StructuredJsonFormatter())

    demo_logger = logging.getLogger("demo.telemetry")
    demo_logger.addHandler(handler)
    demo_logger.setLevel(logging.DEBUG)
    demo_logger.propagate = False  # keep output inside our buffer

    # --- plain message ---
    demo_logger.info("SDK connected")
    line = buffer.getvalue().strip().split("\n")[-1]
    record = json.loads(line)
    print("\n  Plain INFO record:")
    print(f"    {json.dumps(record, indent=4)}")
    assert record["level"] == "INFO"
    assert record["msg"] == "SDK connected"
    assert "ts" in record and "logger" in record

    # --- message with structured extra fields ---
    demo_logger.info(
        "search completed",
        extra={
            "operation": "search",
            "collection": COLLECTION,
            "duration_ms": 4.7,
            "request_id": "req-abc-123",
            "status": "Completed",
            "transport": "grpc",
        },
    )
    line = buffer.getvalue().strip().split("\n")[-1]
    record = json.loads(line)
    print("\n  INFO with all extra fields:")
    print(f"    {json.dumps(record, indent=4)}")
    assert record["operation"] == "search"
    assert record["collection"] == COLLECTION
    assert record["duration_ms"] == 4.7
    assert record["transport"] == "grpc"

    # --- exception record ---
    try:
        raise ValueError("dimension mismatch: expected 128, got 64")
    except ValueError:
        demo_logger.error("vector insert failed", exc_info=True)

    line = buffer.getvalue().strip().split("\n")[-1]
    record = json.loads(line)
    print("\n  ERROR with exc_info:")
    print(f"    {json.dumps(record, indent=4)}")
    assert record["level"] == "ERROR"
    assert "error" in record
    assert record["error_type"] == "ValueError"

    # clean up
    demo_logger.removeHandler(handler)
    print("\n  ✓ All StructuredJsonFormatter fields verified")


# ─── Part 3: configure_structured_logging ────────────────────────────────────


def demo_configure_structured_logging() -> None:
    """configure_structured_logging() — attach JSON formatter to SDK logger.

    What it does
    ────────────
    Looks up the ``actian_vectorai`` logger (or whichever logger_name you
    pass), attaches a StreamHandler with StructuredJsonFormatter if no
    handlers are present yet, and sets the desired log level.  Returns the
    configured Logger so you can keep a reference.

    The SDK's internal loggers (actian_vectorai.client, actian_vectorai.vde,
    etc.) are all children of the ``actian_vectorai`` root logger, so every
    SDK log line automatically inherits this formatter.

    When to use it
    ──────────────
    Call once during application startup, before creating any client.  After
    that every SDK log record — connections, RPCs, retries, timeouts — will
    be emitted as JSON lines.
    """
    print(fmt.format("configure_structured_logging()"))

    # Capture SDK log output in a buffer for inspection
    buffer = io.StringIO()
    sdk_handler = logging.StreamHandler(buffer)
    sdk_handler.setFormatter(StructuredJsonFormatter())

    sdk_logger = configure_structured_logging(level=logging.DEBUG)
    # Replace its handler with our capturing handler (for demo only)
    sdk_logger.handlers.clear()
    sdk_logger.addHandler(sdk_handler)

    print("  Configured actian_vectorai logger with DEBUG level + JSON formatter")
    print(f"  Logger name  : {sdk_logger.name}")
    print(f"  Logger level : {logging.getLevelName(sdk_logger.level)}")
    print(f"  Handlers     : {sdk_logger.handlers}")

    # Emit a test record through the SDK logger hierarchy
    child = logging.getLogger("actian_vectorai.demo")
    child.info(
        "demo operation",
        extra={"operation": "upsert", "collection": COLLECTION, "duration_ms": 2.1},
    )
    line = buffer.getvalue().strip()
    if line:
        record = json.loads(line.split("\n")[-1])
        print("\n  Captured SDK child-logger output:")
        print(f"    {json.dumps(record, indent=4)}")
        assert record["operation"] == "upsert"

    # Restore a clean state for the live-client demo below
    sdk_logger.handlers.clear()
    print("\n  ✓ configure_structured_logging() verified")


# ─── Part 4: trace_operation ─────────────────────────────────────────────────


def demo_trace_operation() -> None:
    """trace_operation() — OpenTelemetry span context manager.

    What it does
    ────────────
    Opens an OTel span named ``actian.<operation>`` for the duration of the
    ``with`` block.  The span carries standard DB semantic convention
    attributes (db.system, db.operation, db.collection) plus any additional
    keyword arguments you pass.

    The yielded span object lets you:
      - span.set_attribute(key, value)   add/update span attributes at runtime
      - span.record_exception(exc)       attach a caught exception to the span
      - span.set_status(status, msg)     mark the span OK or ERROR

    No-op fallback
    ──────────────
    If opentelemetry-api is not installed, _get_tracer() returns _NoOpTracer
    and every span operation becomes a silent no-op.  The with-block executes
    normally; no ImportError is raised.  This means you can instrument your
    code unconditionally and activate OTel simply by installing the packages.

    When to use it
    ──────────────
    Wrap each logical SDK call with trace_operation() in your application
    layer when you want distributed traces that show VectorAI operations as
    spans inside a larger request trace (e.g., inside a FastAPI endpoint).
    """
    print(fmt.format("trace_operation()"))

    # --- basic span (OTel absent → no-op) ---
    print("\n  Basic span (db.system + db.operation + db.collection):")
    with trace_operation("search", collection=COLLECTION, limit=10) as span:
        print(f"    span type : {type(span).__name__}")
        # Simulate the work
        time.sleep(0.001)
        span.set_attribute("result_count", 5)
    print("    ✓ span exited cleanly (no-op when OTel absent)")

    # --- span with exception recording ---
    print("\n  Span with exception recording:")
    try:
        with trace_operation("upsert", collection=COLLECTION) as span:
            raise ValueError("simulated network error")
    except ValueError as exc:
        span.record_exception(exc)
        print(f"    ✓ exception attached to span: {exc}")

    # --- span without collection (server-level operation) ---
    print("\n  Span without collection (server-level operation):")
    with trace_operation("health_check") as span:
        span.set_attribute("server", SERVER)
    print("    ✓ health_check span completed")

    # --- multiple spans (realistic request flow) ---
    print("\n  Simulated request flow (prefetch → rerank → respond):")
    with trace_operation("query", collection=COLLECTION, stage="prefetch") as s1:
        s1.set_attribute("prefetch_limit", 100)
        time.sleep(0.001)
        with trace_operation("query", collection=COLLECTION, stage="rerank") as s2:
            s2.set_attribute("rerank_limit", 10)
            time.sleep(0.001)
    print("    ✓ nested spans completed")


# ─── Part 5: record_request ──────────────────────────────────────────────────


def demo_record_request() -> None:
    """record_request() — OTel metrics: counter + histogram + error counter.

    What it does
    ────────────
    On the first call, lazily initialises three OTel instruments on the
    ``actian_vectorai`` meter:

      actian.client.requests            Counter
        Incremented by 1 on every call, labelled with {"operation": <name>}.
        Use it to track total RPC volume per operation type.

      actian.client.request.duration_ms  Histogram
        Records the ``duration_ms`` value.  Export to a time-series backend
        (Prometheus, Datadog, etc.) to compute P50/P95/P99 latencies.

      actian.client.errors               Counter
        Incremented only when ``success=False``.  Use it to build error-rate
        dashboards or SLO burn alerts.

    No-op fallback
    ──────────────
    Same as trace_operation: if opentelemetry-sdk is absent, _get_meter()
    returns _NoOpMeter and all .add() / .record() calls are silent no-ops.

    When to use it
    ──────────────
    Call record_request() in your wrapper/middleware around each SDK
    operation so that your metrics backend receives latency and error
    telemetry without instrumenting every call site individually.
    """
    print(fmt.format("record_request()"))

    operations = [
        ("upsert", 12.4, True),
        ("search", 3.2, True),
        ("search", 8.7, True),
        ("query", 5.1, True),
        ("search", 99.9, False),  # simulated timeout / error
        ("delete", 1.8, True),
    ]

    print("\n  Recording synthetic request telemetry:")
    print(f"  {'operation':<12}  {'duration_ms':>12}  {'success':>8}")
    print(f"  {'-' * 12}  {'-' * 12}  {'-' * 8}")
    for operation, duration_ms, success in operations:
        record_request(operation, duration_ms, success)
        status_icon = "✓" if success else "✗"
        print(f"  {operation:<12}  {duration_ms:>11.1f}ms  {status_icon:>8}")

    print(
        "\n  Instruments created (or no-op if OTel absent):"
        "\n    actian.client.requests            — counter (6 total calls above)"
        "\n    actian.client.request.duration_ms — histogram (6 samples)"
        "\n    actian.client.errors              — counter (1 failure above)"
    )
    print("  ✓ record_request() verified")


# ─── Part 6: live integration — SDK + telemetry together ─────────────────────


def demo_live_integration() -> None:
    """Live integration — SDK operations wrapped with tracing + metrics.

    Shows how trace_operation and record_request compose with real
    client calls to produce per-RPC observability in a production app.
    """
    print(fmt.format("Live integration (SDK + telemetry)"))

    # Enable structured JSON logging for SDK internals
    buffer = io.StringIO()
    sdk_handler = logging.StreamHandler(buffer)
    sdk_handler.setFormatter(StructuredJsonFormatter())
    sdk_logger = configure_structured_logging(level=logging.DEBUG)
    sdk_logger.handlers.clear()
    sdk_logger.addHandler(sdk_handler)

    import random

    random.seed(99)

    with VectorAIClient(SERVER) as client:
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)

        # --- instrumented create ---
        t0 = time.perf_counter()
        with trace_operation("collections.create", collection=COLLECTION):
            client.collections.create(
                COLLECTION,
                vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
            )
        record_request("collections.create", (time.perf_counter() - t0) * 1000, True)
        print("  ✓ create  — traced + metric recorded")

        # --- instrumented upsert ---
        points = [
            PointStruct(
                id=i,
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={"label": f"item-{i}"},
            )
            for i in range(1, 21)
        ]
        t0 = time.perf_counter()
        with trace_operation(
            "points.upsert", collection=COLLECTION, batch_size=len(points)
        ) as span:
            client.points.upsert(COLLECTION, points)
            span.set_attribute("points_inserted", len(points))
        record_request("points.upsert", (time.perf_counter() - t0) * 1000, True)
        print(f"  ✓ upsert  — {len(points)} points, traced + metric recorded")

        # --- instrumented search ---
        query = [random.gauss(0, 1) for _ in range(DIM)]
        t0 = time.perf_counter()
        with trace_operation("points.search", collection=COLLECTION, limit=5) as span:
            results = client.points.search(COLLECTION, vector=query, limit=5)
            span.set_attribute("result_count", len(results))
        duration = (time.perf_counter() - t0) * 1000
        record_request("points.search", duration, True)
        print(f"  ✓ search  — {len(results)} results in {duration:.1f}ms, traced + metric recorded")

        # --- instrumented search that fails ---
        t0 = time.perf_counter()
        try:
            with trace_operation("points.search", collection="nonexistent_col") as span:
                client.points.search("nonexistent_col", vector=query, limit=3)
        except CollectionNotFoundError as exc:
            span.record_exception(exc)
            record_request("points.search", (time.perf_counter() - t0) * 1000, False)
            print("  ✓ failed search — exception attached to span, error metric recorded")
        except VectorAIError as exc:
            span.record_exception(exc)
            record_request("points.search", (time.perf_counter() - t0) * 1000, False)
            print("  ✓ failed search — exception attached to span, error metric recorded")

        # Cleanup
        client.collections.delete(COLLECTION)
        print("  ✓ cleanup")

    # Show a sample of the structured JSON the SDK emitted
    sdk_lines = [line for line in buffer.getvalue().strip().split("\n") if line]
    sdk_logger.handlers.clear()

    if sdk_lines:
        print(f"\n  SDK emitted {len(sdk_lines)} structured log line(s) — showing first:")
        try:
            sample = json.loads(sdk_lines[0])
            print(f"    {json.dumps(sample, indent=4)}")
        except json.JSONDecodeError:
            print(f"    {sdk_lines[0]}")
    else:
        print("\n  (No SDK debug log lines captured at this level)")


# ─── main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    demo_build_user_agent()
    demo_structured_json_formatter()
    demo_configure_structured_logging()
    demo_trace_operation()
    demo_record_request()
    demo_live_integration()
    print("\n✓ All telemetry demos complete")


if __name__ == "__main__":
    main()
