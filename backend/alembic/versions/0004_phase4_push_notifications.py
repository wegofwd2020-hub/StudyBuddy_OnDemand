"""phase4_push_notifications

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-25

Phase 4 schema: push notification infrastructure.

Tables created:
  push_tokens               — FCM device tokens per student
  notification_preferences  — per-student opt-in/out flags
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── push_tokens ───────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS push_tokens (
            token_id     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id   UUID        NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            device_token TEXT        NOT NULL,
            platform     TEXT        NOT NULL CHECK (platform IN ('ios', 'android')),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (student_id, device_token)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_push_tokens_student ON push_tokens(student_id)")

    # ── notification_preferences ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS notification_preferences (
            student_id          UUID        PRIMARY KEY REFERENCES students(student_id) ON DELETE CASCADE,
            streak_reminders    BOOLEAN     NOT NULL DEFAULT TRUE,
            weekly_summary      BOOLEAN     NOT NULL DEFAULT TRUE,
            quiz_nudges         BOOLEAN     NOT NULL DEFAULT TRUE,
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notification_preferences")
    op.execute("DROP TABLE IF EXISTS push_tokens")
