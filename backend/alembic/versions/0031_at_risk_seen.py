"""0031 — at_risk_seen: track which at-risk students a teacher has acknowledged

Revision ID: 0031
Revises: 0030
Create Date: 2026-04-10
"""

from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS at_risk_seen (
            school_id    UUID          NOT NULL,
            student_id   UUID          NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            seen_by      UUID          NOT NULL REFERENCES teachers(teacher_id) ON DELETE CASCADE,
            seen_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            PRIMARY KEY (school_id, student_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS at_risk_seen")
