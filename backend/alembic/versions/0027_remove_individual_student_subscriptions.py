"""
0027_remove_individual_student_subscriptions

Revision ID: 0027
Revises: 0026
Create Date: 2026-04-05

Remove the individual student subscription tier per ADR-001 Decision 2.

All billing flows exclusively through school_subscriptions (migration 0019).
Students receive entitlements via their school's subscription, written to
student_entitlements by _bulk_update_enrolled_student_entitlements() in
src/school/subscription_service.py.

Tables dropped:
  subscriptions    — individual Stripe subscriptions per student

Tables kept:
  student_entitlements — entitlement cache written by school subscription webhooks;
                         read by content/service.py to gate lesson access.
                         This table is NOT student-billing-specific; it is the
                         shared entitlement mechanism for all subscription types.
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS subscriptions")


def downgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            subscription_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id              UUID        NOT NULL
                REFERENCES students(student_id) ON DELETE CASCADE,
            plan                    TEXT        NOT NULL
                CHECK (plan IN ('monthly', 'annual')),
            status                  TEXT        NOT NULL
                CHECK (status IN ('active', 'past_due', 'cancelled')),
            stripe_customer_id      TEXT,
            stripe_subscription_id  TEXT        UNIQUE,
            current_period_end      TIMESTAMPTZ,
            grace_period_end        TIMESTAMPTZ,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_subscriptions_student_id
            ON subscriptions (student_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_subscriptions_stripe_sub
            ON subscriptions (stripe_subscription_id)
    """)
