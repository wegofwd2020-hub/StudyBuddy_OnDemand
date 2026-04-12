"""0042_demo_leads

Demo lead management tables for Epic 7 — Self-Serve Demo System (Option C).

  demo_leads       — tracks all demo tour requests (pending / approved / rejected)
  demo_geo_blocks  — countries blocked from requesting a demo (IP-country check)

The plat_admin role is added to the admin_users role CHECK constraint so that
a Platform Administrator account can be provisioned via seed_super_admin.py.

Revision ID: 0042
Revises: 0041
"""

from alembic import op
import sqlalchemy as sa

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extend admin_role ENUM to include plat_admin ──────────────────────
    # PostgreSQL requires the new label to be added before any rows use it.
    op.execute("ALTER TYPE admin_role ADD VALUE IF NOT EXISTS 'plat_admin'")

    # ── 2. demo_leads ─────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE demo_leads (
            lead_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name             TEXT NOT NULL,
            email            TEXT NOT NULL,
            school_org       TEXT NOT NULL,
            ip_country       CHAR(2),
            ip_address       TEXT,
            status           TEXT NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'approved', 'rejected')),
            demo_token       TEXT,
            token_expires_at TIMESTAMPTZ,
            approved_by      UUID REFERENCES admin_users(admin_user_id) ON DELETE SET NULL,
            approved_at      TIMESTAMPTZ,
            rejected_reason  TEXT,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX demo_leads_email_idx  ON demo_leads(email)")
    op.execute("CREATE INDEX demo_leads_status_idx ON demo_leads(status)")
    op.execute("CREATE INDEX demo_leads_created_idx ON demo_leads(created_at DESC)")

    # ── 3. demo_geo_blocks ────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE demo_geo_blocks (
            country_code CHAR(2) PRIMARY KEY,
            country_name TEXT,
            added_by     UUID REFERENCES admin_users(admin_user_id) ON DELETE SET NULL,
            added_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_geo_blocks")
    op.execute("DROP TABLE IF EXISTS demo_leads")
    # Note: PostgreSQL does not support removing enum labels — downgrade leaves
    # 'plat_admin' in the admin_role enum but removes all tables that use it.
