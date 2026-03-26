"""phase7_admin_review

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-25

Phase 7 schema additions:
  content_reviews  — add language_rating and content_rating columns
  content_subject_versions — add archived_at column for publish/rollback tracking
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add rating columns to content_reviews
    op.execute("""
        ALTER TABLE content_reviews
            ADD COLUMN IF NOT EXISTS language_rating INT CHECK (language_rating BETWEEN 1 AND 5),
            ADD COLUMN IF NOT EXISTS content_rating  INT CHECK (content_rating  BETWEEN 1 AND 5)
    """)

    # Add archived_at to content_subject_versions for publish/rollback tracking
    op.execute("""
        ALTER TABLE content_subject_versions
            ADD COLUMN IF NOT EXISTS archived_at timestamptz
    """)

    # Index to speed up review queue query
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_csv_status
        ON content_subject_versions(status)
    """)

    # Index for feedback listing by unit
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_scf_category
        ON student_content_feedback(unit_id, category)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_scf_category")
    op.execute("DROP INDEX IF EXISTS ix_csv_status")
    op.execute("ALTER TABLE content_subject_versions DROP COLUMN IF EXISTS archived_at")
    op.execute("ALTER TABLE content_reviews DROP COLUMN IF EXISTS content_rating")
    op.execute("ALTER TABLE content_reviews DROP COLUMN IF EXISTS language_rating")
