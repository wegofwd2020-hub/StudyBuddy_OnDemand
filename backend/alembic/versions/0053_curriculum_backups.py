"""0053 — curriculum_backups table for Epic 15 Backup & Restore"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0053"
down_revision: str | None = "0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE curriculum_backups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            school_id UUID NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
            label TEXT NOT NULL DEFAULT '',
            scope_type TEXT NOT NULL CHECK (scope_type IN ('grade','name','full')),
            scope_value TEXT,
            storage_path TEXT NOT NULL DEFAULT '',
            manifest_json JSONB,
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed')),
            triggered_by UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ,
            file_count INT NOT NULL DEFAULT 0,
            total_bytes BIGINT NOT NULL DEFAULT 0
        )
    """)
    op.execute("ALTER TABLE curriculum_backups ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE curriculum_backups FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON curriculum_backups
            USING (
                school_id::text = current_setting('app.current_school_id', true)
                OR current_setting('app.current_school_id', true) = 'bypass'
            )
    """)
    op.execute("""
        CREATE INDEX idx_curriculum_backups_school_id
            ON curriculum_backups(school_id)
    """)
    op.execute("""
        CREATE INDEX idx_curriculum_backups_created_at
            ON curriculum_backups(school_id, created_at DESC)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS curriculum_backups")
