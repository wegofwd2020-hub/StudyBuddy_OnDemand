"""
0015_subject_name

Revision ID: 0015
Revises: 0014
Create Date: 2026-03-31

Adds subject_name column to content_subject_versions.
Backfills Grade 8 rows where subject already holds a human-readable name.
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE content_subject_versions
        ADD COLUMN IF NOT EXISTS subject_name text
    """)
    # Backfill rows where subject looks like a plain name (no hyphen pattern like G12-MATH)
    op.execute("""
        UPDATE content_subject_versions
        SET subject_name = subject
        WHERE subject_name IS NULL
          AND subject NOT SIMILAR TO '[A-Z][0-9]+-[A-Z]+'
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE content_subject_versions DROP COLUMN IF EXISTS subject_name")
