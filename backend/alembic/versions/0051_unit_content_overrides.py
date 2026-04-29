"""0051 — Unit content overrides + active version pointers (TA-1)

Introduces the two tables that back teacher content customization (Epic 12).

unit_content_overrides
  Append-only version history of teacher-edited content. Each row is one
  immutable version of one content type for one unit. The body field (JSONB)
  is never updated in place — new edits produce a new row with version_number
  incremented. The review_status field IS mutable (draft → pending_review →
  approved/rejected). The bundle_id links the four rows that make up one
  tutorial package (tutorial + quiz_set_1/2/3) so they transition atomically.

unit_content_active_versions
  Mutable pointer table — one row per (school_id, curriculum_id, unit_id, lang,
  content_type). Points to whichever override_id is currently live for students.
  NULL means the school has no active override: serve the platform OOB content.
  Publishing an approved version is an UPSERT into this table.

RLS
  Both tables follow the standard tenant-isolation pattern using the
  app.current_school_id session variable. 'bypass' allows service and pipeline
  roles full access.

Indexes
  unit_content_overrides:
    (curriculum_id, unit_id, lang, content_type)   — unit content list queries
    bundle_id  WHERE bundle_id IS NOT NULL          — bundle atomic transition
    (school_id, review_status)                      — governance queue filter

  unit_content_active_versions:
    (curriculum_id, unit_id, lang, content_type)   — serving path lookup

Revision ID: 0051
Revises: 0050
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0051"
down_revision: str | None = "0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── unit_content_overrides ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS unit_content_overrides (
            override_id       UUID         NOT NULL DEFAULT gen_random_uuid(),
            school_id         UUID         NOT NULL
                                  REFERENCES schools(school_id) ON DELETE CASCADE,
            curriculum_id     TEXT         NOT NULL,
            unit_id           TEXT         NOT NULL,
            lang              TEXT         NOT NULL DEFAULT 'en',
            content_type      TEXT         NOT NULL DEFAULT 'lesson'
                                  CHECK (content_type IN (
                                      'lesson', 'tutorial',
                                      'quiz_set_1', 'quiz_set_2', 'quiz_set_3',
                                      'experiment'
                                  )),
            bundle_id         UUID,
            content_source    TEXT         NOT NULL
                                  CHECK (content_source IN (
                                      'imported', 'ai_assisted', 'teacher_authored'
                                  )),
            source_override_id UUID
                                  REFERENCES unit_content_overrides(override_id)
                                  ON DELETE SET NULL,
            body              JSONB        NOT NULL,
            ai_model          TEXT,
            last_edited_by    UUID
                                  REFERENCES teachers(teacher_id) ON DELETE SET NULL,
            edited_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
            review_status     TEXT         NOT NULL DEFAULT 'draft'
                                  CHECK (review_status IN (
                                      'draft', 'pending_review', 'approved', 'rejected'
                                  )),
            rejection_reason  TEXT,
            version_number    INT          NOT NULL DEFAULT 1,
            PRIMARY KEY (override_id),
            UNIQUE (curriculum_id, unit_id, lang, content_type, version_number)
        )
    """)

    # Serving + list queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_uco_unit
            ON unit_content_overrides(curriculum_id, unit_id, lang, content_type)
    """)
    # Bundle atomic transition
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_uco_bundle_id
            ON unit_content_overrides(bundle_id)
            WHERE bundle_id IS NOT NULL
    """)
    # Governance queue: pending review per school
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_uco_school_status
            ON unit_content_overrides(school_id, review_status)
    """)

    # ── RLS — unit_content_overrides ─────────────────────────────────────────
    op.execute("ALTER TABLE unit_content_overrides ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE unit_content_overrides FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON unit_content_overrides
            USING (
                school_id::TEXT = current_setting('app.current_school_id', TRUE)
                OR current_setting('app.current_school_id', TRUE) = 'bypass'
            )
    """)

    # ── unit_content_active_versions ──────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS unit_content_active_versions (
            school_id      UUID         NOT NULL
                               REFERENCES schools(school_id) ON DELETE CASCADE,
            curriculum_id  TEXT         NOT NULL,
            unit_id        TEXT         NOT NULL,
            lang           TEXT         NOT NULL,
            content_type   TEXT         NOT NULL,
            override_id    UUID         NOT NULL
                               REFERENCES unit_content_overrides(override_id)
                               ON DELETE RESTRICT,
            activated_by   UUID
                               REFERENCES teachers(teacher_id) ON DELETE SET NULL,
            activated_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
            PRIMARY KEY (school_id, curriculum_id, unit_id, lang, content_type)
        )
    """)

    # Serving path: look up active version by curriculum/unit/lang/content_type
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ucav_lookup
            ON unit_content_active_versions(curriculum_id, unit_id, lang, content_type)
    """)

    # ── RLS — unit_content_active_versions ───────────────────────────────────
    op.execute("ALTER TABLE unit_content_active_versions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE unit_content_active_versions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON unit_content_active_versions
            USING (
                school_id::TEXT = current_setting('app.current_school_id', TRUE)
                OR current_setting('app.current_school_id', TRUE) = 'bypass'
            )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS unit_content_active_versions CASCADE")
    op.execute("DROP TABLE IF EXISTS unit_content_overrides CASCADE")
