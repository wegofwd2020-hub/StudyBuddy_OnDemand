"""0047_curriculum_archived_state

Epic 10 L-3 — add `'archived'` to the `curricula.retention_status` CHECK
constraint and create a sweeper-friendly index.

The column itself (and `expires_at`, `grace_until`, `renewed_at`) already
exists from migration 0029. That migration's CHECK allowed
`{active, unavailable, purged}`; the new archive lifecycle (Epic 10)
needs a distinct `archived` state so the TTL sweeper (L-6) can find rows
without conflicting with the lesson-retention service's existing states.

The partial index `ix_curricula_archived_expires` is the one the sweeper
scans each night:

    SELECT curriculum_id
      FROM curricula
     WHERE retention_status = 'archived'
       AND expires_at < now();

Revision ID: 0047
Revises: 0046
"""

from alembic import op


revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE curricula DROP CONSTRAINT curricula_retention_status_check")
    op.execute(
        "ALTER TABLE curricula ADD CONSTRAINT curricula_retention_status_check "
        "CHECK (retention_status = ANY (ARRAY["
        "'active'::text, 'unavailable'::text, 'purged'::text, 'archived'::text]))"
    )
    op.execute(
        "CREATE INDEX ix_curricula_archived_expires "
        "ON curricula (expires_at) "
        "WHERE retention_status = 'archived'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_curricula_archived_expires")
    op.execute("ALTER TABLE curricula DROP CONSTRAINT curricula_retention_status_check")
    op.execute(
        "ALTER TABLE curricula ADD CONSTRAINT curricula_retention_status_check "
        "CHECK (retention_status = ANY (ARRAY["
        "'active'::text, 'unavailable'::text, 'purged'::text]))"
    )
