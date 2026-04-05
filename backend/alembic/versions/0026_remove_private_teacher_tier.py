"""
0026_remove_private_teacher_tier

Revision ID: 0026
Revises: 0025
Create Date: 2026-04-05

Remove the private teacher subscription tier per ADR-001 Decision 1 + 2.

All users — including independent tutors and home schoolers — register as a
School/Institution.  There is no standalone private teacher entity.  Billing
flows exclusively through school_subscriptions (migration 0019).

Tables dropped:
  student_teacher_access   — students subscribing directly to a private teacher
  teacher_subscriptions    — Stripe billing for private teachers
  private_teachers         — bcrypt-auth teacher accounts with no school_id

curricula.owner_type:
  Remove 'teacher' from the CHECK constraint.
  Valid values after this migration: 'platform' | 'school' only.
  Any stale rows with owner_type='teacher' are reassigned to 'platform'.
"""

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Nullify any curricula that pointed at the private teacher tier ──────────
    # In practice there should be none in a clean environment, but this makes the
    # migration safe to run against any state.
    op.execute("""
        UPDATE curricula
        SET owner_type = 'platform',
            owner_id   = NULL
        WHERE owner_type = 'teacher'
    """)

    # ── Drop dependent tables (order respects FK constraints) ──────────────────
    op.execute("DROP TABLE IF EXISTS student_teacher_access")
    op.execute("DROP TABLE IF EXISTS teacher_subscriptions")
    op.execute("DROP TABLE IF EXISTS private_teachers")

    # ── Tighten curricula.owner_type CHECK ─────────────────────────────────────
    # PostgreSQL auto-names inline column CHECK constraints as
    # {table}_{column}_check.  Drop the old one and replace it.
    op.execute("""
        ALTER TABLE curricula
            DROP CONSTRAINT IF EXISTS curricula_owner_type_check
    """)
    op.execute("""
        ALTER TABLE curricula
            ADD CONSTRAINT curricula_owner_type_check
            CHECK (owner_type IN ('platform', 'school'))
    """)


def downgrade() -> None:
    # Restore the wider CHECK constraint first so the inserts below succeed.
    op.execute("ALTER TABLE curricula DROP CONSTRAINT IF EXISTS curricula_owner_type_check")
    op.execute("""
        ALTER TABLE curricula
            ADD CONSTRAINT curricula_owner_type_check
            CHECK (owner_type IN ('platform', 'school', 'teacher'))
    """)

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
