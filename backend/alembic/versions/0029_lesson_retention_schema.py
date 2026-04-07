"""
0029_lesson_retention_schema

Revision ID: 0029
Revises: 0028
Create Date: 2026-04-07

Lesson Retention Service — Phase A schema (GitHub issue #90).

Changes
-------

curricula
  + retention_status  TEXT NOT NULL DEFAULT 'active'
                      CHECK ('active', 'unavailable', 'purged')
                      Separate from the existing pipeline `status` column.
  + expires_at        TIMESTAMPTZ — 1 year from creation (school curricula only).
                      NULL for platform-default curricula (they never expire).
  + grace_until       TIMESTAMPTZ — set to expires_at + 180 days when retention
                      status transitions to 'unavailable'.  NULL while active.
  + renewed_at        TIMESTAMPTZ — timestamp of last admin renewal action.
                      NULL if never renewed.

content_subject_versions
  + tokens_used       INTEGER — token count returned by the Anthropic API for
                      this pipeline run.  Populated by the pipeline worker on
                      job completion.
  + cost_usd          NUMERIC(10,6) — tokens_used × cost_per_token at generation
                      time.  Stored for billing statement display; not recalculated.

school_storage_quotas (new table)
  One row per school.  Tracks storage allocation and current usage.
  base_gb     — GB included in the school subscription (default: 5)
  purchased_gb — additional GB bought as add-ons via Stripe
  used_bytes  — running total of payload_bytes across all pipeline jobs;
                updated atomically after each job and reconciled nightly.
  RLS policy mirrors the schools table (school_id-scoped).

grade_curriculum_assignments (new table)
  Allows a school admin to pin a specific curriculum version to a grade.
  One row per (school_id, grade) pair — the currently active version for
  that grade.  The curriculum resolver reads this instead of deriving the
  curriculum from enrolment alone when a school has multiple versions.
  RLS policy mirrors school_enrolments (school_id-scoped).
"""

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None

# Shared RLS expression for school_id-scoped tables.
_SCHOOL_POLICY = """
    COALESCE(current_setting('app.current_school_id', TRUE), '') = 'bypass'
    OR (
        COALESCE(current_setting('app.current_school_id', TRUE), '') <> ''
        AND school_id::text = current_setting('app.current_school_id', TRUE)
    )
"""


def upgrade() -> None:
    # ── curricula: retention columns ──────────────────────────────────────────

    op.execute("""
        ALTER TABLE curricula
            ADD COLUMN IF NOT EXISTS retention_status TEXT NOT NULL DEFAULT 'active',
            ADD COLUMN IF NOT EXISTS expires_at       TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS grace_until      TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS renewed_at       TIMESTAMPTZ
    """)

    op.execute("""
        ALTER TABLE curricula
            ADD CONSTRAINT curricula_retention_status_check
            CHECK (retention_status IN ('active', 'unavailable', 'purged'))
    """)

    # Backfill expires_at for existing school-owned curricula.
    # Platform-default curricula (owner_type = 'platform') never expire.
    op.execute("""
        UPDATE curricula
        SET expires_at = created_at + INTERVAL '1 year'
        WHERE owner_type = 'school'
          AND expires_at IS NULL
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_curricula_retention_status
        ON curricula(retention_status)
        WHERE retention_status <> 'active'
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_curricula_expires_at
        ON curricula(expires_at)
        WHERE expires_at IS NOT NULL AND retention_status = 'active'
    """)

    # ── content_subject_versions: pipeline cost columns ───────────────────────

    op.execute("""
        ALTER TABLE content_subject_versions
            ADD COLUMN IF NOT EXISTS tokens_used INTEGER,
            ADD COLUMN IF NOT EXISTS cost_usd    NUMERIC(10, 6)
    """)

    # ── school_storage_quotas ─────────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS school_storage_quotas (
            quota_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            school_id       UUID        NOT NULL UNIQUE
                                        REFERENCES schools(school_id) ON DELETE CASCADE,
            base_gb         INTEGER     NOT NULL DEFAULT 5,
            purchased_gb    INTEGER     NOT NULL DEFAULT 0,
            used_bytes      BIGINT      NOT NULL DEFAULT 0,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT school_storage_quotas_base_gb_check   CHECK (base_gb >= 0),
            CONSTRAINT school_storage_quotas_purchased_check CHECK (purchased_gb >= 0),
            CONSTRAINT school_storage_quotas_used_check      CHECK (used_bytes >= 0)
        )
    """)

    # Seed one row per existing school so the metering endpoint always has a row.
    op.execute("""
        INSERT INTO school_storage_quotas (school_id)
        SELECT school_id FROM schools
        ON CONFLICT DO NOTHING
    """)

    # RLS — school_id-scoped, same pattern as schools/teachers.
    op.execute("ALTER TABLE school_storage_quotas ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE school_storage_quotas FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON school_storage_quotas")
    op.execute(f"""
        CREATE POLICY tenant_isolation ON school_storage_quotas
        USING ({_SCHOOL_POLICY})
        WITH CHECK ({_SCHOOL_POLICY})
    """)

    # ── grade_curriculum_assignments ──────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS grade_curriculum_assignments (
            school_id       UUID        NOT NULL
                                        REFERENCES schools(school_id) ON DELETE CASCADE,
            grade           INTEGER     NOT NULL
                                        CHECK (grade BETWEEN 5 AND 12),
            curriculum_id   TEXT        NOT NULL
                                        REFERENCES curricula(curriculum_id) ON DELETE RESTRICT,
            assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            assigned_by     UUID        REFERENCES teachers(teacher_id) ON DELETE SET NULL,
            PRIMARY KEY (school_id, grade)
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_gca_curriculum
        ON grade_curriculum_assignments(curriculum_id)
    """)

    # RLS — school_id-scoped.
    op.execute("ALTER TABLE grade_curriculum_assignments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE grade_curriculum_assignments FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON grade_curriculum_assignments")
    op.execute(f"""
        CREATE POLICY tenant_isolation ON grade_curriculum_assignments
        USING ({_SCHOOL_POLICY})
        WITH CHECK ({_SCHOOL_POLICY})
    """)


def downgrade() -> None:
    # ── grade_curriculum_assignments ──────────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON grade_curriculum_assignments")
    op.execute("ALTER TABLE grade_curriculum_assignments NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE grade_curriculum_assignments DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS grade_curriculum_assignments")

    # ── school_storage_quotas ─────────────────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON school_storage_quotas")
    op.execute("ALTER TABLE school_storage_quotas NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE school_storage_quotas DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS school_storage_quotas")

    # ── content_subject_versions: drop cost columns ───────────────────────────
    op.execute("""
        ALTER TABLE content_subject_versions
            DROP COLUMN IF EXISTS tokens_used,
            DROP COLUMN IF EXISTS cost_usd
    """)

    # ── curricula: drop retention columns ─────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_curricula_expires_at")
    op.execute("DROP INDEX IF EXISTS ix_curricula_retention_status")
    op.execute("""
        ALTER TABLE curricula
            DROP CONSTRAINT IF EXISTS curricula_retention_status_check,
            DROP COLUMN IF EXISTS renewed_at,
            DROP COLUMN IF EXISTS grace_until,
            DROP COLUMN IF EXISTS expires_at,
            DROP COLUMN IF EXISTS retention_status
    """)
