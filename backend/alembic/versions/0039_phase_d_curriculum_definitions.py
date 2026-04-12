"""0039 — Phase D: Curriculum Definitions

Introduces the Curriculum Definition entity — the structured spec a teacher
builds via the form UI before a pipeline run.  A Definition captures the intent
(grade, subjects, units, languages); the platform admin/school admin approves it
before the pipeline is triggered (Phase E).

New table
─────────
curriculum_definitions
  definition_id    UUID PK
  school_id        UUID FK → schools ON DELETE CASCADE
  submitted_by     UUID FK → teachers (the teacher who built the form)
  name             TEXT NOT NULL       e.g. "Grade 8 STEM — Semester 1"
  grade            INT  NOT NULL
  languages        TEXT[] NOT NULL DEFAULT '{en}'
  subjects         JSONB NOT NULL     [{subject_label, units:[{title}]}]
  status           TEXT NOT NULL DEFAULT 'pending_approval'
                   CHECK status IN ('pending_approval','approved','rejected')
  rejection_reason TEXT               populated on reject
  reviewed_by      UUID               FK → teachers (the school_admin who acted)
  reviewed_at      TIMESTAMPTZ
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()

RLS policy
──────────
Rows are scoped to the school:
  USING (school_id::text = current_setting('app.current_school_id', true))
"""

from __future__ import annotations

from typing import Union

from alembic import op


revision: str = "0039"
down_revision: Union[str, None] = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS curriculum_definitions (
            definition_id    UUID        NOT NULL DEFAULT gen_random_uuid(),
            school_id        UUID        NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
            submitted_by     UUID        NOT NULL REFERENCES teachers(teacher_id),
            name             TEXT        NOT NULL,
            grade            INT         NOT NULL CHECK (grade BETWEEN 1 AND 12),
            languages        TEXT[]      NOT NULL DEFAULT '{en}',
            subjects         JSONB       NOT NULL DEFAULT '[]',
            status           TEXT        NOT NULL DEFAULT 'pending_approval'
                             CHECK (status IN ('pending_approval', 'approved', 'rejected')),
            rejection_reason TEXT,
            reviewed_by      UUID        REFERENCES teachers(teacher_id),
            reviewed_at      TIMESTAMPTZ,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (definition_id)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_curriculum_defs_school ON curriculum_definitions (school_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_curriculum_defs_status ON curriculum_definitions (school_id, status)")

    # ── Row-Level Security ────────────────────────────────────────────────────
    op.execute("ALTER TABLE curriculum_definitions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE curriculum_definitions FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY tenant_isolation ON curriculum_definitions
            USING (
                school_id::text = current_setting('app.current_school_id', true)
                OR current_setting('app.current_school_id', true) = 'bypass'
            )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS curriculum_definitions CASCADE")
