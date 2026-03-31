"""
0013_pipeline_jobs

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-31

Adds pipeline_jobs table to persist admin-triggered pipeline job history.
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_jobs (
            job_id          text          PRIMARY KEY,
            curriculum_id   text          NOT NULL,
            grade           int,
            langs           text          NOT NULL DEFAULT 'en',
            force           boolean       NOT NULL DEFAULT false,
            status          text          NOT NULL DEFAULT 'queued',
            built           int           NOT NULL DEFAULT 0,
            failed          int           NOT NULL DEFAULT 0,
            total           int           NOT NULL DEFAULT 0,
            triggered_by    uuid          REFERENCES admin_users(admin_user_id) ON DELETE SET NULL,
            triggered_at    timestamptz   NOT NULL DEFAULT NOW(),
            started_at      timestamptz,
            completed_at    timestamptz,
            error           text
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_triggered ON pipeline_jobs(triggered_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_status ON pipeline_jobs(status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pipeline_jobs_status")
    op.execute("DROP INDEX IF EXISTS ix_pipeline_jobs_triggered")
    op.execute("DROP TABLE IF EXISTS pipeline_jobs")
