"""0066 — one OPEN report alert per unit, and let a cleared breach close itself.

Reported by Venki 2026-08-31: the Alert Inbox showed "156 new", every entry a
`pass_rate_breach`, and passing a quiz changed nothing. Two separate defects sat
behind that.

## Defect 1 — a deduplication that has never once run

`evaluate_report_alerts_task` inserts with `ON CONFLICT DO NOTHING`, which reads
as "raise this alert at most once". `report_alerts` has no unique constraint —
only the `alert_id` primary key — so there is nothing for a row to conflict ON,
every insert succeeds, and the clause is decoration.

The task runs daily at 06:00 UTC, so a unit that keeps breaching accumulates one
duplicate row per day, forever. Measured on the demo before this migration:

    294 pass_rate_breach rows across 13 distinct units
    G8-TECH-001 alone: 69 rows, byte-identical (one distinct pass_rate)

That is the "156 new" badge: not 156 problems, one problem counted 156 times.

## Defect 2 — alerts are raised but never withdrawn

Nothing retracts an alert when the condition clears. A unit whose pass rate
recovers keeps its alert until a human dismisses it by hand, so the inbox
describes the past rather than the present — exactly what "I passed but the
alerts do not reflect it" means. `acknowledged` cannot express this: it records
that a *teacher dismissed* the alert, and conflating "a person judged this" with
"the system observed the breach end" loses the distinction that makes the inbox
trustworthy. Hence a separate `resolved_at`.

## What this migration does

1. Adds `resolved_at TIMESTAMPTZ NULL` — set by the evaluator when a previously
   breaching unit no longer breaches. NULL means still open.
2. Collapses the existing duplicates, keeping the EARLIEST row per
   (school, alert_type, unit) among those still open. Earliest, not latest, so
   "breaching since" survives the cleanup; the evaluator refreshes the pass rate
   on the surviving row from now on.
3. Adds the partial unique index the `ON CONFLICT` clause always assumed:
   one OPEN alert per (school, alert_type, unit).

## The index is partial on purpose

`WHERE NOT acknowledged AND resolved_at IS NULL` scopes uniqueness to OPEN
alerts. A unit that breaches, is dismissed, and later breaches again must be able
to raise a fresh alert — a permanent unique index would silence the second one,
which is a worse bug than the one being fixed here.

## A trap left for whoever adds the next alert type

The index keys on `details->>'unit_id'`. `pass_rate_breach` is the only type
written today (`auth/tasks.py`), and it always carries a unit_id. A future alert
type WITHOUT one yields NULL, and Postgres treats NULLs in a unique index as
distinct — so that type would silently duplicate exactly as pass_rate_breach did.
Anyone adding an alert type keyed on something else must extend this index, not
assume it covers them.

## Downgrade is lossy, deliberately

The duplicate rows deleted in step 2 are not recoverable. They are redundant
copies of a derived operational signal — recomputed daily from
`progress_sessions` — not educational records, and nothing references them by id.
The downgrade restores the schema, not the duplicates.

Revision ID: 0066
Revises: 0065
"""

from alembic import op

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE report_alerts ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ")

    # Collapse duplicates BEFORE the unique index, or its creation fails on the
    # existing data. Keep the earliest open row per (school, type, unit) so the
    # "breaching since" timestamp is preserved rather than reset to today.
    op.execute(
        """
        DELETE FROM report_alerts a
        USING report_alerts keep
        WHERE a.school_id  = keep.school_id
          AND a.alert_type = keep.alert_type
          AND a.details->>'unit_id' IS NOT NULL
          AND a.details->>'unit_id' = keep.details->>'unit_id'
          AND NOT a.acknowledged     AND a.resolved_at    IS NULL
          AND NOT keep.acknowledged  AND keep.resolved_at IS NULL
          AND (keep.triggered_at, keep.alert_id) < (a.triggered_at, a.alert_id)
        """
    )

    # The constraint `ON CONFLICT DO NOTHING` has always been written against.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_report_alerts_open_unit
            ON report_alerts (school_id, alert_type, (details->>'unit_id'))
            WHERE NOT acknowledged AND resolved_at IS NULL
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_alerts_open
            ON report_alerts (school_id, resolved_at)
            WHERE resolved_at IS NULL
        """
    )


def downgrade() -> None:
    # Schema only. The duplicate rows removed on upgrade are not restored --
    # see the module docstring.
    op.execute("DROP INDEX IF EXISTS idx_alerts_open")
    op.execute("DROP INDEX IF EXISTS uq_report_alerts_open_unit")
    op.execute("ALTER TABLE report_alerts DROP COLUMN IF EXISTS resolved_at")
