"""
0025_schema_corrections

Revision ID: 0025
Revises: 0024
Create Date: 2026-04-05

Schema corrections from ADR-001 compliance review (G1, G2).

G1 — schools.contact_email UNIQUE
  Without this, two separate school registrations with the same email cause
  a confusing error on the teachers INSERT (teachers.email UNIQUE fires first).
  Adding the constraint here makes the failure point clear and the error message
  meaningful.

G2 — teachers CHECK (school_id IS NOT NULL OR auth_provider = 'demo')
  teachers.school_id was made nullable in 0016 to support demo teacher accounts.
  The business rule is: only demo teachers may have a NULL school_id. Real teacher
  rows must always have a school_id. This CHECK constraint makes that rule
  DB-enforceable rather than relying solely on application logic.

G3 (code-only — see enrolment_service.py get_roster) — roster JOIN grade filter
  The LEFT JOIN on student_teacher_assignments lacked a grade condition. A student
  assigned to multiple grades would appear multiple times in the roster. Fixed in
  the service layer (no migration needed).

G4 — single active grade per student (deferred)
  Design question: should a student ever hold assignments for more than one grade
  simultaneously? If not, UNIQUE (student_id) on student_teacher_assignments would
  enforce it. Deferred until confirmed.
"""

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # G1 — unique contact email on schools
    op.execute("""
        ALTER TABLE schools
            ADD CONSTRAINT uq_schools_contact_email UNIQUE (contact_email)
    """)

    # G2 — real teachers must have a school_id; only demo teachers may be NULL
    op.execute("""
        ALTER TABLE teachers
            ADD CONSTRAINT chk_teachers_school_id_or_demo
            CHECK (school_id IS NOT NULL OR auth_provider = 'demo')
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE teachers DROP CONSTRAINT IF EXISTS chk_teachers_school_id_or_demo")
    op.execute("ALTER TABLE schools DROP CONSTRAINT IF EXISTS uq_schools_contact_email")
