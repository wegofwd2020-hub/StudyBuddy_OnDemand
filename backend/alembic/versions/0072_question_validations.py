"""0072 — Question validations (per-school checked answers)

Per-school record of which quiz answers a reviewer has checked, keyed by
stable_question_id (ADR-008 / migration 0067) because `q1` names a SLOT within
a set, not a question, and the same question appears in several sets.

question_validations (new table)
  school_id            UUID         NOT NULL  FK → schools
  stable_question_id   TEXT         NOT NULL  Unique per school
  correct_text         TEXT         NOT NULL  The verified answer text
  validated_by         UUID         NOT NULL  FK → teachers (reviewer)
  validated_at         TIMESTAMPTZ  NOT NULL  When validation occurred
  PRIMARY KEY (school_id, stable_question_id)

RLS: standard tenant-isolation on app.current_school_id ('bypass' for the
service role).

Downgrade: DROP TABLE CASCADE.

Revision ID: 0072
Revises: 0071
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0072"
down_revision: str | None = "0071"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS question_validations (
            school_id           UUID        NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
            stable_question_id  TEXT        NOT NULL,
            correct_text        TEXT        NOT NULL,
            validated_by        UUID        NOT NULL REFERENCES teachers(teacher_id),
            validated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (school_id, stable_question_id)
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_question_validations_school "
        "ON question_validations(school_id)"
    )

    # ── RLS ───────────────────────────────────────────────────────────────────
    op.execute("ALTER TABLE question_validations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE question_validations FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON question_validations
            USING (
                school_id::TEXT = current_setting('app.current_school_id', TRUE)
                OR current_setting('app.current_school_id', TRUE) = 'bypass'
            )
    """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS question_validations CASCADE")
