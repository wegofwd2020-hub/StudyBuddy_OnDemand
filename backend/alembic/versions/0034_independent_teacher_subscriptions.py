"""0034 — independent_teacher_subscriptions

Adds Stripe billing support for independent (non-school-affiliated) teachers.

An independent teacher signs up without a school invitation, pays a flat monthly
fee (Solo $29 · Growth $59 · Pro $99), and teaches up to 25 / 75 / 200 students.
The teacher keeps 100% of any student-side revenue they collect (Option A, #57).

Schema changes
──────────────
1. teacher_subscriptions
   Mirrors the school_subscriptions table but scoped to a single teacher.
   Fields: teacher_id (PK → teachers), plan, status, max_students,
           stripe_customer_id, stripe_subscription_id,
           current_period_end, grace_period_end, created_at, updated_at.

2. teachers.teacher_plan
   Denormalised fast-read column: 'solo' | 'growth' | 'pro' | NULL.
   NULL = school-affiliated (no independent plan).
   Kept in sync by the subscription webhook.

Revision ID: 0034
Revises: 0033
Create Date: 2026-04-10
"""

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend the demo-only NULL school_id guard to also allow independent teachers.
    # Old constraint: school_id IS NOT NULL OR auth_provider = 'demo'
    # New constraint: school_id IS NOT NULL OR auth_provider IN ('demo', 'auth0')
    #   where auth_provider='auth0' with school_id IS NULL = independent teacher.
    # The independent teacher path is distinguished from school-auth0-teachers by
    # school_id IS NULL; demo teachers continue to use auth_provider='demo'.
    op.execute(
        "ALTER TABLE teachers DROP CONSTRAINT IF EXISTS chk_teachers_school_id_or_demo"
    )
    op.execute(
        """
        ALTER TABLE teachers
            ADD CONSTRAINT chk_teachers_school_id_or_demo
                CHECK (school_id IS NOT NULL OR auth_provider IN ('demo', 'auth0'))
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS teacher_subscriptions (
            teacher_id          UUID        PRIMARY KEY
                                            REFERENCES teachers(teacher_id)
                                            ON DELETE CASCADE,
            plan                VARCHAR(20) NOT NULL
                                            CHECK (plan IN ('solo', 'growth', 'pro')),
            status              VARCHAR(20) NOT NULL DEFAULT 'active'
                                            CHECK (status IN ('active', 'past_due',
                                                              'cancelled', 'trialing')),
            max_students        INTEGER     NOT NULL DEFAULT 25,
            stripe_customer_id  VARCHAR(255),
            stripe_subscription_id VARCHAR(255),
            current_period_end  TIMESTAMPTZ,
            grace_period_end    TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_teacher_subscriptions_stripe_sub
            ON teacher_subscriptions (stripe_subscription_id)
            WHERE stripe_subscription_id IS NOT NULL
        """
    )
    # Denormalised plan column on teachers for fast JWT population.
    op.execute(
        """
        ALTER TABLE teachers
            ADD COLUMN IF NOT EXISTS teacher_plan VARCHAR(20)
                CHECK (teacher_plan IN ('solo', 'growth', 'pro'))
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE teachers DROP COLUMN IF EXISTS teacher_plan")
    op.execute("DROP TABLE IF EXISTS teacher_subscriptions")
    # Remove independent-teacher rows before reinstating the demo-only constraint.
    # SET LOCAL ensures the RLS bypass applies within this migration's transaction
    # even when running as a non-superuser (e.g. the studybuddy_rls_tester role in CI).
    op.execute("SELECT set_config('app.current_school_id', 'bypass', true)")
    op.execute(
        "DELETE FROM teachers WHERE auth_provider = 'auth0' AND school_id IS NULL"
    )
    op.execute(
        "ALTER TABLE teachers DROP CONSTRAINT IF EXISTS chk_teachers_school_id_or_demo"
    )
    op.execute(
        """
        ALTER TABLE teachers
            ADD CONSTRAINT chk_teachers_school_id_or_demo
                CHECK (school_id IS NOT NULL OR auth_provider = 'demo')
        """
    )
