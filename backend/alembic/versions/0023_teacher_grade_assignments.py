"""
0023_teacher_grade_assignments

Revision ID: 0023
Revises: 0022
Create Date: 2026-04-01

Track which grades each teacher is assigned to within their school.

New table:
  teacher_grade_assignments — one row per (teacher, grade) pair
"""

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS teacher_grade_assignments (
            assignment_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            teacher_id     UUID        NOT NULL
                REFERENCES teachers(teacher_id) ON DELETE CASCADE,
            school_id      UUID        NOT NULL
                REFERENCES schools(school_id) ON DELETE CASCADE,
            grade          SMALLINT    NOT NULL
                CHECK (grade BETWEEN 5 AND 12),
            assigned_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (teacher_id, grade)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_teacher_grade_school
            ON teacher_grade_assignments (school_id, grade)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_teacher_grade_teacher
            ON teacher_grade_assignments (teacher_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_teacher_grade_teacher")
    op.execute("DROP INDEX IF EXISTS ix_teacher_grade_school")
    op.execute("DROP TABLE IF EXISTS teacher_grade_assignments")
