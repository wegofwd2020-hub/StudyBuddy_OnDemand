"""
backend/alembic/versions/0008_phase9_enrolment.py

Phase 9 schema additions:
  school_enrolments — teacher-uploaded student roster;
                      rows transition pending → active when student registers.
"""

revision = "0008"
down_revision = "0007"

from alembic import op


def upgrade() -> None:
    # ── school_enrolments ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS school_enrolments (
            enrolment_id    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
            school_id       uuid        NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
            student_email   text        NOT NULL,
            student_id      uuid        REFERENCES students(student_id) ON DELETE SET NULL,
            status          text        NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'active')),
            added_at        timestamptz NOT NULL DEFAULT NOW(),
            UNIQUE (school_id, student_email)
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_enrolments_school_status
        ON school_enrolments(school_id, status)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_enrolments_email
        ON school_enrolments(student_email)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_enrolments_student_id
        ON school_enrolments(student_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_enrolments_student_id")
    op.execute("DROP INDEX IF EXISTS ix_enrolments_email")
    op.execute("DROP INDEX IF EXISTS ix_enrolments_school_status")
    op.execute("DROP TABLE IF EXISTS school_enrolments CASCADE")
