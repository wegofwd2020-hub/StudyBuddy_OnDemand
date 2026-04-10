"""
0030_content_warning_acks

Revision ID: 0030
Revises: 0029
Create Date: 2026-04-10

AlexJS warning acknowledgements (GitHub issue #76).

Changes
-------

content_warning_acks  NEW TABLE
  Tracks per-warning acknowledgement state so the approve flow can be gated
  until every AlexJS warning has been either acknowledged or marked
  false-positive by a reviewer.

  Compound key: (version_id, unit_id, content_type, warning_index) is UNIQUE
  so upsert on re-acknowledge is safe (idempotent).

  warning_index is the 0-based position of the warning in the
  alex_warnings_detail array stored in the unit's meta.json.

Also adds alex_warnings_detail_by_type JSONB column to meta.json (pipeline
only — no DB column needed, stored on filesystem).
"""

from alembic import op
import sqlalchemy as sa

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE content_warning_acks (
            ack_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            version_id      UUID        NOT NULL
                                REFERENCES content_subject_versions(version_id)
                                ON DELETE CASCADE,
            unit_id         TEXT        NOT NULL,
            content_type    TEXT        NOT NULL,
            warning_index   INT         NOT NULL,
            is_false_positive BOOLEAN   NOT NULL DEFAULT FALSE,
            acknowledged_by UUID        NOT NULL
                                REFERENCES admin_users(admin_user_id),
            acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (version_id, unit_id, content_type, warning_index)
        )
    """)
    op.execute(
        "CREATE INDEX ix_content_warning_acks_version ON content_warning_acks (version_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS content_warning_acks")
