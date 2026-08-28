"""0065 — a unit's progress status counts the lesson, not only the quiz.

Issue #675, reported by Venki 2026-08-28. He worked the legend out himself:

    1. Completed    – quiz completed successfully
    2. Needs retry  – quiz not completed successfully
    3. In Progress  – completed the lesson but not taken the quiz
    4. Not started  – not started the lesson

and found that 3 never appears. His reading is the natural one, and it could
not be true: `mv_student_curriculum_progress` was built FROM progress_sessions
alone, so `in_progress` actually meant "has an ABANDONED QUIZ ATTEMPT", and
`not_started` covered units whose lesson had been read end to end.

It narrowed further after #579/#646. The lesson page used to create a phantom
session, which accidentally made the icon almost mean what the label said;
removing those sessions was right, and it quietly emptied a state that was
already mislabelled.

## What changes

The view now unions the keys of both tables, so a unit reached only by reading
its lesson gets a row:

    completed    a passed, completed session          (unchanged)
    needs_retry  a completed session, none passed     (unchanged)
    in_progress  an open session OR a lesson view     (was: open session only)
    not_started  neither                              (now genuinely untouched)

`attempts`, `best_score`, `best_pct` and `last_attempt_at` stay QUIZ figures —
a lesson view is not an attempt and must not inflate them. `attempts` is 0 for
a lesson-only row rather than NULL, since the reader renders it directly.

`subject` and `grade` are carried for compatibility (the one reader,
`get_progress_map`, takes both from `curriculum_units` instead) and fall back to
the curriculum for lesson-only rows, which have neither on `lesson_views`.

The unique index is recreated: REFRESH MATERIALIZED VIEW CONCURRENTLY requires
it, and dropping the view drops its indexes.

Revision ID: 0065
Revises: 0064
"""

from alembic import op

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None


_VIEW_SQL = """
CREATE MATERIALIZED VIEW mv_student_curriculum_progress AS
WITH touched AS (
    -- Every (student, unit, curriculum) the student has reached by ANY route.
    -- Previously only quiz sessions could put a row here, which is why a unit
    -- whose lesson had been read still read as "not started".
    SELECT student_id, unit_id, curriculum_id FROM progress_sessions
    UNION
    SELECT student_id, unit_id, curriculum_id FROM lesson_views
),
quiz AS (
    SELECT
        student_id, unit_id, curriculum_id,
        COUNT(*)                                                        AS attempts,
        MAX(score)                                                      AS best_score,
        MAX(score::float / NULLIF(total_questions, 0) * 100)            AS best_pct,
        MAX(CASE WHEN passed AND completed THEN 1 ELSE 0 END)           AS any_passed,
        MAX(CASE WHEN completed THEN 1 ELSE 0 END)                      AS any_completed,
        MAX(CASE WHEN NOT completed THEN 1 ELSE 0 END)                  AS any_open,
        MAX(ended_at)                                                   AS last_attempt_at,
        MAX(subject)                                                    AS subject,
        MAX(grade)                                                      AS grade
    FROM progress_sessions
    GROUP BY student_id, unit_id, curriculum_id
),
viewed AS (
    -- Aggregated to one row per unit BEFORE the join, so several views of one
    -- lesson cannot fan the row out.
    --
    -- ANY view row counts, including one still open. "In progress" literally
    -- means started and not finished, so a lesson opened and left is exactly
    -- that; requiring `ended_at` would instead mean "finished reading", which
    -- is a different claim and one we cannot actually observe.
    SELECT student_id, unit_id, curriculum_id, COUNT(*) AS views
    FROM lesson_views
    GROUP BY student_id, unit_id, curriculum_id
),
unit_meta AS (
    -- Aggregated for the same reason as `viewed`, and it is NOT hypothetical:
    -- nothing enforces uniqueness on (unit_id, curriculum_id) in
    -- curriculum_units, and a plain LEFT JOIN here duplicated the view's key,
    -- which the unique index below then rejected outright.
    SELECT unit_id, curriculum_id, MAX(subject) AS subject
    FROM curriculum_units
    GROUP BY unit_id, curriculum_id
)
SELECT
    t.student_id,
    t.unit_id,
    t.curriculum_id,
    COALESCE(q.subject, cu.subject)                                     AS subject,
    COALESCE(q.grade, c.grade)                                          AS grade,
    -- Quiz figures stay quiz figures: reading a lesson is not an attempt.
    COALESCE(q.attempts, 0)                                             AS attempts,
    q.best_score                                                        AS best_score,
    q.best_pct                                                          AS best_pct,
    CASE
        WHEN COALESCE(q.any_passed, 0) = 1    THEN 'completed'
        WHEN COALESCE(q.any_completed, 0) = 1 THEN 'needs_retry'
        WHEN COALESCE(q.any_open, 0) = 1
             OR v.views IS NOT NULL           THEN 'in_progress'
        ELSE 'not_started'
    END                                                                 AS status,
    q.last_attempt_at                                                   AS last_attempt_at
FROM touched t
LEFT JOIN quiz   q  ON q.student_id = t.student_id
                   AND q.unit_id = t.unit_id
                   AND q.curriculum_id = t.curriculum_id
LEFT JOIN viewed v  ON v.student_id = t.student_id
                   AND v.unit_id = t.unit_id
                   AND v.curriculum_id = t.curriculum_id
LEFT JOIN unit_meta cu ON cu.unit_id = t.unit_id
                      AND cu.curriculum_id = t.curriculum_id
-- curricula.curriculum_id is the primary key, so this one cannot fan out.
LEFT JOIN curricula c ON c.curriculum_id = t.curriculum_id
WITH DATA
"""

