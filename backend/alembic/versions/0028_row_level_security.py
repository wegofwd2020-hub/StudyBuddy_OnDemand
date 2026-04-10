"""
0028_row_level_security

Revision ID: 0028
Revises: 0027
Create Date: 2026-04-05

PostgreSQL Row-Level Security (RLS) for tenant isolation.

Per ADR-001 Decision 3: shared SaaS instance with DB-enforced tenant isolation.
Every school's data is physically scoped by the DB engine — a teacher from
School A cannot read School B's rows regardless of application behaviour.

Mechanism
---------
The application sets a session variable on every connection before executing
queries:

    SELECT set_config('app.current_school_id', '<uuid-or-bypass>', false)

RLS policies on each tenant-scoped table use:

    COALESCE(current_setting('app.current_school_id', TRUE), '')
        IN ('bypass', <school_id_column>::text)

Values:
  '<uuid>'  — teacher-authenticated requests; only that school's rows visible
  'bypass'  — admin, student, and unauthenticated requests; all rows visible
  '' / NULL — variable not set (should not happen in production); all rows DENIED

FORCE ROW LEVEL SECURITY is applied so the constraint holds even for the
table owner (the DB user the app connects as).

Tables covered
--------------
  schools                    — school_id (read/write by school admin only)
  teachers                   — school_id
  school_enrolments          — school_id
  student_teacher_assignments — school_id
  teacher_grade_assignments  — school_id
  school_subscriptions       — school_id
  curricula                  — owner_id / owner_type ('platform' rows shared)
"""

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

# Reusable policy USING / WITH CHECK expression for tables with a direct school_id column.
_SCHOOL_POLICY = """
    COALESCE(current_setting('app.current_school_id', TRUE), '') = 'bypass'
    OR (
        COALESCE(current_setting('app.current_school_id', TRUE), '') <> ''
        AND school_id::text = current_setting('app.current_school_id', TRUE)
    )
"""


def _enable_rls(table: str, using: str, with_check: str | None = None) -> None:
    wc = with_check if with_check is not None else using
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.execute(
        f"CREATE POLICY tenant_isolation ON {table} "
        f"USING ({using}) "
        f"WITH CHECK ({wc})"
    )


def _disable_rls(table: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    # ── schools ───────────────────────────────────────────────────────────────
    # INSERT allowed on bypass (school registration is public — no JWT).
    # Teachers may only SELECT/UPDATE/DELETE their own school row.
    _enable_rls("schools", _SCHOOL_POLICY)

    # ── teachers ──────────────────────────────────────────────────────────────
    # Demo teachers have school_id IS NULL; the bypass path covers admin inserts.
    # Teacher invites (INSERT) run under a school_admin JWT — school_id matches.
    _enable_rls("teachers", _SCHOOL_POLICY)

    # ── school_enrolments ─────────────────────────────────────────────────────
    _enable_rls("school_enrolments", _SCHOOL_POLICY)

    # ── student_teacher_assignments ───────────────────────────────────────────
    _enable_rls("student_teacher_assignments", _SCHOOL_POLICY)

    # ── teacher_grade_assignments ─────────────────────────────────────────────
    _enable_rls("teacher_grade_assignments", _SCHOOL_POLICY)

    # ── school_subscriptions ──────────────────────────────────────────────────
    _enable_rls("school_subscriptions", _SCHOOL_POLICY)

    # ── curricula ─────────────────────────────────────────────────────────────
    # Platform-default curricula (owner_type = 'platform') are readable by ALL.
    # School curricula (owner_type = 'school') are scoped to the owning school.
    curricula_using = """
        COALESCE(current_setting('app.current_school_id', TRUE), '') = 'bypass'
        OR owner_type = 'platform'
        OR (
            owner_type = 'school'
            AND COALESCE(current_setting('app.current_school_id', TRUE), '') <> ''
            AND owner_id::text = current_setting('app.current_school_id', TRUE)
        )
    """
    _enable_rls("curricula", curricula_using)


def downgrade() -> None:
    for table in (
        "curricula",
        "school_subscriptions",
        "teacher_grade_assignments",
        "student_teacher_assignments",
        "school_enrolments",
        "teachers",
        "schools",
    ):
        _disable_rls(table)
