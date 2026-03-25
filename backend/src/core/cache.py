"""
backend/src/core/cache.py

L1 in-process TTL caches (cachetools).

These are per-worker, in-memory caches — fast but not shared across workers.
For shared state use Redis (L2).

Cache instances:
  jwks_cache       — Auth0 JWKS keys  (24-hr TTL, size=10)
  curriculum_cache — Grade curriculum trees (1-hr TTL, size=100)
"""

from __future__ import annotations

from config import settings
from cachetools import TTLCache

# Auth0 JWKS: keyed by AUTH0_JWKS_URL; stores the raw JWKS dict.
# TTL = 24 hours; at most 10 distinct JWKS URLs (only one in practice).
jwks_cache: TTLCache = TTLCache(
    maxsize=10,
    ttl=settings.JWKS_CACHE_TTL_HOURS * 3600,
)

# Curriculum tree: keyed by grade (int); stores the parsed JSON dict.
# TTL = 1 hour; one entry per grade (5–12 = 8 entries max).
curriculum_cache: TTLCache = TTLCache(
    maxsize=20,
    ttl=3600,
)
