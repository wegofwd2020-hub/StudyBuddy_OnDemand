"""
0017_review_assignment

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-01

Adds review-assignment columns to content_subject_versions so that a
specific admin can be assigned responsibility for reviewing a version.

  assigned_to_admin_id  — FK → admin_users(admin_user_id), nullable
  assigned_at           — timestamp when the assignment was made, nullable
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE content_subject_versions
            ADD COLUMN IF NOT EXISTS assigned_to_admin_id uuid
                REFERENCES admin_users(admin_user_id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS assigned_at timestamptz
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_csv_assigned_to
            ON content_subject_versions (assigned_to_admin_id)
            WHERE assigned_to_admin_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_csv_assigned_to")
    op.execute("""
        ALTER TABLE content_subject_versions
            DROP COLUMN IF EXISTS assigned_to_admin_id,
            DROP COLUMN IF EXISTS assigned_at
    """)
