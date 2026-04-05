"""
0018_pipeline_school_support

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-01

Extends pipeline_jobs to track school-triggered builds.

  school_id                — FK → schools(school_id), NULL for admin-triggered jobs
  triggered_by_teacher_id  — FK → teachers(teacher_id), NULL for admin-triggered jobs

Together these allow school-scoped job listing and monthly quota checks without
touching the existing triggered_by (admin_users FK) column.
"""

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE pipeline_jobs
            ADD COLUMN IF NOT EXISTS school_id uuid
                REFERENCES schools(school_id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS triggered_by_teacher_id uuid
                REFERENCES teachers(teacher_id) ON DELETE SET NULL
    """)
    # Supports monthly quota count: WHERE school_id = $1 AND triggered_at >= date_trunc('month', NOW())
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_school_month
            ON pipeline_jobs(school_id, triggered_at)
            WHERE school_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pipeline_jobs_school_month")
    op.execute("""
        ALTER TABLE pipeline_jobs
            DROP COLUMN IF EXISTS triggered_by_teacher_id,
            DROP COLUMN IF EXISTS school_id
    """)
