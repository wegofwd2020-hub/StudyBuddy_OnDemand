"""0054 — backup_restore_requests table for Epic 15 Backup & Restore"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0054"
down_revision: str | None = "0053"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE backup_restore_requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            school_id UUID NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
            backup_id UUID REFERENCES curriculum_backups(id),
            requested_by UUID,
            status TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN (
                'submitted','acknowledged','dry_run','awaiting_school_confirm',
                'in_progress','completed','cancelled','failed'
            )),
            scope_type TEXT NOT NULL CHECK (scope_type IN ('grade','name','full')),
            scope_value TEXT,
            conflict_catalog_id UUID,
            side_by_side BOOLEAN NOT NULL DEFAULT FALSE,
            scheduled_at TIMESTAMPTZ,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("ALTER TABLE backup_restore_requests ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE backup_restore_requests FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON backup_restore_requests
            USING (
                school_id::text = current_setting('app.current_school_id', true)
                OR current_setting('app.current_school_id', true) = 'bypass'
            )
    """)
    op.execute("""
        CREATE INDEX idx_brr_school_id ON backup_restore_requests(school_id)
    """)
    op.execute("""
        CREATE INDEX idx_brr_status ON backup_restore_requests(status)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS backup_restore_requests")
