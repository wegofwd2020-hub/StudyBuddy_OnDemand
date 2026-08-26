"""0063 — record which kind of content a lesson_view row represents.

Issue #569. Tutorial and Experiment pages never recorded a view at all, so time
spent in them counted as zero everywhere: the student's "Time spent", the school
admin's per-unit Time column, "Lessons viewed", and the struggle / health / at-risk
logic that reads the same tables to recommend interventions.

The table already carried `experiment_viewed` — written by the end endpoint,
never set by any page, and never read by any report. This adds the matching
`tutorial_viewed` so the three content types are distinguishable once the pages
start recording.

Deliberately additive: no existing read changes meaning here. Every current row
is a lesson view, which is exactly what `FALSE` on both flags means, so the
backfill is the default and no data migration is needed.

Revision ID: 0063
Revises: 0062
"""

from alembic import op

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE lesson_views
        ADD COLUMN IF NOT EXISTS tutorial_viewed BOOLEAN NOT NULL DEFAULT FALSE
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE lesson_views DROP COLUMN IF EXISTS tutorial_viewed")
