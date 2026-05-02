"""0055 — school backup_cron column for Epic 15 Backup & Restore"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0055"
down_revision: str | None = "0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE schools ADD COLUMN IF NOT EXISTS backup_cron TEXT DEFAULT '0 2 * * *'
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE schools DROP COLUMN IF EXISTS backup_cron")
