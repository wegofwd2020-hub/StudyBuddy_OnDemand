"""0059 — Teacher capabilities (curriculum_mgmt)

Adds the additive-capability grant store behind issue #358. A school_admin can
grant a teacher one or more curriculum-management capabilities WITHOUT promoting
them to school_admin. The grant travels alongside the single `role` JWT claim as
a `capabilities[]` array, minted at login.

Capabilities (CHECK-constrained):
  curriculum.commission  — Gate 1: approve/adopt/load + trigger generation (spend)
  curriculum.review      — Gate 2: approve/publish generated content (editorial)
  curriculum_mgmt        — umbrella, covers both gates

school_admin is an implicit superset (no row needed); these grants exist to
empower *non-admin* teachers.

teacher_capabilities  (new table)
  teacher_id   UUID  FK → teachers  ON DELETE CASCADE
  school_id    UUID  FK → schools   ON DELETE CASCADE  (denormalised for RLS)
  capability   TEXT  CHECK in the 3 values above
  granted_by   UUID  FK → teachers  ON DELETE SET NULL
  granted_at   TIMESTAMPTZ DEFAULT now()
  PRIMARY KEY (teacher_id, capability)

RLS: standard tenant-isolation on app.current_school_id ('bypass' for the login
mint / service role). school_id is denormalised onto the row so the policy needs
no subquery (consistent with school_adopted_curricula, classroom_students).

Downgrade: DROP TABLE — additive, no dependents, no data-only pre-drop needed.

Revision ID: 0059
Revises: 0058
Create Date: 2026-05-21
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0059"
down_revision: str | None = "0058"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS teacher_capabilities (
            teacher_id   UUID         NOT NULL
                             REFERENCES teachers(teacher_id) ON DELETE CASCADE,
            school_id    UUID         NOT NULL
                             REFERENCES schools(school_id) ON DELETE CASCADE,
            capability   TEXT         NOT NULL
                             CHECK (capability IN
                                 ('curriculum.commission', 'curriculum.review', 'curriculum_mgmt')),
            granted_by   UUID         REFERENCES teachers(teacher_id) ON DELETE SET NULL,
            granted_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
            PRIMARY KEY (teacher_id, capability)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_teacher_capabilities_school_id "
        "ON teacher_capabilities(school_id)"
    )

    # ── RLS ───────────────────────────────────────────────────────────────────
    op.execute("ALTER TABLE teacher_capabilities ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE teacher_capabilities FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON teacher_capabilities
            USING (
                school_id::TEXT = current_setting('app.current_school_id', TRUE)
                OR current_setting('app.current_school_id', TRUE) = 'bypass'
            )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS teacher_capabilities CASCADE")
