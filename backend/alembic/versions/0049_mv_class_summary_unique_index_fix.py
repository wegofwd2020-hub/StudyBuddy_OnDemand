"""0049 — mv_class_summary: align unique index with GROUP BY (Issue #254 P2)

Migration 0010 created the mv_class_summary materialised view with a
GROUP BY of four columns:

    GROUP BY se.school_id, ps.curriculum_id, ps.unit_id, ps.subject

but a unique index over only three columns:

    CREATE UNIQUE INDEX mv_class_summary_pk
        ON mv_class_summary(school_id, curriculum_id, unit_id)

Whenever a (school_id, curriculum_id, unit_id) tuple has more than one
distinct `ps.subject` value, the MV produces multiple rows with the same
three-column key and `REFRESH MATERIALIZED VIEW` (non-CONCURRENTLY) fails
on index creation with `UniqueViolationError: could not create unique
index "mv_class_summary_pk"`.

This migration drops the 3-column index and recreates it over all four
GROUP BY columns so the index matches the authored grain.

Why this is the right fix (as opposed to dropping `subject` from the
GROUP BY):
  - No `SELECT FROM mv_class_summary` callers exist in the application
    source — only REFRESH callers.  So the shape is purely structural.
  - `subject` is a real dimension in the source (progress_sessions has
    its own subject column independent of curriculum_unit mapping).
    Keeping it at the unit level preserves information.

Effect on REFRESH:
  - Non-CONCURRENTLY refreshes continue to work.
  - CONCURRENT refreshes also work because the unique index still exists;
    only its columns changed.  Postgres requires at least one unique
    index for CONCURRENTLY refresh, and this migration keeps that
    invariant.

Revision ID: 0049
Revises: 0048
Create Date: 2026-04-23
"""

from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the mismatched 3-col unique index and recreate with 4 cols.
    op.execute("DROP INDEX IF EXISTS mv_class_summary_pk")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS mv_class_summary_pk
            ON mv_class_summary(school_id, curriculum_id, unit_id, subject)
        """
    )


def downgrade() -> None:
    # Restore the original 3-col index.  Note: downgrading on a schema
    # where real multi-subject rows exist will fail because the index
    # violates uniqueness.  That's expected — the whole point of this
    # migration is that the 3-col shape was wrong.
    op.execute("DROP INDEX IF EXISTS mv_class_summary_pk")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS mv_class_summary_pk
            ON mv_class_summary(school_id, curriculum_id, unit_id)
        """
    )