# The pre-0065 behaviour: status derived from progress_sessions alone.
#
# NOT a byte-for-byte restoration, and deliberately so. Migration 0003 grouped
# by (student, unit, curriculum, SUBJECT, GRADE) while indexing UNIQUE on only
# the first three. Any student whose sessions for one unit disagree on subject
# or grade therefore yields two rows with the same key, and the unique index
# cannot be built — which is not theoretical: it fails on the existing test
# fixtures the moment anything rebuilds the view.
#
# So the rollback restores the old MEANING (sessions only) with a sound key.
# Grouping on the three key columns is what 0065 does anyway; carrying that part
# backwards is the only way `downgrade` can succeed at all.
_OLD_VIEW_SQL = """
CREATE MATERIALIZED VIEW mv_student_curriculum_progress AS
SELECT
    s.student_id,
    s.unit_id,
    s.curriculum_id,
    MAX(s.subject)                                        AS subject,
    MAX(s.grade)                                          AS grade,
    COUNT(s.session_id)                                   AS attempts,
    MAX(s.score)                                          AS best_score,
    MAX(s.score::float / NULLIF(s.total_questions, 0) * 100) AS best_pct,
    CASE
        WHEN MAX(CASE WHEN s.passed AND s.completed THEN 1 ELSE 0 END) = 1 THEN 'completed'
        WHEN MAX(CASE WHEN s.completed THEN 1 ELSE 0 END) = 1            THEN 'needs_retry'
        WHEN MAX(CASE WHEN NOT s.completed THEN 1 ELSE 0 END) = 1        THEN 'in_progress'
        ELSE 'not_started'
    END AS status,
    MAX(s.ended_at) AS last_attempt_at
FROM progress_sessions s
GROUP BY s.student_id, s.unit_id, s.curriculum_id
WITH DATA
"""

_INDEXES = (
    """CREATE UNIQUE INDEX idx_mv_progress_pk
           ON mv_student_curriculum_progress(student_id, unit_id, curriculum_id)""",
    """CREATE INDEX idx_mv_progress_student
           ON mv_student_curriculum_progress(student_id, curriculum_id)""",
)


def upgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_student_curriculum_progress")
    op.execute(_VIEW_SQL)
    for stmt in _INDEXES:
        op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_student_curriculum_progress")
    op.execute(_OLD_VIEW_SQL)
    for stmt in _INDEXES:
        op.execute(stmt)
