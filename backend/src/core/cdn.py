"""
backend/src/core/cdn.py

CloudFront CDN invalidation helpers.

Used after content purge or version bumps to ensure stale files are not
served from the CDN edge after the DB has been updated.

Design rules
────────────
- No-op when CLOUDFRONT_DISTRIBUTION_ID is not configured (local dev / LocalStorage).
- boto3 CloudFront calls are synchronous — dispatched to the default thread
  pool executor via asyncio.to_thread so the event loop is never blocked.
- boto3 is a lazy import; if it is not installed the function logs a warning
  and returns rather than crashing (S3/CloudFront is only used in production).
- Caller is responsible for deciding which paths to invalidate — this module
  only owns the mechanism, not the policy.

Invalidation path conventions
──────────────────────────────
  Per curriculum:    curricula/{curriculum_id}/*
  Per unit:          curricula/{curriculum_id}/{unit_id}/*
  Platform-wide:     /*  (use sparingly — counts as 1000 paths against quota)
"""

from __future__ import annotations

import asyncio
import time
from typing import Sequence

from src.utils.logger import get_logger

log = get_logger("cdn")


async def invalidate_paths(
    paths: Sequence[str],
    distribution_id: str | None,
    *,
    caller_reference: str | None = None,
) -> bool:
    """
    Submit a CloudFront invalidation batch for the given paths.

    Parameters
    ──────────
    paths               Iterable of CloudFront path patterns (must start with /).
                        E.g. ["/curricula/abc-123/*"].
    distribution_id     The CloudFront distribution ID.  If None or empty the
                        function is a no-op and returns False.
    caller_reference    Unique string for idempotency.  Defaults to a
                        microsecond timestamp if not supplied.

    Returns True on success, False when skipped (no distribution configured).
    Raises on boto3 / network errors so callers can decide how to handle them.
    """
    if not distribution_id:
        log.debug("cdn_invalidation_skipped no_distribution_id paths=%s", list(paths))
        return False

    if not paths:
        log.debug("cdn_invalidation_skipped empty_paths")
        return False

    ref = caller_reference or str(time.monotonic_ns())

    def _invalidate() -> dict:
        import boto3  # type: ignore  # lazy — not required in dev

        client = boto3.client("cloudfront")
        return client.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                "Paths": {
                    "Quantity": len(paths),
                    "Items": list(paths),
                },
                "CallerReference": ref,
            },
        )

    try:
        response = await asyncio.to_thread(_invalidate)
        invalidation_id = response.get("Invalidation", {}).get("Id", "unknown")
        log.info(
            "cdn_invalidation_submitted distribution=%s paths=%s invalidation_id=%s",
            distribution_id,
            list(paths),
            invalidation_id,
        )
        return True
    except ImportError:
        log.warning(
            "cdn_invalidation_skipped boto3_not_installed distribution=%s paths=%s",
            distribution_id,
            list(paths),
        )
        return False


async def invalidate_curriculum(
    curriculum_id: str,
    distribution_id: str | None,
) -> bool:
    """
    Invalidate all CloudFront cached files for a single curriculum.

    Issues a wildcard invalidation for /curricula/{curriculum_id}/* which
    covers all units, all languages, all content types, and all audio files.

    This is the correct call after:
      - Content purge (retention_status → 'purged')
      - Full curriculum rebuild / version bump
    """
    path = f"/curricula/{curriculum_id}/*"
    return await invalidate_paths([path], distribution_id, caller_reference=f"purge-{curriculum_id}")


async def invalidate_unit(
    curriculum_id: str,
    unit_id: str,
    distribution_id: str | None,
) -> bool:
    """
    Invalidate CloudFront cache for a single unit within a curriculum.

    Use after a targeted unit rebuild rather than a full curriculum bump,
    to avoid unnecessary invalidation quota consumption.
    """
    path = f"/curricula/{curriculum_id}/{unit_id}/*"
    return await invalidate_paths(
        [path],
        distribution_id,
        caller_reference=f"unit-{curriculum_id}-{unit_id}",
    )
