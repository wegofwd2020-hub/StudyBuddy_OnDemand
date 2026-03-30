"""demo_accounts

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-29

Demo student system schema.

Tables created:
  demo_requests       — analytics: every inbound demo request (email + IP)
  demo_verifications  — email verification tokens (60-min TTL, single-use)
  demo_accounts       — operational: active demo student sessions

A demo account maps 1:1 to a students row (auth_provider='demo').
Celery Beat sweeps expired/revoked accounts nightly.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── demo_requests (analytics — every inbound request) ─────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS demo_requests (
            id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
            email        text        NOT NULL,
            ip_address   text,
            user_agent   text,
            status       text        NOT NULL DEFAULT 'pending',
            requested_at timestamptz NOT NULL DEFAULT NOW(),
            CONSTRAINT demo_requests_status_check
                CHECK (status IN ('pending', 'verified', 'expired', 'revoked'))
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_requests_email  ON demo_requests(email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_requests_status ON demo_requests(status)")

    # ── demo_verifications (email verification tokens) ────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS demo_verifications (
            id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id uuid        NOT NULL REFERENCES demo_requests(id) ON DELETE CASCADE,
            email      text        NOT NULL,
            token      text        NOT NULL UNIQUE,
            expires_at timestamptz NOT NULL,
            used_at    timestamptz,
            created_at timestamptz NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_verif_token ON demo_verifications(token)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_verif_email ON demo_verifications(email)")

    # ── demo_accounts (operational — active demo sessions) ────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS demo_accounts (
            id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id    uuid        NOT NULL REFERENCES demo_requests(id) ON DELETE CASCADE,
            student_id    uuid        NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
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
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_accounts_email   ON demo_accounts(email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_accounts_student ON demo_accounts(student_id)")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_demo_accounts_active
        ON demo_accounts(expires_at)
        WHERE revoked_at IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_accounts")
    op.execute("DROP TABLE IF EXISTS demo_verifications")
    op.execute("DROP TABLE IF EXISTS demo_requests")
