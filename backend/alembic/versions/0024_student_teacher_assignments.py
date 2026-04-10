"""
0024_student_teacher_assignments

Revision ID: 0024
Revises: 0023
Create Date: 2026-04-05

Enforce the rule that every school-enrolled student is assigned to exactly one
teacher per grade, and that assignment is owned entirely by the school.

New table:
  student_teacher_assignments — one row per (student, grade); teacher per grade

Constraint:
  UNIQUE (student_id, grade) — a student cannot be in two teachers' classes
                                for the same grade simultaneously.

Also adds grade + teacher_id to school_enrolments so the initial grade/teacher
assignment travels with the enrolment record.
"""

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── student_teacher_assignments ──────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS student_teacher_assignments (
            assignment_id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id      UUID        NOT NULL
                REFERENCES students(student_id) ON DELETE CASCADE,
            teacher_id      UUID        NOT NULL
                REFERENCES teachers(teacher_id) ON DELETE RESTRICT,
            school_id       UUID        NOT NULL
                REFERENCES schools(school_id) ON DELETE CASCADE,
            grade           SMALLINT    NOT NULL
                CHECK (grade BETWEEN 5 AND 12),
            assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            assigned_by     UUID
                REFERENCES teachers(teacher_id) ON DELETE SET NULL,

            -- A student can only be in one teacher's class per grade.
            -- Changing grade/teacher is a school admin action that replaces this row.
            UNIQUE (student_id, grade)
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_sta_student
            ON student_teacher_assignments (student_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_sta_teacher
            ON student_teacher_assignments (teacher_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_sta_school_grade
            ON student_teacher_assignments (school_id, grade)
    """)

    # ── Extend school_enrolments with grade + teacher at enrolment time ──────
    # Both columns are nullable: a school may enrol students before assigning
    # teachers, or may assign teachers in bulk via the assignment endpoint.
    op.execute("""
        ALTER TABLE school_enrolments
            ADD COLUMN IF NOT EXISTS grade        SMALLINT
                CHECK (grade BETWEEN 5 AND 12),
            ADD COLUMN IF NOT EXISTS teacher_id   UUID
                REFERENCES teachers(teacher_id) ON DELETE SET NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE school_enrolments DROP COLUMN IF EXISTS teacher_id")
    op.execute("ALTER TABLE school_enrolments DROP COLUMN IF EXISTS grade")
    op.execute("DROP INDEX IF EXISTS ix_sta_school_grade")
    op.execute("DROP INDEX IF EXISTS ix_sta_teacher")
    op.execute("DROP INDEX IF EXISTS ix_sta_student")
    op.execute("DROP TABLE IF EXISTS student_teacher_assignments")
