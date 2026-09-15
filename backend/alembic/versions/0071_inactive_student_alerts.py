"""0071 — the inactive-student alert gets a key of its own.

Closes the live half of #735. `report_alert_settings` has offered four
thresholds since migration 0010 and the evaluator read exactly one of them.
`inactive_days_threshold` was the worst of the three dead ones: it is
`SELECT`ed by `evaluate_report_alerts_task` and then never referenced, so a
school admin could set it, see it persist, and watch nothing happen.

## Why another index rather than reuse

`inactive_students` is keyed on a STUDENT and carries no unit at all, which is
precisely the case migration 0066's docstring warned about: keyed through
`(school_id, alert_type, details->>'unit_id')`, every row of this type would
key on NULL, and Postgres treats NULLs in a unique index as distinct — so the
daily task would append one row per student per day, forever, exactly as
pass_rate_breach did before 0066.

Migration 0070 already narrowed that index to `alert_type = 'pass_rate_breach'`
and gave the per-student stuck alert its own. This continues that shape: one
index per alert type, each scoped to its own `alert_type`. A type does not get
to borrow another's key, because the key IS the definition of "the same alert".

## Not a settings-column drop

`score_drop_threshold` and `feedback_count_threshold` stop being offered in the
API and the settings form in this change, but their columns stay. Dropping them
would be irreversible for the sake of tidiness, and they are NOT NULL with
defaults, so leaving them costs nothing and keeps the door open if either ever
gets a definition worth implementing.

Revision ID: 0071
Revises: 0070
"""

from alembic import op

revision = "0071"
down_revision = "0070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_report_alerts_open_inactive
            ON report_alerts (school_id, COALESCE(details->>'student_id', ''))
            WHERE alert_type = 'inactive_students'
              AND NOT acknowledged AND resolved_at IS NULL
        """
    )


def downgrade() -> None:
    # Rows first: without the index they are merely un-deduplicated, but leaving
    # a type behind whose key no longer exists is how 0066's orphan state
    # happened (pitfall #27). These are derived operational rows, recomputed on
    # the next nightly run, and referenced by nothing.
    op.execute("DELETE FROM report_alerts WHERE alert_type = 'inactive_students'")
    op.execute("DROP INDEX IF EXISTS uq_report_alerts_open_inactive")
