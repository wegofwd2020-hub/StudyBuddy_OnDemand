"""0070 — a student who never passes a unit produces a signal.

Reported by Venki 2026-09-02, against a student card reading
`Attempt #11 · Score 3/8`: "Why was this not shown in the Alerts section?"

It could not have been. Every alert the platform raises is UNIT-grained —
`evaluate_report_alerts_task` runs `GROUP BY ps.unit_id`, and `student_id`
survives only inside `COUNT(DISTINCT …)`, consumed by the aggregate. The
sentence the system can produce is "unit X is hard for this school". There has
never been a grammar for "student Y is not getting through unit X".

Both sides of that pass-rate ratio also filter `attempt_number = 1`, so attempts
2..N are invisible to it. A student can fail ten times after passing once and
contribute a "pass" forever.

## What this migration does NOT try to catch

Not the reported history itself. That student failed attempt 1, PASSED attempts
2-10, then failed attempt 11. One slip after nine passes is revision, and a
threshold low enough to fire on it fires on everyone who ever revises — noise, in
an inbox that migration 0066 just cut from 294 rows to 13.

The genuinely missing signal is the adjacent one, and it is the one this adds:
repeated completed attempts with NO pass, ever.

## The index split, and why the shared one had to be narrowed

Migration 0066's docstring left a warning for whoever added the next alert type:
`uq_report_alerts_open_unit` keys on `(school_id, alert_type, details->>'unit_id')`,
and a type carrying no unit_id would yield NULL — distinct in a unique index — and
silently duplicate exactly as pass_rate_breach did.

This type carries a unit_id, so it hits the opposite failure. Keyed on unit alone,
TWO students stuck on the SAME unit collide: the second insert `DO UPDATE`s the
first and one of them is never reported. Suppression, not duplication.

Widening the shared index to include `student_id` fixes that and breaks the other
half — `pass_rate_breach` has no `student_id`, so every row keys on NULL, NULLs
are distinct, and the 69-duplicates-per-unit bug comes straight back.

Neither key works for both types, so there is one index per type, each scoped to
its own `alert_type`. A third type gets its own; it does not get to borrow one.

## Downgrade deletes rows before restoring the old index

Deliberate, and ordered. The old type-blind index cannot be built against data
containing two students stuck on one unit, so those rows must go first (the same
shape as 0060's `source_type='admin_authored'` cleanup).

Lossy, but not of anything owed to anyone: these are derived operational rows,
recomputed from `progress_sessions` on the next nightly run, and nothing
references them by id. They are not educational records.

Revision ID: 0070
Revises: 0069
"""

from alembic import op

revision = "0070"
down_revision = "0069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ge=2 is enforced at the schema level: one failed attempt is a bad day, not
    # a pattern. The default is deliberately not 1.
    op.execute(
        """
        ALTER TABLE report_alert_settings
            ADD COLUMN IF NOT EXISTS stuck_attempts_threshold INT NOT NULL DEFAULT 3
        """
    )

    # Narrow the shared index to the single type it was ever written for, then
    # give the new type its own. See the module docstring for why neither key
    # can serve both.
    op.execute("DROP INDEX IF EXISTS uq_report_alerts_open_unit")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_report_alerts_open_unit
            ON report_alerts (school_id, (details->>'unit_id'))
            WHERE alert_type = 'pass_rate_breach'
              AND NOT acknowledged AND resolved_at IS NULL
        """
    )

    # COALESCE rather than the bare expressions: both keys are guaranteed present
    # for this type, but a malformed insert that dropped one would otherwise key
    # on NULL and duplicate silently instead of failing loudly.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_report_alerts_open_stuck
            ON report_alerts (school_id,
                              COALESCE(details->>'student_id', ''),
                              COALESCE(details->>'unit_id', ''))
            WHERE alert_type = 'student_stuck_on_unit'
              AND NOT acknowledged AND resolved_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_report_alerts_open_stuck")

    # Before the type-blind index can be rebuilt. Two students stuck on one unit
    # is a legal state under the index this drops and an illegal one under the
    # index it restores.
    op.execute("DELETE FROM report_alerts WHERE alert_type = 'student_stuck_on_unit'")

    op.execute("DROP INDEX IF EXISTS uq_report_alerts_open_unit")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_report_alerts_open_unit
            ON report_alerts (school_id, alert_type, (details->>'unit_id'))
            WHERE NOT acknowledged AND resolved_at IS NULL
        """
    )

    op.execute(
        """
        ALTER TABLE report_alert_settings
            DROP COLUMN IF EXISTS stuck_attempts_threshold
        """
    )
