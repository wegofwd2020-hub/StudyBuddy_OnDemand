"""
backend/alembic/versions/0007_phase8_school_curriculum.py

Phase 8 schema additions:
  curricula        — add source_type, status, restrict_access, created_by, activated_at
                     (table already exists from 0002; alter to add Phase 8 columns)
  curriculum_units — add unit_name, objectives, lab_description, sequence, content_status
                     (table already exists from 0002; alter to add Phase 8 columns)

Note: schools and teachers tables already exist from Phase 1 (0001).
      curricula and curriculum_units exist from Phase 2 (0002) with a simpler schema.
"""

revision = "0007"
down_revision = "0006"

from alembic import op


def upgrade() -> None:
    # ── curricula: add Phase 8 columns ────────────────────────────────────────
    op.execute("""
        ALTER TABLE curricula
            ADD COLUMN IF NOT EXISTS source_type text NOT NULL DEFAULT 'default',
            ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active',
            ADD COLUMN IF NOT EXISTS restrict_access boolean NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS created_by uuid REFERENCES teachers(teacher_id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS activated_at timestamptz
    """)

    # Add CHECK constraints (PostgreSQL allows adding named constraints)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'curricula_source_type_check'
            ) THEN
                ALTER TABLE curricula
                    ADD CONSTRAINT curricula_source_type_check
                    CHECK (source_type IN ('default', 'xlsx_upload', 'ui_form'));
            END IF;
        END $$
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'curricula_status_check'
            ) THEN
                ALTER TABLE curricula
                    ADD CONSTRAINT curricula_status_check
                    CHECK (status IN ('draft', 'building', 'active', 'archived', 'failed'));
            END IF;
        END $$
    """)

    # ── curriculum_units: add Phase 8 columns ─────────────────────────────────
    op.execute("""
        ALTER TABLE curriculum_units
            ADD COLUMN IF NOT EXISTS unit_name text,
            ADD COLUMN IF NOT EXISTS objectives text[] NOT NULL DEFAULT '{}',
            ADD COLUMN IF NOT EXISTS lab_description text,
            ADD COLUMN IF NOT EXISTS sequence int NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS content_status text NOT NULL DEFAULT 'pending'
    """)

    # Make old columns nullable to avoid conflicts with new insert patterns.
    op.execute("ALTER TABLE curriculum_units ALTER COLUMN title DROP NOT NULL")
    op.execute("ALTER TABLE curriculum_units ALTER COLUMN description DROP NOT NULL")

    # Backfill unit_name from title where title exists
    op.execute("""
        UPDATE curriculum_units
        SET unit_name = title
        WHERE unit_name IS NULL AND title IS NOT NULL
    """)

    # Make unit_name NOT NULL after backfill (set a default for any remaining NULLs)
    op.execute("""
        UPDATE curriculum_units SET unit_name = unit_id WHERE unit_name IS NULL
    """)
    op.execute("""
        ALTER TABLE curriculum_units ALTER COLUMN unit_name SET NOT NULL
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'curriculum_units_content_status_check'
            ) THEN
                ALTER TABLE curriculum_units
                    ADD CONSTRAINT curriculum_units_content_status_check
                    CHECK (content_status IN ('pending', 'built', 'failed'));
            END IF;
        END $$
    """)

    # ── New indexes ───────────────────────────────────────────────────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_curricula_school_grade_year
        ON curricula(school_id, grade, year)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_curricula_status
        ON curricula(status)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_curriculum_units_curriculum_id
        ON curriculum_units(curriculum_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_curriculum_units_curriculum_id")
    op.execute("DROP INDEX IF EXISTS ix_curricula_status")
    op.execute("DROP INDEX IF EXISTS ix_curricula_school_grade_year")
    op.execute("ALTER TABLE curriculum_units DROP COLUMN IF EXISTS content_status")
    op.execute("ALTER TABLE curriculum_units DROP COLUMN IF EXISTS sequence")
    op.execute("ALTER TABLE curriculum_units DROP COLUMN IF EXISTS lab_description")
    op.execute("ALTER TABLE curriculum_units DROP COLUMN IF EXISTS objectives")
    op.execute("ALTER TABLE curriculum_units DROP COLUMN IF EXISTS unit_name")
    op.execute("ALTER TABLE curricula DROP COLUMN IF EXISTS activated_at")
    op.execute("ALTER TABLE curricula DROP COLUMN IF EXISTS created_by")
    op.execute("ALTER TABLE curricula DROP COLUMN IF EXISTS restrict_access")
    op.execute("ALTER TABLE curricula DROP COLUMN IF EXISTS status")
    op.execute("ALTER TABLE curricula DROP COLUMN IF EXISTS source_type")
