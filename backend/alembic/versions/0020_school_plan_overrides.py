"""
0020_school_plan_overrides

Revision ID: 0020
Revises: 0019
Create Date: 2026-04-01

Adds school_plan_overrides table for per-school limit overrides.

Design:
  - One row per school (PRIMARY KEY on school_id).
  - All limit columns are nullable — NULL means "use plan default from settings".
  - set_by_admin_id: audit trail; which super_admin set the override.
  - override_reason: required at application layer, nullable here for flexibility.

Resolution order (enforced in application code, not DB):
  1. Per-school override (this table)
  2. Plan defaults (settings.py env vars)

Only super_admin role can write to this table. school_admin role is read-only.
"""

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS school_plan_overrides (
            school_id        uuid        PRIMARY KEY
                                         REFERENCES schools(school_id) ON DELETE CASCADE,
            max_students     int,
            max_teachers     int,
            pipeline_quota   int,
            override_reason  text,
            set_by_admin_id  uuid        REFERENCES admin_users(admin_user_id) ON DELETE SET NULL,
            set_at           timestamptz NOT NULL DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS school_plan_overrides")
