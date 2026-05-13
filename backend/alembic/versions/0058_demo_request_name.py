"""0058 — name column on demo_requests for the test-run admin view.

The /demo/test-run/request endpoint captures the visitor's name so the
super-admin "Test Runs" page can display who made each request. Existing
/demo/request submissions leave this NULL (they never collected a name).

Nullable + no default → backwards-compatible; old code paths keep working.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0058"
down_revision: str | None = "0057"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE demo_requests ADD COLUMN IF NOT EXISTS name TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE demo_requests DROP COLUMN IF EXISTS name")
