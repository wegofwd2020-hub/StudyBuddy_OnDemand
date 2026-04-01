"""
0019_school_subscriptions

Revision ID: 0019
Revises: 0018
Create Date: 2026-04-01

Adds school_subscriptions table for per-school billing.

Design:
  - One row per school (UNIQUE school_id).
  - plan: starter | professional | enterprise
  - status: trialing | active | past_due | cancelled
  - max_students / max_teachers: seat limits stamped at subscription time;
    updated by webhook on plan change or override.
  - stripe_customer_id / stripe_subscription_id: Stripe identifiers.
  - current_period_end / grace_period_end: access validity windows.

Individual student subscriptions (subscriptions table) are unchanged —
non-school students continue to use the existing path.
"""

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS school_subscriptions (
            school_subscription_id  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
            school_id               uuid        NOT NULL UNIQUE
                                                REFERENCES schools(school_id) ON DELETE CASCADE,
            plan                    text        NOT NULL
                                                CHECK (plan IN ('starter', 'professional', 'enterprise')),
            status                  text        NOT NULL
                                                CHECK (status IN ('trialing', 'active', 'past_due', 'cancelled')),
            stripe_customer_id      text        NOT NULL,
            stripe_subscription_id  text        NOT NULL UNIQUE,
            max_students            int         NOT NULL DEFAULT 30,
            max_teachers            int         NOT NULL DEFAULT 5,
            current_period_end      timestamptz,
            grace_period_end        timestamptz,
            created_at              timestamptz NOT NULL DEFAULT NOW(),
            updated_at              timestamptz NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_school_subscriptions_stripe
            ON school_subscriptions(stripe_subscription_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_school_subscriptions_status
            ON school_subscriptions(status)
            WHERE status IN ('active', 'trialing', 'past_due')
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_school_subscriptions_status")
    op.execute("DROP INDEX IF EXISTS ix_school_subscriptions_stripe")
    op.execute("DROP TABLE IF EXISTS school_subscriptions")
