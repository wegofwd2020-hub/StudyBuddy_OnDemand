"""0050 — School Curriculum Library (TA-0)

Introduces the school curriculum adoption catalog — the mechanism by which
a school "adopts" an out-of-the-box (OOB) platform curriculum and, on first
teacher import, gets a school-owned fork of that curriculum (Option B, Epic 12).

Changes
───────
curricula
  + source_curriculum_id  TEXT  FK → curricula(curriculum_id) ON DELETE SET NULL
    Populated only on school-owned forks; NULL for all OOB and school-authored
    curricula that were not derived from an OOB source.

school_adopted_curricula  (new table)
  Tracks which schools have adopted which OOB curricula, and (once first import
  happens) where their forked curriculum row lives.

  adoption_id           UUID  PK
  school_id             UUID  FK → schools  ON DELETE CASCADE
  curriculum_id         TEXT  FK → curricula (the OOB source)  ON DELETE RESTRICT
  forked_curriculum_id  TEXT  FK → curricula ON DELETE SET NULL  (NULL until first import)
  grade                 INT   denormalised from source for fast filtering
  adopted_by            UUID  FK → teachers ON DELETE SET NULL
  adopted_at            TIMESTAMPTZ DEFAULT now()
  status                TEXT  'active' | 'deactivated'
  notes                 TEXT  optional school annotation

  UNIQUE (school_id, curriculum_id)  — one adoption record per OOB curriculum per school

RLS: school_adopted_curricula inherits the standard tenant-isolation policy
     (app.current_school_id session variable, 'bypass' for service/pipeline role).

Revision ID: 0050
Revises: 0049
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0050"
down_revision: str | None = "0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── curricula: lineage column ─────────────────────────────────────────────
    op.execute("""
        ALTER TABLE curricula
            ADD COLUMN IF NOT EXISTS source_curriculum_id TEXT
                REFERENCES curricula(curriculum_id) ON DELETE SET NULL
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_curricula_source_curriculum_id "
        "ON curricula(source_curriculum_id) WHERE source_curriculum_id IS NOT NULL"
    )

    # ── school_adopted_curricula ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS school_adopted_curricula (
            adoption_id           UUID         NOT NULL DEFAULT gen_random_uuid(),
            school_id             UUID         NOT NULL
                                      REFERENCES schools(school_id) ON DELETE CASCADE,
            curriculum_id         TEXT         NOT NULL
                                      REFERENCES curricula(curriculum_id) ON DELETE RESTRICT,
            forked_curriculum_id  TEXT
                                      REFERENCES curricula(curriculum_id) ON DELETE SET NULL,
            grade                 INT          CHECK (grade BETWEEN 1 AND 12),
            adopted_by            UUID
                                      REFERENCES teachers(teacher_id) ON DELETE SET NULL,
            adopted_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
            status                TEXT         NOT NULL DEFAULT 'active'
                                      CHECK (status IN ('active', 'deactivated')),
            notes                 TEXT,
            PRIMARY KEY (adoption_id),
            UNIQUE (school_id, curriculum_id)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_school_adopted_curricula_school_id "
        "ON school_adopted_curricula(school_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_school_adopted_curricula_curriculum_id "
        "ON school_adopted_curricula(curriculum_id)"
    )

    # ── RLS ───────────────────────────────────────────────────────────────────
    op.execute("ALTER TABLE school_adopted_curricula ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE school_adopted_curricula FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON school_adopted_curricula
            USING (
                school_id::TEXT = current_setting('app.current_school_id', TRUE)
                OR current_setting('app.current_school_id', TRUE) = 'bypass'
            )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS school_adopted_curricula CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_curricula_source_curriculum_id")
    op.execute("ALTER TABLE curricula DROP COLUMN IF EXISTS source_curriculum_id")
