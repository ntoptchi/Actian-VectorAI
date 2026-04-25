"""OpenRouteService client — DEPRECATED.

Routing is now handled entirely by a self-hosted OSRM instance (see
routing.py). This module is kept as a no-op so any stale imports
fail loudly rather than silently degrading.
"""

raise ImportError(
    "ors_client is deprecated. Routing uses local OSRM — see routing.py."
)
