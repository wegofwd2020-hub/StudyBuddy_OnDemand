"""0043_provider_column

Epic 1 — Multi-Provider LLM Pipeline (F-2)

Adds `provider` column to:
  - content_subject_versions  — which LLM generated this version
  - pipeline_jobs             — which LLM ran this job

Default is 'anthropic' (the only provider before this migration).
Existing rows are backfilled with this default.

Revision ID: 0043
Revises: 0042
"""

from alembic import op
import sqlalchemy as sa

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None

_VALID_PROVIDERS = ("anthropic", "openai", "google", "school_upload")


def upgrade() -> None:
    # ── content_subject_versions ──────────────────────────────────────────────
    op.add_column(
        "content_subject_versions",
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            server_default="anthropic",
        ),
    )
    op.execute(
        "ALTER TABLE content_subject_versions "
        "ADD CONSTRAINT csv_provider_check "
        "CHECK (provider IN ('anthropic', 'openai', 'google', 'school_upload'))"
    )

    # ── pipeline_jobs ─────────────────────────────────────────────────────────
    op.add_column(
        "pipeline_jobs",
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            server_default="anthropic",
        ),
    )
    op.execute(
        "ALTER TABLE pipeline_jobs "
        "ADD CONSTRAINT pj_provider_check "
        "CHECK (provider IN ('anthropic', 'openai', 'google', 'school_upload'))"
    )

    # ── school_llm_config (F-5 — school-level provider preferences) ───────────
    op.execute(
        """
        CREATE TABLE school_llm_config (
            school_id               UUID        PRIMARY KEY
                                                REFERENCES schools(school_id) ON DELETE CASCADE,
            allowed_providers       JSONB       NOT NULL DEFAULT '["anthropic"]',
            default_provider        VARCHAR(50) NOT NULL DEFAULT 'anthropic',
            comparison_enabled      BOOLEAN     NOT NULL DEFAULT FALSE,
            dpa_acknowledged_at     JSONB       NOT NULL DEFAULT '{}',
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT slc_default_provider_check
                CHECK (default_provider IN ('anthropic', 'openai', 'google'))
        )
        """
    )
    op.execute(
        "ALTER TABLE school_llm_config ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY school_llm_config_isolation ON school_llm_config
            USING (
                current_setting('app.current_school_id', TRUE) = 'bypass'
                OR school_id::TEXT = current_setting('app.current_school_id', TRUE)
            )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS school_llm_config")
    op.execute(
        "ALTER TABLE pipeline_jobs DROP CONSTRAINT IF EXISTS pj_provider_check"
    )
    op.drop_column("pipeline_jobs", "provider")
    op.execute(
        "ALTER TABLE content_subject_versions DROP CONSTRAINT IF EXISTS csv_provider_check"
    )
    op.drop_column("content_subject_versions", "provider")
