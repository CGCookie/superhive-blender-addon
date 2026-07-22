"""Curated catalog roots, fetched from the server and cached per session.

Every published catalog path's first segment must be one of these roots
(GET /api/v1/assets/taxonomy/roots). The fallback list mirrors the server's
AssetCatalog::ROOTS at the time of writing — used only when we've never
reached the server this session.
"""

from __future__ import annotations

import time

from .client import ApiError, SuperhiveClient

FALLBACK_ROOTS = (
    "Materials",
    "Models",
    "HDRIs",
    "Node Groups",
    "Brushes",
    "Poses & Animations",
    "Worlds",
)

_cache: dict = {"fetched_at": 0.0, "roots": None}


def get_cached_roots(
    client: SuperhiveClient | None = None, ttl: float = 86400.0
) -> list[str]:
    if _cache["roots"] is not None and time.monotonic() - _cache["fetched_at"] < ttl:
        return list(_cache["roots"])

    if client is not None:
        try:
            roots = client.get_taxonomy_roots()
        except ApiError:
            roots = None
        if roots:
            _cache["fetched_at"] = time.monotonic()
            _cache["roots"] = list(roots)
            return list(roots)

    if _cache["roots"] is not None:  # stale beats hardcoded
        return list(_cache["roots"])
    return list(FALLBACK_ROOTS)


def clear_cache() -> None:
    _cache["fetched_at"] = 0.0
    _cache["roots"] = None
