"""0060 — Curriculum Authoring Studio (super-admin)

Super-admin TOC-driven content authoring. A super-admin pastes a free-text
table of contents; the system structures it (LLM), runs an advisory flow
analysis, lets the admin edit the structured tree, materialises it as a
*staged* platform curriculum, generates per-topic content, and (PR-B) supports
unlimited regenerate-with-reason, per-topic append-only versioning, whole-
curriculum manifest snapshots/restore, and publish (private | school catalog).

Scope distinction (requirement d — "not mixed with other school curriculum"):
authored curricula are created with owner_type='platform' and
source_type='admin_authored', is_default=FALSE while staged. They never carry a
school_id, so they live in the platform namespace, isolated from school forks.
On publish-to-catalog the row's is_default flips TRUE and it becomes adoptable
via the Epic 12 school library.

Tables (all platform/admin-scoped — NOT tenant-scoped, like pipeline_jobs):
  authoring_projects        one row per authoring session (state machine)
  authoring_topic_versions  append-only per-topic content versions
  authoring_active_versions mutable pointer: which version is "live" per topic
  authoring_snapshots       whole-curriculum manifest snapshots (point-in-time)

RLS: these tables are not tenant-scoped (no school_id, gated by admin JWT +
the curriculum:author permission), so they get no app.current_school_id policy
— consistent with pipeline_jobs. The curricula/curriculum_units rows the
service writes ARE under the migration-0046 platform write-guard, so the
service path uses get_db() which stamps app.current_school_id='bypass' for
admin requests (pitfall #28).

Also extends curricula.source_type CHECK to allow 'admin_authored'.

Revision ID: 0060
Revises: 0059
Create Date: 2026-05-26
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0060"
down_revision: str | None = "0059"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── curricula.source_type: allow 'admin_authored' ─────────────────────────
    op.execute("ALTER TABLE curricula DROP CONSTRAINT IF EXISTS curricula_source_type_check")
    op.execute("""
        ALTER TABLE curricula
            ADD CONSTRAINT curricula_source_type_check
            CHECK (source_type IN ('default', 'xlsx_upload', 'ui_form', 'school', 'admin_authored'))
    """)

    # ── authoring_projects ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS authoring_projects (
            project_id          UUID         NOT NULL DEFAULT gen_random_uuid(),
            title               TEXT         NOT NULL,
            grade               INT          CHECK (grade BETWEEN 1 AND 12),
            languages           TEXT[]       NOT NULL DEFAULT '{en}',
            raw_toc             TEXT,
            structured_toc      JSONB,
            flow_report         JSONB,
            status              TEXT         NOT NULL DEFAULT 'draft'
                                    CHECK (status IN (
                                        'draft', 'analyzing', 'analyzed', 'structured',
                                        'generating', 'generated', 'published')),
            curriculum_id       TEXT         REFERENCES curricula(curriculum_id) ON DELETE SET NULL,
            visibility          TEXT         NOT NULL DEFAULT 'private'
                                    CHECK (visibility IN ('private', 'catalog')),
            current_snapshot_id UUID,
            analyze_error       TEXT,
            created_by          UUID,
            created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
            PRIMARY KEY (project_id)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_authoring_projects_status "
        "ON authoring_projects(status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_authoring_projects_curriculum_id "
        "ON authoring_projects(curriculum_id) WHERE curriculum_id IS NOT NULL"
    )

    # ── authoring_topic_versions (append-only) ────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS authoring_topic_versions (
            topic_version_id  UUID         NOT NULL DEFAULT gen_random_uuid(),
            project_id        UUID         NOT NULL
                                  REFERENCES authoring_projects(project_id) ON DELETE CASCADE,
            unit_id           TEXT         NOT NULL,
            lang              TEXT         NOT NULL DEFAULT 'en',
            content_type      TEXT         NOT NULL
                                  CHECK (content_type IN (
                                      'lesson', 'tutorial',
                                      'quiz_set_1', 'quiz_set_2', 'quiz_set_3',
                                      'experiment')),
            body              JSONB        NOT NULL,
            version_number    INT          NOT NULL,
            regen_reason      TEXT,
            flow_recheck      JSONB,
            ai_model          TEXT,
            tokens_used       INT,
            cost_usd          NUMERIC(10, 4),
            review_status     TEXT         NOT NULL DEFAULT 'pending'
                                  CHECK (review_status IN ('pending', 'accepted')),
            created_by        UUID,
            created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
            PRIMARY KEY (topic_version_id),
            UNIQUE (project_id, unit_id, lang, content_type, version_number)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_authoring_topic_versions_lookup "
        "ON authoring_topic_versions(project_id, unit_id, lang, content_type)"
    )

    # ── authoring_active_versions (mutable pointer) ───────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS authoring_active_versions (
            project_id        UUID         NOT NULL
                                  REFERENCES authoring_projects(project_id) ON DELETE CASCADE,
            unit_id           TEXT         NOT NULL,
            lang              TEXT         NOT NULL,
            content_type      TEXT         NOT NULL,
            topic_version_id  UUID         NOT NULL
                                  REFERENCES authoring_topic_versions(topic_version_id) ON DELETE RESTRICT,
            activated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            PRIMARY KEY (project_id, unit_id, lang, content_type)
        )
    """)

    # ── authoring_snapshots (whole-curriculum manifest) ───────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS authoring_snapshots (
            snapshot_id      UUID         NOT NULL DEFAULT gen_random_uuid(),
            project_id       UUID         NOT NULL
                                 REFERENCES authoring_projects(project_id) ON DELETE CASCADE,
            snapshot_number  INT          NOT NULL,
            manifest         JSONB        NOT NULL,
            label            TEXT,
            created_by       UUID,
            created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
            PRIMARY KEY (snapshot_id),
            UNIQUE (project_id, snapshot_number)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS authoring_snapshots CASCADE")
    op.execute("DROP TABLE IF EXISTS authoring_active_versions CASCADE")
    op.execute("DROP TABLE IF EXISTS authoring_topic_versions CASCADE")
    op.execute("DROP TABLE IF EXISTS authoring_projects CASCADE")

    # Remove the feature's own staged curricula before reverting the CHECK —
    # otherwise the narrower constraint can't be re-added while admin_authored
    # rows exist. These are studio artifacts; removing them is the documented,
    # safe downgrade behaviour. curriculum_units cascade via their FK.
    op.execute("DELETE FROM curricula WHERE source_type = 'admin_authored'")

    # Revert source_type CHECK to the pre-0060 set.
    op.execute("ALTER TABLE curricula DROP CONSTRAINT IF EXISTS curricula_source_type_check")
    op.execute("""
        ALTER TABLE curricula
            ADD CONSTRAINT curricula_source_type_check
            CHECK (source_type IN ('default', 'xlsx_upload', 'ui_form', 'school'))
    """)
