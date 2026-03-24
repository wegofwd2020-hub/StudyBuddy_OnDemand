"""phase1_initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-03-24

Phase 1 schema: all tables and types required for auth, account management,
curriculum serving, and the audit trail.

Tables (created in FK dependency order):
  schools           — stub for Phase 1 curriculum resolver
  students          — Auth0 external auth users (grades 5–12)
  teachers          — Auth0 external auth users (school-scoped)
  admin_users       — internal product team (local bcrypt)
  parental_consents — COPPA compliance (under-13 students)
  audit_log         — immutable event trail

ENUM types:
  account_status  — pending | active | suspended | deleted
  admin_role      — developer | tester | product_admin | super_admin
  consent_status  — pending | granted | denied
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ENUM types ────────────────────────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE account_status AS ENUM ('pending', 'active', 'suspended', 'deleted');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE admin_role AS ENUM ('developer', 'tester', 'product_admin', 'super_admin');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE consent_status AS ENUM ('pending', 'granted', 'denied');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    # ── schools (must exist before students FK) ────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS schools (
            school_id      uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
            name           text          NOT NULL,
            contact_email  text          NOT NULL,
            country        text          NOT NULL DEFAULT 'CA',
            enrolment_code text          UNIQUE,
            status         account_status NOT NULL DEFAULT 'active',
            created_at     timestamptz   NOT NULL DEFAULT NOW()
        )
    """)

    # ── students ───────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id       uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
            external_auth_id text          UNIQUE NOT NULL,
            auth_provider    text          NOT NULL DEFAULT 'auth0',
            name             text          NOT NULL,
            email            text          UNIQUE NOT NULL,
            grade            smallint      NOT NULL CHECK (grade BETWEEN 5 AND 12),
            locale           text          NOT NULL DEFAULT 'en',
            account_status   account_status NOT NULL DEFAULT 'pending',
            school_id        uuid          REFERENCES schools(school_id) ON DELETE SET NULL,
            enrolled_at      timestamptz,
            lessons_accessed int           NOT NULL DEFAULT 0,
            created_at       timestamptz   NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_students_external_auth_id ON students(external_auth_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_students_school_id        ON students(school_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_students_account_status   ON students(account_status)")

    # ── teachers ───────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            teacher_id       uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
            school_id        uuid          NOT NULL REFERENCES schools(school_id),
            external_auth_id text          UNIQUE NOT NULL,
            auth_provider    text          NOT NULL DEFAULT 'auth0',
            name             text          NOT NULL,
            email            text          UNIQUE NOT NULL,
            role             text          NOT NULL DEFAULT 'teacher',
            account_status   account_status NOT NULL DEFAULT 'pending',
            created_at       timestamptz   NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_teachers_school_id ON teachers(school_id)")

    # ── admin_users ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            admin_user_id  uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
            email          text          UNIQUE NOT NULL,
            password_hash  text          NOT NULL,
            role           admin_role    NOT NULL DEFAULT 'developer',
            account_status account_status NOT NULL DEFAULT 'active',
            totp_secret    text,
            last_login_at  timestamptz,
            created_at     timestamptz   NOT NULL DEFAULT NOW()
        )
    """)

    # ── parental_consents ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS parental_consents (
            consent_id       uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id       uuid          NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            guardian_email   text          NOT NULL,
            status           consent_status NOT NULL DEFAULT 'pending',
            consent_token    text          UNIQUE,
            token_expires_at timestamptz,
            consented_at     timestamptz,
            ip_address       inet,
            created_at       timestamptz   NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_parental_consents_student_id ON parental_consents(student_id)")

    # ── audit_log ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id             bigserial     PRIMARY KEY,
            timestamp      timestamptz   NOT NULL DEFAULT NOW(),
            event_type     text          NOT NULL,
            actor_type     text          NOT NULL,
            actor_id       uuid,
            target_type    text,
            target_id      uuid,
            metadata       jsonb,
            ip_address     inet,
            correlation_id text
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log(timestamp DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_target    ON audit_log(target_type, target_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_actor     ON audit_log(actor_type, actor_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE")
    op.execute("DROP TABLE IF EXISTS parental_consents CASCADE")
    op.execute("DROP TABLE IF EXISTS admin_users CASCADE")
    op.execute("DROP TABLE IF EXISTS teachers CASCADE")
    op.execute("DROP TABLE IF EXISTS students CASCADE")
    op.execute("DROP TABLE IF EXISTS schools CASCADE")
    op.execute("DROP TYPE IF EXISTS consent_status")
    op.execute("DROP TYPE IF EXISTS admin_role")
    op.execute("DROP TYPE IF EXISTS account_status")
