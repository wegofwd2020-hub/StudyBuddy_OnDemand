"""0033 — build_credits_balance: credit rollover balance for curriculum builds

Adds builds_credits_balance to school_storage_quotas for Option C (credit bundles).

Credits are purchased as one-time Stripe payments in bundles of 3/10/25 and are
consumed when a school triggers a pipeline build after their plan allowance is
exhausted.  Credits roll over — they never expire.

Flow:
  1. School exhausts plan build allowance (builds_used >= builds_included).
  2. consume_build() deducts 1 from builds_credits_balance instead of failing.
  3. If credits also = 0, the pipeline trigger endpoint returns 402.
  4. School purchases a credit bundle via POST /schools/{id}/pipeline/credits-checkout.
  5. checkout.session.completed webhook increments builds_credits_balance.

Revision ID: 0033
Revises: 0032
Create Date: 2026-04-10
"""

from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE school_storage_quotas
            ADD COLUMN IF NOT EXISTS builds_credits_balance INTEGER NOT NULL DEFAULT 0
        """
    )
    op.execute(
        """
        ALTER TABLE school_storage_quotas
            ADD CONSTRAINT school_storage_quotas_builds_credits_check
                CHECK (builds_credits_balance >= 0)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE school_storage_quotas
            DROP CONSTRAINT IF EXISTS school_storage_quotas_builds_credits_check,
            DROP COLUMN IF EXISTS builds_credits_balance
        """
    )
