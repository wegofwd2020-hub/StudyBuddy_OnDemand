"""phase2_content_schema

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-25

Phase 2 schema: tables for content pipeline, entitlement, and review workflow.

Tables (created in FK dependency order):
  curricula                 — default + school curriculum definitions
  curriculum_units          — unit metadata per curriculum
  content_subject_versions  — tracks pipeline-generated content versions per subject
  content_reviews           — human review records (Phase 7 full UI; table created now)
  content_annotations       — reviewer annotations on content blocks
  content_blocks            — admin-blocked content items
  student_content_feedback  — student flags on content
  app_versions              — mobile app version control
  student_entitlements      — per-student plan + usage tracking

Note: admin_users table uses admin_user_id as primary key (created in Phase 1).
      This migration references admin_users(admin_id) but Phase 1 uses admin_user_id.
      We reference admin_user_id to match the Phase 1 schema.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── curricula ─────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS curricula (
            curriculum_id   text          PRIMARY KEY,
            grade           int           NOT NULL,
            year            int           NOT NULL,
            name            text          NOT NULL,
            is_default      boolean       NOT NULL DEFAULT true,
            school_id       uuid          REFERENCES schools(school_id) ON DELETE SET NULL,
            created_at      timestamptz   NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_curricula_grade ON curricula(grade)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_curricula_school ON curricula(school_id)")

    # ── curriculum_units ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS curriculum_units (
            unit_id         text          NOT NULL,
            curriculum_id   text          NOT NULL REFERENCES curricula(curriculum_id) ON DELETE CASCADE,
            subject         text          NOT NULL,
            title           text          NOT NULL,
            description     text,
            has_lab         boolean       NOT NULL DEFAULT false,
            sort_order      int           NOT NULL DEFAULT 0,
            PRIMARY KEY (unit_id, curriculum_id)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_cu_curriculum ON curriculum_units(curriculum_id, subject)")

    # ── content_subject_versions ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS content_subject_versions (
            version_id          uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
            curriculum_id       text          NOT NULL,
            subject             text          NOT NULL,
            version_number      int           NOT NULL DEFAULT 1,
            status              text          NOT NULL DEFAULT 'ready_for_review',
            alex_warnings_count int           NOT NULL DEFAULT 0,
            generated_at        timestamptz   NOT NULL DEFAULT NOW(),
            published_at        timestamptz,
            pipeline_run_id     text,
            UNIQUE (curriculum_id, subject, version_number)
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_csv_curriculum_subject
        ON content_subject_versions(curriculum_id, subject)
    """)

    # ── content_reviews ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS content_reviews (
            review_id       uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
            version_id      uuid          NOT NULL REFERENCES content_subject_versions(version_id) ON DELETE CASCADE,
            reviewer_id     uuid          REFERENCES admin_users(admin_user_id) ON DELETE SET NULL,
            action          text          NOT NULL,
            notes           text,
            reviewed_at     timestamptz   NOT NULL DEFAULT NOW()
        )
    """)

    # ── content_annotations ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS content_annotations (
            annotation_id   uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
            version_id      uuid          NOT NULL REFERENCES content_subject_versions(version_id) ON DELETE CASCADE,
            unit_id         text          NOT NULL,
            content_type    text          NOT NULL,
            start_offset    int,
            end_offset      int,
            marked_text     text,
            annotation_text text,
            created_by      uuid          REFERENCES admin_users(admin_user_id) ON DELETE SET NULL,
            created_at      timestamptz   NOT NULL DEFAULT NOW()
        )
    """)

    # ── content_blocks ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS content_blocks (
            block_id        uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
            curriculum_id   text          NOT NULL,
            unit_id         text          NOT NULL,
            content_type    text          NOT NULL,
            reason          text,
            blocked_by      uuid          REFERENCES admin_users(admin_user_id) ON DELETE SET NULL,
            blocked_at      timestamptz   NOT NULL DEFAULT NOW(),
            unblocked_at    timestamptz,
            UNIQUE (curriculum_id, unit_id, content_type)
        )
    """)

    # ── student_content_feedback ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS student_content_feedback (
            feedback_id     uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id      uuid          NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            unit_id         text          NOT NULL,
            curriculum_id   text          NOT NULL,
            content_type    text          NOT NULL,
            category        text          NOT NULL,
            message         text,
            created_at      timestamptz   NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_scf_unit
        ON student_content_feedback(unit_id, curriculum_id)
    """)

    # ── app_versions ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS app_versions (
            id              serial        PRIMARY KEY,
            platform        text          NOT NULL,
            min_version     text          NOT NULL,
            latest_version  text          NOT NULL,
            release_notes   text,
            updated_at      timestamptz   NOT NULL DEFAULT NOW()
        )
    """)

    # Seed initial version
    op.execute("""
        INSERT INTO app_versions (platform, min_version, latest_version)
        VALUES ('all', '0.1.0', '0.1.0')
        ON CONFLICT DO NOTHING
    """)

    # ── student_entitlements ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS student_entitlements (
            student_id          uuid          PRIMARY KEY REFERENCES students(student_id) ON DELETE CASCADE,
            plan                text          NOT NULL DEFAULT 'free',
            lessons_accessed    int           NOT NULL DEFAULT 0,
            valid_until         timestamptz,
            updated_at          timestamptz   NOT NULL DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS student_entitlements CASCADE")
    op.execute("DROP TABLE IF EXISTS app_versions CASCADE")
    op.execute("DROP TABLE IF EXISTS student_content_feedback CASCADE")
    op.execute("DROP TABLE IF EXISTS content_blocks CASCADE")
    op.execute("DROP TABLE IF EXISTS content_annotations CASCADE")
    op.execute("DROP TABLE IF EXISTS content_reviews CASCADE")
    op.execute("DROP TABLE IF EXISTS content_subject_versions CASCADE")
    op.execute("DROP TABLE IF EXISTS curriculum_units CASCADE")
    op.execute("DROP TABLE IF EXISTS curricula CASCADE")
