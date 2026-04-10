"""0032 — build_allowance: track curriculum build quota per school subscription year

Adds three columns to school_storage_quotas so the platform can enforce
Option A: absorbed into plan with a hard annual allowance.

  builds_included  — how many grade builds the plan covers per year.
                     Stamped from plan defaults at subscription activation time.
                     -1 = unlimited (Enterprise).
  builds_used      — cumulative grade builds consumed in the current period.
                     Incremented each time a school-scoped pipeline job completes.
  builds_period_end — when the current allowance resets (1 year from activation).

A Celery Beat task (future: feat/q3-b-pay-per-build) will reset builds_used
and roll builds_period_end forward annually.

Revision ID: 0032
Revises: 0031
Create Date: 2026-04-10
"""

from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE school_storage_quotas
            ADD COLUMN IF NOT EXISTS builds_included  INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS builds_used      INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS builds_period_end TIMESTAMPTZ
        """
    )
    op.execute(
        """
        ALTER TABLE school_storage_quotas
            ADD CONSTRAINT school_storage_quotas_builds_included_check
                CHECK (builds_included >= -1),
            ADD CONSTRAINT school_storage_quotas_builds_used_check
                CHECK (builds_used >= 0)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE school_storage_quotas
            DROP CONSTRAINT IF EXISTS school_storage_quotas_builds_used_check,
            DROP CONSTRAINT IF EXISTS school_storage_quotas_builds_included_check,
            DROP COLUMN IF EXISTS builds_period_end,
            DROP COLUMN IF EXISTS builds_used,
            DROP COLUMN IF EXISTS builds_included
        """
    )
