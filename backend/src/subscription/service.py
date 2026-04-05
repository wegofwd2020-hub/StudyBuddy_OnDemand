"""
backend/src/subscription/service.py

Stripe webhook deduplication helpers.

Individual student subscriptions were removed in migration 0027 (ADR-001).
All billing now flows through school_subscriptions — see
src/school/subscription_service.py.

student_entitlements is kept as the shared entitlement mechanism: written by
_bulk_update_enrolled_student_entitlements() when a school subscription
activates/renews/lapses; read by src/content/service.py to gate lesson access.
"""

from __future__ import annotations

import asyncpg

from src.utils.logger import get_logger

log = get_logger("subscription")


async def already_processed(conn: asyncpg.Connection, stripe_event_id: str) -> bool:
    """Return True if this stripe_event_id has already been handled."""
    row = await conn.fetchrow(
        "SELECT 1 FROM stripe_events WHERE stripe_event_id = $1 AND outcome = 'ok'",
        stripe_event_id,
    )
    return row is not None


async def log_stripe_event(
    conn: asyncpg.Connection,
    stripe_event_id: str,
    event_type: str,
    outcome: str,
    error_detail: str | None = None,
) -> None:
    """Insert a stripe_events row. ON CONFLICT DO NOTHING for idempotency."""
    await conn.execute(
        """
        INSERT INTO stripe_events (stripe_event_id, event_type, outcome, error_detail)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (stripe_event_id) DO NOTHING
        """,
        stripe_event_id,
        event_type,
        outcome,
        error_detail,
    )
