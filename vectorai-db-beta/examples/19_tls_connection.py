############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""TLS Connection — secure gRPC transport.

Demonstrates:
  - Plaintext connection (default)
  - TLS with server verification
  - TLS with custom CA certificate
  - Connection options and metadata

Usage::

    python examples/19_tls_connection.py
"""

from __future__ import annotations

from actian_vectorai import VectorAIClient

fmt = "\n=== {:50} ==="


def main() -> None:
    # ── Plaintext (default) ─────────────────────────────
    print(fmt.format("Plaintext connection"))
    client = VectorAIClient("localhost:50051")
    print(f"  Client: {client!r}")
    print(f"  Connected: {client.is_connected}")

    # ── TLS with default CA ─────────────────────────────
    print(fmt.format("TLS connection (system CA)"))
    client_tls = VectorAIClient(
        "vectorai.example.com:443",
        tls=True,
    )
    print(f"  Client: {client_tls!r}")
    # NOTE: connect() would fail without a real server
    # client_tls.connect()

    # ── TLS with custom CA ──────────────────────────────
    print(fmt.format("TLS with custom CA cert"))
    client_ca = VectorAIClient(
        "vectorai.example.com:443",
        tls=True,
        tls_ca_cert="/path/to/ca-certificate.pem",
    )
    print(f"  Client: {client_ca!r}")

    # ── Connection with options ─────────────────────────
    print(fmt.format("Connection with all options"))
    client_full = VectorAIClient(
        "vectorai.example.com:443",
        tls=True,
        tls_ca_cert="/path/to/ca.pem",
        api_key="my-secret-api-key",
        timeout=30.0,
        max_message_size=512 * 1024 * 1024,  # 512 MiB
        max_retries=5,
        enable_tracing=True,
        enable_logging=True,
        metadata=[("x-tenant-id", "acme"), ("x-app-version", "2.0")],
    )
    print(f"  Client: {client_full!r}")

    # ── Using context manager ───────────────────────────
    print(fmt.format("Context manager pattern"))
    print("  with VectorAIClient('localhost:50051') as client:")
    print("      client.collections.list()")
    print("  # auto-closes on exit")

    print("\n✓ Connection examples complete (no server needed)")


if __name__ == "__main__":
    main()
