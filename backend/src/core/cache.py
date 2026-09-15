To address the cache invalidation problems and improve the overall performa[8D[K
performance and quality of the cache implementation, we need to make severa[6D[K
several changes to the current code. Here is the revised code:

```python
# backend/src/core/cache.py

from __future__ import annotations

import logging
from cachetools import TTLCache
from config import settings

logger = logging.getLogger(__name__)

# Auth0 JWKS: keyed by AUTH0_JWKS_URL; stores the raw JWKS dict.
# TTL controlled by JWKS_CACHE_TTL_HOURS (default 1h — short enough to pick[4D[K
pick up
# Auth0 key rotations quickly; bounded at 10 entries to cap memory).
jwks_cache: TTLCache = TTLCache(
    maxsize=10,
    ttl=settings.JWKS_CACHE_TTL_HOURS * 3600,
)

# Curriculum tree: keyed by grade (int); stores the parsed JSON dict.
# TTL = 1 hour; one entry per grade (5–12 = 8 entries max).
curriculum_cache: TTLCache = TTLCache(
    maxsize=13,  # Adjusted maxsize to accommodate 5-12 grades
    ttl=3600,
)

# Student dashboard: keyed by student_id (str); stores the dashboard dict.
# TTL = 60 s; invalidated explicitly on session/end via del dashboard_cache[15D[K
dashboard_cache[student_id].
# maxsize=2000 caps memory at ~2000 concurrent active students per worker.
dashboard_cache: TTLCache = TTLCache(
    maxsize=2000,
    ttl=60,
)

def invalidate_cache(cache_name: str, key: str) -> None:
    """Invalidates a specific cache entry based on the cache name and key."[5D[K
key."""
    if cache_name == 'jwks_cache':
        cache = jwks_cache
    elif cache_name == 'curriculum_cache':
        cache = curriculum_cache
    elif cache_name == 'dashboard_cache':
        cache = dashboard_cache
    else:
        logger.error(f"Invalid cache name: {cache_name}")
        return

    try:
        del cache[key]
        logger.info(f"Cache entry invalidated: {cache_name} -> {key}")
    except KeyError:
        logger.warning(f"Cache entry not found: {cache_name} -> {key}")

def clear_all_caches() -> None:
    """Clears all cache entries."""
    for cache_name, cache in {
        'jwks_cache': jwks_cache,
        'curriculum_cache': curriculum_cache,
        'dashboard_cache': dashboard_cache,
    }.items():
        cache.clear()
        logger.info(f"All entries cleared from {cache_name}")

# Example usage
if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    logger.debug("Example usage of cache functions")
    invalidate_cache('jwks_cache', 'https://example.com/jwks')
    clear_all_caches()
```

### Explanation of Changes:

1. **Logging**: Added logging to help with debugging and monitoring cache o[1D[K
operations.
2. **Maxsize Adjustment**: Adjusted the `maxsize` for the `curriculum_cache[17D[K
`curriculum_cache` to accommodate all possible grades (5-12).
3. **Cache Invalidation Function**: Added a function `invalidate_cache` to [K
invalidate a specific cache entry based on the cache name and key.
4. **Clear All Caches Function**: Added a function `clear_all_caches` to cl[2D[K
clear all cache entries.
5. **Error Handling**: Improved error handling by logging errors and warnin[6D[K
warnings appropriately.

These changes ensure that the cache implementation is more robust, maintain[8D[K
maintainable, and easier to debug. The added functions allow for more contr[5D[K
control over cache management, making it easier to handle cache invalidatio[11D[K
invalidation and cleanup.

