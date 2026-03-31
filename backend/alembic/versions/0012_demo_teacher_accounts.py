"""demo_teacher_accounts

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-30

Demo teacher system schema.

Tables created:
  demo_teacher_requests       — every inbound teacher demo request (email + IP)
  demo_teacher_verifications  — email verification tokens (60-min TTL, single-use)
  demo_teacher_accounts       — active demo teacher sessions

A demo teacher account maps 1:1 to a teachers row (auth_provider='demo').
Celery Beat sweeps expired/revoked accounts nightly at 03:15 UTC.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── demo_teacher_requests ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS demo_teacher_requests (
            id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
            email        text        NOT NULL,
            ip_address   text,
            user_agent   text,
            status       text        NOT NULL DEFAULT 'pending',
            requested_at timestamptz NOT NULL DEFAULT NOW(),
            CONSTRAINT demo_teacher_requests_status_check
                CHECK (status IN ('pending', 'verified', 'expired', 'revoked'))
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_teacher_req_email  ON demo_teacher_requests(email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_teacher_req_status ON demo_teacher_requests(status)")

    # ── demo_teacher_verifications ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS demo_teacher_verifications (
            id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id uuid        NOT NULL REFERENCES demo_teacher_requests(id) ON DELETE CASCADE,
            email      text        NOT NULL,
            token      text        NOT NULL UNIQUE,
            expires_at timestamptz NOT NULL,
            used_at    timestamptz,
            created_at timestamptz NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_teacher_verif_token ON demo_teacher_verifications(token)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_teacher_verif_email ON demo_teacher_verifications(email)")

    # ── demo_teacher_accounts ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS demo_teacher_accounts (
            id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id    uuid        NOT NULL REFERENCES demo_teacher_requests(id) ON DELETE CASCADE,
            teacher_id    uuid        NOT NULL REFERENCES teachers(teacher_id) ON DELETE CASCADE,
            email         text        NOT NULL UNIQUE,
            password_hash text        NOT NULL,
            expires_at    timestamptz NOT NULL,
            created_at    timestamptz NOT NULL DEFAULT NOW(),
            last_login_at timestamptz,
            extended_at   timestamptz,
            extended_by   uuid,
            revoked_at    timestamptz,
            revoked_by    uuid
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_teacher_acc_email   ON demo_teacher_accounts(email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_teacher_acc_teacher ON demo_teacher_accounts(teacher_id)")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_demo_teacher_acc_active
        ON demo_teacher_accounts(expires_at)
        WHERE revoked_at IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_teacher_accounts")
    op.execute("DROP TABLE IF EXISTS demo_teacher_verifications")
    op.execute("DROP TABLE IF EXISTS demo_teacher_requests")
