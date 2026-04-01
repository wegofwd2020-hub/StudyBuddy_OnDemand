"""
0022_private_teacher_subscription

Revision ID: 0022
Revises: 0021
Create Date: 2026-04-01

Multi-tier subscription model — private teacher tier.

New tables:
  private_teachers              — bcrypt-authenticated teacher accounts
  teacher_subscriptions         — Stripe subscription for a private teacher
  student_teacher_access        — per-student Stripe subscription linking
                                  a student to a private teacher's content

Alterations to existing tables:
  curricula.owner_type          — 'platform' | 'school' | 'teacher'
  curricula.owner_id            — UUID of the owning school or teacher
"""

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── private_teachers ─────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS private_teachers (
            teacher_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            email           TEXT        UNIQUE NOT NULL,
            name            TEXT        NOT NULL,
            password_hash   TEXT        NOT NULL,
            account_status  account_status NOT NULL DEFAULT 'active',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ── teacher_subscriptions ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS teacher_subscriptions (
            teacher_subscription_id  UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
            teacher_id               UUID  NOT NULL
                REFERENCES private_teachers(teacher_id) ON DELETE CASCADE,
            plan                     TEXT  NOT NULL
                CHECK (plan IN ('basic', 'pro')),
            status                   TEXT  NOT NULL
                CHECK (status IN ('trialing', 'active', 'past_due', 'cancelled')),
            stripe_customer_id       TEXT,
            stripe_subscription_id   TEXT  UNIQUE,
            pipeline_quota_monthly   INT   NOT NULL DEFAULT 2,
            pipeline_runs_this_month INT   NOT NULL DEFAULT 0,
            pipeline_resets_at       TIMESTAMPTZ NOT NULL
                DEFAULT date_trunc('month', NOW()) + INTERVAL '1 month',
            current_period_end       TIMESTAMPTZ,
            created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_teacher_subscriptions_teacher_id
            ON teacher_subscriptions (teacher_id)
    """)

    # ── student_teacher_access ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS student_teacher_access (
            access_id              UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id             UUID  NOT NULL
                REFERENCES students(student_id) ON DELETE CASCADE,
            teacher_id             UUID  NOT NULL
                REFERENCES private_teachers(teacher_id) ON DELETE CASCADE,
            status                 TEXT  NOT NULL
                CHECK (status IN ('active', 'cancelled', 'past_due')),
            stripe_customer_id     TEXT,
            stripe_subscription_id TEXT  UNIQUE,
            valid_until            TIMESTAMPTZ,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (student_id, teacher_id)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_student_teacher_access_student_id
            ON student_teacher_access (student_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_student_teacher_access_teacher_id
            ON student_teacher_access (teacher_id)
    """)

    # ── curricula — add owner_type / owner_id ─────────────────────────────────
    op.execute("""
        ALTER TABLE curricula
            ADD COLUMN IF NOT EXISTS owner_type TEXT NOT NULL DEFAULT 'platform'
                CHECK (owner_type IN ('platform', 'school', 'teacher')),
            ADD COLUMN IF NOT EXISTS owner_id UUID
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE curricula
            DROP COLUMN IF EXISTS owner_id,
            DROP COLUMN IF EXISTS owner_type
    """)
    op.execute("DROP INDEX IF EXISTS ix_student_teacher_access_teacher_id")
    op.execute("DROP INDEX IF EXISTS ix_student_teacher_access_student_id")
    op.execute("DROP TABLE IF EXISTS student_teacher_access")
    op.execute("DROP INDEX IF EXISTS ix_teacher_subscriptions_teacher_id")
    op.execute("DROP TABLE IF EXISTS teacher_subscriptions")
    op.execute("DROP TABLE IF EXISTS private_teachers")
