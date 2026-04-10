"""0035 — teacher_connect_accounts

Stripe Connect (Express) support for independent teacher revenue-share billing
(Option B, GitHub #104).

Under this model the teacher earns a configurable percentage of each student's
monthly subscription payment.  The platform keeps the remainder as an
application fee.  No flat monthly fee is charged to the teacher.

Schema changes
──────────────
1. teachers.billing_model
   Denormalised fast-read column distinguishing Option-A (flat_fee) teachers
   from Option-B (revenue_share) teachers.  NULL = school-affiliated or
   unsubscribed independent teacher.

2. teacher_connect_accounts
   Stores the Stripe Connect Express account ID and onboarding/capability
   state per teacher.  One row per teacher (1-1 with teachers).

3. student_connect_subscriptions
   Tracks the Stripe Subscription created for each student who pays an
   Option-B teacher directly via the platform.  The subscription is created
   on the platform account with application_fee_percent and
   transfer_data.destination set to the teacher's Connect account so Stripe
   handles the split automatically.

Revision ID: 0035
Revises: 0034
Create Date: 2026-04-10
"""

from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. teachers.billing_model
    op.execute(
        """
        ALTER TABLE teachers
            ADD COLUMN IF NOT EXISTS billing_model VARCHAR(20)
                CHECK (billing_model IN ('flat_fee', 'revenue_share'))
        """
    )

    # 2. teacher_connect_accounts
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS teacher_connect_accounts (
            teacher_id          UUID        PRIMARY KEY
                                            REFERENCES teachers(teacher_id)
                                            ON DELETE CASCADE,
            stripe_account_id   VARCHAR(255) NOT NULL UNIQUE,
            -- onboarding_complete: True once the teacher finishes the Stripe
            -- Express onboarding flow and capabilities are enabled.
            onboarding_complete BOOLEAN     NOT NULL DEFAULT FALSE,
            charges_enabled     BOOLEAN     NOT NULL DEFAULT FALSE,
            payouts_enabled     BOOLEAN     NOT NULL DEFAULT FALSE,
            -- Timestamp of the last sync from Stripe account.updated webhook.
            last_synced_at      TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_teacher_connect_stripe_account
            ON teacher_connect_accounts (stripe_account_id)
        """
    )

    # 3. student_connect_subscriptions
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS student_connect_subscriptions (
            subscription_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id              UUID        NOT NULL
                                                REFERENCES students(student_id)
                                                ON DELETE CASCADE,
            teacher_id              UUID        NOT NULL
                                                REFERENCES teachers(teacher_id)
                                                ON DELETE CASCADE,
            stripe_customer_id      VARCHAR(255),
            stripe_subscription_id  VARCHAR(255) UNIQUE,
            status                  VARCHAR(20) NOT NULL DEFAULT 'active'
                                                CHECK (status IN ('active', 'past_due',
                                                                  'cancelled', 'trialing')),
            current_period_end      TIMESTAMPTZ,
            grace_period_end        TIMESTAMPTZ,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (student_id, teacher_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_scs_teacher_id
            ON student_connect_subscriptions (teacher_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_scs_stripe_sub
            ON student_connect_subscriptions (stripe_subscription_id)
            WHERE stripe_subscription_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS student_connect_subscriptions")
    op.execute("DROP TABLE IF EXISTS teacher_connect_accounts")
    op.execute("ALTER TABLE teachers DROP COLUMN IF EXISTS billing_model")
