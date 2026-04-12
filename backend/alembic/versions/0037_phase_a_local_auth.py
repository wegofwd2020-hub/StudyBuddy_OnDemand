"""0037 — Phase A local auth

Adds local-auth columns to teachers and students so that school-provisioned
users can log in with email + password instead of Auth0.

Schema changes
──────────────
teachers
  + password_hash  TEXT NULL   — bcrypt hash; NULL for Auth0-only accounts
  + first_login    BOOLEAN NOT NULL DEFAULT FALSE
                   Set TRUE when a default password is issued by school admin.
                   Cleared to FALSE when the user changes their own password.

students
  + password_hash  TEXT NULL   — bcrypt hash; NULL for Auth0-only accounts
  + first_login    BOOLEAN NOT NULL DEFAULT FALSE

Both tables already have auth_provider TEXT which accepts 'auth0'.
School-provisioned users will use auth_provider = 'local' (no constraint change
needed — the column is plain TEXT).

Revision ID: 0037
Revises: 0036
Create Date: 2026-04-11
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0037"
down_revision: Union[str, None] = "0036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── teachers ──────────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE teachers
            ADD COLUMN IF NOT EXISTS password_hash TEXT,
            ADD COLUMN IF NOT EXISTS first_login   BOOLEAN NOT NULL DEFAULT FALSE
    """)

    # ── students ──────────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE students
            ADD COLUMN IF NOT EXISTS password_hash TEXT,
            ADD COLUMN IF NOT EXISTS first_login   BOOLEAN NOT NULL DEFAULT FALSE
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE teachers
            DROP COLUMN IF EXISTS password_hash,
            DROP COLUMN IF EXISTS first_login
    """)
    op.execute("""
        ALTER TABLE students
            DROP COLUMN IF EXISTS password_hash,
            DROP COLUMN IF EXISTS first_login
    """)
