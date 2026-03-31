"""
0014_pipeline_payload_size

Revision ID: 0014
Revises: 0013
Create Date: 2026-03-31

Adds payload_bytes column to pipeline_jobs for tracking generated content size.
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE pipeline_jobs
        ADD COLUMN IF NOT EXISTS payload_bytes bigint
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE pipeline_jobs DROP COLUMN IF EXISTS payload_bytes")
