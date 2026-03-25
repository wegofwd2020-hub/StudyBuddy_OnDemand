"""phase5_subscriptions

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-25

Phase 5 schema: subscriptions + Stripe event log.

Tables created:
  subscriptions   — one active row per paying student; tracks plan, status, Stripe IDs
  stripe_events   — dedup + audit log for all Stripe webhook events
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── subscriptions ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            subscription_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id             UUID        NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            plan                   TEXT        NOT NULL CHECK (plan IN ('monthly', 'annual')),
            status                 TEXT        NOT NULL CHECK (status IN ('active', 'cancelled', 'past_due')),
            stripe_customer_id     TEXT        NOT NULL,
            stripe_subscription_id TEXT        NOT NULL UNIQUE,
            current_period_end     TIMESTAMPTZ,
            grace_period_end       TIMESTAMPTZ,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_student ON subscriptions(student_id)")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_student_active
            ON subscriptions(student_id)
            WHERE status = 'active'
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_sub ON subscriptions(stripe_subscription_id)")

    # ── stripe_events ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS stripe_events (
            stripe_event_id TEXT        PRIMARY KEY,
            event_type      TEXT        NOT NULL,
            processed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            outcome         TEXT        NOT NULL CHECK (outcome IN ('ok', 'error')),
            error_detail    TEXT
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS stripe_events")
    op.execute("DROP TABLE IF EXISTS subscriptions")
