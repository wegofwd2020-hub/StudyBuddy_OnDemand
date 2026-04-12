"""0041 — Help system: help_interactions analytics table

Deliver-4: log every POST /help/ask call and record thumbs-up / thumbs-down
feedback so unhelpful answers can be identified and library chunks improved.

New table
─────────
help_interactions
  interaction_id  UUID PK DEFAULT gen_random_uuid()
  persona         TEXT NOT NULL           school_admin | teacher | student
  page            TEXT                    current route at ask time (nullable)
  question        TEXT NOT NULL           question text (max 500 chars, validated)
  response_title  TEXT                    title from the Haiku response
  sources         TEXT[]                  headings of retrieved chunks used
  helpful         BOOLEAN                 NULL = no feedback yet
                                          TRUE  = thumbs up
                                          FALSE = thumbs down
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()

No RLS — help_interactions is internal analytics data, not school-scoped.
No FK constraints — interactions are append-only audit records.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS help_interactions (
            interaction_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            persona         TEXT        NOT NULL,
            page            TEXT,
            question        TEXT        NOT NULL,
            response_title  TEXT,
            sources         TEXT[],
            helpful         BOOLEAN,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    # Index for admin queries: newest first, filter by helpful status.
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_help_interactions_created_at
        ON help_interactions (created_at DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_help_interactions_helpful
        ON help_interactions (helpful)
        WHERE helpful IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS help_interactions")
