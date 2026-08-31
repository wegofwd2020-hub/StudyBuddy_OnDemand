"""
backend/src/reports/service.py

Phase 11 teacher reporting dashboard — business logic.

All service functions query underlying tables directly for correctness and
testability. Materialized views (mv_class_summary, mv_student_progress,
mv_feedback_summary) exist as a performance layer — refresh them via
refresh_materialized_views() for production warm reads.

Shared helper:
  _enrolled_ids()       — active enrolled student IDs for a school
  _period_start()       — convert period string to UTC datetime
  _health_tier()        — classify a unit by pass rate + avg attempts
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import asyncpg

from src.core.subjects import display_subject, resolve_subject_labels
from src.utils.logger import get_logger

log = get_logger("reports")

_STRUGGLE_PASS = 50.0  # below this → struggling (or watch)
_HEALTHY_PASS = 70.0  # at or above this → healthy
_STRUGGLE_ATT = 2.0  # above this → struggling
_HEALTHY_ATT = 1.5  # at or below this → healthy


# ── Helpers ───────────────────────────────────────────────────────────────────


def _period_start(period: str) -> datetime:
    now = datetime.now(UTC)
    if period == "30d":
        return now - timedelta(days=30)
    if period == "term":
        year = now.year if now.month >= 9 else now.year - 1
        return datetime(year, 9, 1, tzinfo=UTC)
    return now - timedelta(days=7)  # default: 7d


def _trend_weeks(period: str) -> int:
    return {"4w": 4, "12w": 12, "term": 16}.get(period, 4)


async def total_units_by_student(
    pool,
    redis,
    students: list[dict],
    school_id: str,
) -> dict[str, int]:
    """Map `student_id` -> how many units they are actually served, across every package.

    Fixes #638. Both report sites previously counted units with

        WHERE c.grade = <student grade> AND c.is_default

    which sums EVERY default curriculum at that grade. Since Epic 8 a grade has
    one default per stream, so a Grade 11 student was measured against STEM +
    Commerce + Humanities + Science together: 19 + 6 + 2 + 29 = 56. Grades with a
    single curriculum (8, 10) read correctly by accident, which is why it
    survived — the bug is invisible in exactly the grades most testing uses.

    The denominator now comes from `resolve_curriculum_ids()`, the same
    resolution that decides which content the student is served (school-owned →
    classroom packages → `default-{year}-g{grade}`), summed across every package
    because they are additive (#651).

    Deliberately NOT re-expressed as SQL. Re-deriving the curriculum with a
    simpler query is pitfall #31 exactly: `get_curriculum_tree` did that and
    quietly served stream students another stream's subjects. One resolver,
    called by everything, is the point — a second copy drifts silently and the
    symptom appears somewhere else entirely.

    Resolution is Redis-cached per student, and unit counts are fetched in one
    query for the distinct curricula rather than per student.
    """
    from src.content.service import resolve_curriculum_ids

    if not students:
        return {}

    # A classroom's packages are ADDITIVE (#651), so a student's denominator is
    # the sum across every package — not whichever one an arbitrary pick
    # returned. Getting this wrong is how "5/56" happened twice already
    # (#638 summed unrelated streams, #650 counted a fork holding no units).
    resolved: dict[str, list[str]] = {}
    for row in students:
        sid = str(row["student_id"])
        resolved[sid] = await resolve_curriculum_ids(
            sid,
            row["grade"],
            pool,
            redis,
            school_id=school_id,
        )

    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        # Count against the curriculum that actually HOLDS the units.
        #
        # A school FORK carries no rows in `curriculum_units` — they live under
        # its `source_curriculum_id`, which is why content serving swaps
        # fork -> source before reading (resolve_content_curriculum). Counting
        # the fork directly returns zero, so a student on a forked curriculum
        # went from a wrong denominator to an impossible one. Caught on the demo
        # minutes after #638 shipped: Venky_Gr11 resolves through a classroom
        # package to a fork with 0 own units and 20 under default-2026-g8.
        counts = await conn.fetch(
            """
            SELECT c.curriculum_id,
                   COALESCE(
                       -- the curriculum's own units, if it has any ...
                       NULLIF((SELECT COUNT(*) FROM curriculum_units own
                               WHERE own.curriculum_id = c.curriculum_id), 0),
                       -- ... otherwise the source it was forked from
                       (SELECT COUNT(*) FROM curriculum_units src
                        WHERE src.curriculum_id = c.source_curriculum_id),
                       0
                   ) AS units
            FROM curricula c
            WHERE c.curriculum_id = ANY($1::text[])
            """,
            sorted({cid for ids in resolved.values() for cid in ids}),
        )
    by_curriculum = {r["curriculum_id"]: r["units"] for r in counts}
    return {sid: sum(by_curriculum.get(cid, 0) for cid in ids) for sid, ids in resolved.items()}


async def cohort_unit_ids(
    conn: asyncpg.Connection,
    pool,
    redis,
    school_id: str,
    allowed_grades: list[int] | None = None,
) -> set[str]:
    """Every unit in the curricula this school's students are actually served.

    The catalog that "no activity" has to be measured against (#590). Both
    metrics that used the name were ungrounded: the overview compared two
    activity sets to each other, and curriculum health only ever saw units that
    already had a session — so the report meant to surface coverage gaps was
    blind to the units nobody had opened.

    Resolution goes through the shared resolver and the fork -> source rule, the
    same path as `total_units_by_student`, so the catalog matches what the
    students are actually served rather than what their grade nominally implies.
    Every package counts, since they are additive (#651) — measuring coverage
    against one of a classroom's three packages would report the other two as
    entirely untouched.
    """
    from src.content.service import resolve_curriculum_ids

    rows = await conn.fetch(
        """
        SELECT student_id::text AS student_id, grade
        FROM school_enrolments
        WHERE school_id = $1 AND status = 'active' AND student_id IS NOT NULL
          AND ($2::smallint[] IS NULL OR grade = ANY($2::smallint[]))
        """,
        uuid.UUID(school_id),
        allowed_grades,
    )
    if not rows:
        return set()

    curricula: set[str] = set()
    for row in rows:
        curricula.update(
            await resolve_curriculum_ids(
                row["student_id"], row["grade"], pool, redis, school_id=school_id
            )
        )

    async with pool.acquire() as conn2:
        await conn2.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        unit_rows = await conn2.fetch(
            """
            SELECT cu.unit_id
            FROM curricula c
            JOIN curriculum_units cu
              ON cu.curriculum_id = CASE
                     WHEN EXISTS (SELECT 1 FROM curriculum_units own
                                  WHERE own.curriculum_id = c.curriculum_id)
                     THEN c.curriculum_id
                     ELSE c.source_curriculum_id
                 END
            WHERE c.curriculum_id = ANY($1::text[])
            """,
            list(curricula),
        )
    return {r["unit_id"] for r in unit_rows}


async def _enrolled_ids(
    conn: asyncpg.Connection,
    school_id: str,
    allowed_grades: list[int] | None = None,
) -> list[str]:
    """Return active enrolled student UUIDs (as strings) for a school.

    `allowed_grades` narrows the cohort to the grades the caller is entitled to
    (#576). `None` means no restriction — a `school_admin`, who is a teacher
    superset under ADR-005, or an internal caller with no teacher context.

    This is the single place five of the six aggregate reports get their cohort
    from (overview, unit, curriculum-health, feedback, trends), so scoping here
    scopes all of them at once rather than repeating the filter per endpoint.
    `get_at_risk_students` builds its own `enrolled` CTE and is scoped
    separately.

    An EMPTY list is meaningful and distinct from None: a teacher with no grade
    assignments has no cohort and must see no students, rather than every
    student. Callers must pass None to mean "unrestricted".
    """
    rows = await conn.fetch(
        """
        SELECT student_id::text
        FROM school_enrolments
        WHERE school_id = $1 AND status = 'active' AND student_id IS NOT NULL
          AND ($2::smallint[] IS NULL OR grade = ANY($2::smallint[]))
        """,
        uuid.UUID(school_id),
        allowed_grades,
    )
    return [r["student_id"] for r in rows]


def _health_tier(pass_rate: float, avg_attempts: float, has_activity: bool) -> str:
    if not has_activity:
        return "no_activity"
    if pass_rate >= _HEALTHY_PASS and avg_attempts <= _HEALTHY_ATT:
        return "healthy"
    if pass_rate < _STRUGGLE_PASS or avg_attempts > _STRUGGLE_ATT:
        return "struggling"
    return "watch"


def _recommended_action(tier: str) -> str:
    return {
        "healthy": "none",
        "watch": "review_content",
        "struggling": "report_to_admin",
        "no_activity": "add_class_time",
    }.get(tier, "none")


# ── Report 1: Class Overview ──────────────────────────────────────────────────


async def get_overview(
    conn: asyncpg.Connection,
    school_id: str,
    period: str,
    allowed_grades: list[int] | None = None,
    pool=None,
    redis=None,
) -> dict:
    """Single-screen class summary for the selected period.

    `allowed_grades` limits the cohort to the caller's assigned grades
    (#576); None means unrestricted (school_admin / internal caller).
    """
    start = _period_start(period)

    enrolled = await _enrolled_ids(conn, school_id, allowed_grades)
    n_enrolled = len(enrolled)

    if not enrolled:
        return {
            "school_id": school_id,
            "period": period,
            "enrolled_students": 0,
            "active_students_period": 0,
            "active_pct": 0.0,
            "lessons_viewed": 0,
            "quiz_attempts": 0,
            "first_attempt_pass_rate_pct": 0.0,
            "audio_play_rate_pct": 0.0,
            "units_with_struggles": [],
            "units_no_activity": [],
            "unreviewed_feedback_count": 0,
        }

    id_uuids = [uuid.UUID(s) for s in enrolled]
    placeholders = ", ".join(f"${i + 2}" for i in range(len(id_uuids)))

    # Active students (any lesson view in period)
    active_row = await conn.fetchrow(
        f"""
        SELECT COUNT(DISTINCT student_id) AS active_students,
               COUNT(*) AS lessons_viewed,
               COUNT(*) FILTER (WHERE audio_played) AS audio_plays
        FROM lesson_views
        WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[])
          AND started_at >= $1
        """,
        start,
        *id_uuids,
    )
    active_students = active_row["active_students"] or 0
    lessons_viewed = active_row["lessons_viewed"] or 0
    audio_plays = active_row["audio_plays"] or 0

    # Quiz attempts + pass rates in period
    quiz_row = await conn.fetchrow(
        f"""
        SELECT
            -- An attempt is a quiz the student actually engaged with (#579).
            -- This counted every row, and a row was written on every quiz-page
            -- load — which is how a school with 8 real attempts read "QUIZ
            -- ATTEMPTS 85". Sessions with no answers that were never completed
            -- are page loads, not attempts.
            --
            -- The pass rates below already filter on `completed`, so they were
            -- never inflated by this and are deliberately left alone: the two
            -- must not be conflated (avg score verified correct on the demo).
            COUNT(*) FILTER (
                WHERE completed
                   OR EXISTS (
                       SELECT 1 FROM progress_answers pa
                       WHERE pa.session_id = progress_sessions.session_id
                   )
            ) AS quiz_attempts,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE attempt_number = 1 AND passed AND completed)
                -- Denominator counts first-attempt SESSIONS, not distinct
                -- students (#471). School-wide a student has one attempt-1
                -- session per unit, so COUNT(DISTINCT student_id) under-counts
                -- the denominator and the rate blew past 100% (e.g. 500% for
                -- 2 students who each passed ~10 units on the first try).
                / NULLIF(COUNT(*) FILTER (WHERE attempt_number = 1 AND completed), 0),
                1
            ) AS first_attempt_pass_rate_pct
        FROM progress_sessions
        WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[])
          AND started_at >= $1
        """,
        start,
        *id_uuids,
    )
    quiz_attempts = quiz_row["quiz_attempts"] or 0
    pass_rate = float(quiz_row["first_attempt_pass_rate_pct"] or 0)

    # Audio play rate
    audio_rate = round(100.0 * audio_plays / lessons_viewed, 1) if lessons_viewed else 0.0

    # Units with struggle (all time for the school)
    struggle_rows = await conn.fetch(
        f"""
        SELECT unit_id,
               ROUND(
                   -- Per unit the population is STUDENTS, so both sides count distinct
                   -- students. Counting rows in the numerator let one student with
                   -- several completed attempt-1 sessions on a unit exceed 100% (#623).
                   -- Unlike get_curriculum_health this query has no join, so it was
                   -- never inflated by lesson-view fan-out (#625) — it is fixed here
                   -- because the metric is the same and the row/student mismatch is
                   -- wrong either way, not because it was observed misreporting.
                   -- NOTE: the school-wide query above is rows/rows on purpose —
                   -- see the #471 comment there. Do not "unify" them.
                   100.0 * COUNT(DISTINCT student_id) FILTER (WHERE attempt_number = 1 AND passed AND completed)
                   / NULLIF(COUNT(DISTINCT student_id) FILTER (WHERE attempt_number = 1 AND completed), 0),
                   1
               ) AS first_pass_rate,
               ROUND(AVG(attempt_number) FILTER (WHERE passed AND completed)::numeric, 1) AS avg_att
        FROM progress_sessions
        WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[])
          AND started_at >= $1
        GROUP BY unit_id
        """,
        start,
        *id_uuids,
    )
    units_with_struggles = [
        r["unit_id"]
        for r in struggle_rows
        if (
            float(r["first_pass_rate"] or 0) < _STRUGGLE_PASS
            or float(r["avg_att"] or 1) > _STRUGGLE_ATT
        )
    ]

    # Units with NO activity in the period, measured against the real catalog
    # (#590).
    #
    # This used to be (units viewed BEFORE the period) minus (units quizzed
    # DURING it) — "went quiet", not "untouched", and structurally empty
    # whenever no lesson views predate the window. A unit never opened could
    # therefore never appear, which is the one case the card exists for.
    touched_rows = await conn.fetch(
        f"""
        SELECT DISTINCT unit_id FROM lesson_views
        WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[]) AND started_at >= $1
        UNION
        SELECT DISTINCT unit_id FROM progress_sessions
        WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[]) AND started_at >= $1
        """,
        start,
        *id_uuids,
    )
    touched_units = {r["unit_id"] for r in touched_rows}
    catalog = (
        await cohort_unit_ids(conn, pool, redis, school_id, allowed_grades)
        if pool is not None and redis is not None
        else set()
    )
    units_no_activity = sorted(catalog - touched_units)

    # Unreviewed feedback from enrolled students (no $1=start param here)
    fb_placeholders = ", ".join(f"${i + 1}" for i in range(len(id_uuids)))
    feedback_row = await conn.fetchrow(
        f"""
        SELECT COUNT(*) AS cnt FROM feedback
        WHERE student_id = ANY(ARRAY[{fb_placeholders}]::uuid[]) AND NOT reviewed
        """,
        *id_uuids,
    )
    unreviewed = feedback_row["cnt"] or 0

    return {
        "school_id": school_id,
        "period": period,
        "enrolled_students": n_enrolled,
        "active_students_period": active_students,
        "active_pct": round(100.0 * active_students / n_enrolled, 1) if n_enrolled else 0.0,
        "lessons_viewed": lessons_viewed,
        "quiz_attempts": quiz_attempts,
        "first_attempt_pass_rate_pct": pass_rate,
        "audio_play_rate_pct": audio_rate,
        "units_with_struggles": units_with_struggles,
        "units_no_activity": units_no_activity,
        "unreviewed_feedback_count": unreviewed,
    }


# ── Report 2: Unit Performance ────────────────────────────────────────────────


async def get_unit_report(
    conn: asyncpg.Connection,
    school_id: str,
    unit_id: str,
    period: str,
    allowed_grades: list[int] | None = None,
) -> dict:
    """Per-unit deep-dive for enrolled students in the period.

    `allowed_grades` limits the cohort to the caller's assigned grades
    (#576); None means unrestricted (school_admin / internal caller).
    """
    start = _period_start(period)
    enrolled = await _enrolled_ids(conn, school_id, allowed_grades)
    n_enrolled = len(enrolled)
    id_uuids = [uuid.UUID(s) for s in enrolled]

    if not enrolled:
        return _empty_unit_report(school_id, unit_id, period)

    placeholders = ", ".join(f"${i + 3}" for i in range(len(id_uuids)))

    # Lesson view stats
    lv_row = await conn.fetchrow(
        f"""
        SELECT
            COUNT(DISTINCT student_id)                          AS students_viewed,
            COUNT(*)                                            AS total_views,
            ROUND(AVG(duration_s)::numeric, 1)                  AS avg_duration_s,
            COUNT(*) FILTER (WHERE audio_played)                AS audio_plays,
            COUNT(*) FILTER (WHERE experiment_viewed)           AS exp_views
        FROM lesson_views
        WHERE unit_id = $1
          AND started_at >= $2
          AND student_id = ANY(ARRAY[{placeholders}]::uuid[])
        """,
        unit_id,
        start,
        *id_uuids,
    )
    students_viewed = lv_row["students_viewed"] or 0
    total_views = lv_row["total_views"] or 0
    avg_duration = float(lv_row["avg_duration_s"] or 0)
    audio_plays = lv_row["audio_plays"] or 0
    exp_views = lv_row["exp_views"] or 0
    audio_rate = round(100.0 * audio_plays / total_views, 1) if total_views else 0.0
    exp_rate = round(100.0 * exp_views / total_views, 1) if total_views else None

    # Quiz stats
    quiz_rows = await conn.fetch(
        f"""
        SELECT student_id::text, attempt_number, score, passed, completed
        FROM progress_sessions
        WHERE unit_id = $1
          AND started_at >= $2
          AND student_id = ANY(ARRAY[{placeholders}]::uuid[])
        """,
        unit_id,
        start,
        *id_uuids,
    )
    students_attempted = len({r["student_id"] for r in quiz_rows if r["completed"]})
    first_pass = sum(
        1 for r in quiz_rows if r["attempt_number"] == 1 and r["passed"] and r["completed"]
    )
    first_attempt_students = len(
        {r["student_id"] for r in quiz_rows if r["attempt_number"] == 1 and r["completed"]}
    )
    pass_rate = (
        round(100.0 * first_pass / first_attempt_students, 1) if first_attempt_students else 0.0
    )

    completed_rows = [r for r in quiz_rows if r["completed"]]
    avg_score = (
        round(
            sum(r["score"] for r in completed_rows if r["score"] is not None) / len(completed_rows),
            1,
        )
        if completed_rows
        else 0.0
    )

    # Average attempts to pass
    passed_students: dict[str, int] = {}
    for r in quiz_rows:
        if r["passed"] and r["completed"]:
            sid = r["student_id"]
            passed_students[sid] = max(passed_students.get(sid, 0), r["attempt_number"])
    avg_att = (
        round(sum(passed_students.values()) / len(passed_students), 1) if passed_students else 0.0
    )

    # Attempt distribution
    att_counts: dict[str, int] = {}
    for r in quiz_rows:
        if r["completed"]:
            sid = r["student_id"]
            att_counts[sid] = max(att_counts.get(sid, 0), r["attempt_number"])
    dist = {"one": 0, "two": 0, "three": 0, "four_plus": 0}
    for v in att_counts.values():
        if v == 1:
            dist["one"] += 1
        elif v == 2:
            dist["two"] += 1
        elif v == 3:
            dist["three"] += 1
        else:
            dist["four_plus"] += 1

    struggle_flag = pass_rate < _STRUGGLE_PASS or avg_att > _STRUGGLE_ATT

    # Feedback for this unit from enrolled students
    fb_placeholders = ", ".join(f"${i + 2}" for i in range(len(id_uuids)))
    fb_rows = await conn.fetch(
        f"""
        SELECT feedback_id::text, category, rating, message, helpful, content_type, submitted_at
        FROM feedback
        WHERE unit_id = $1
          AND student_id = ANY(ARRAY[{fb_placeholders}]::uuid[])
        ORDER BY submitted_at DESC
        LIMIT 3
        """,
        unit_id,
        *id_uuids,
    )
    fb_count_row = await conn.fetchrow(
        f"""
        SELECT COUNT(*) AS cnt, ROUND(AVG(rating)::numeric, 1) AS avg_rating
        FROM feedback
        WHERE unit_id = $1 AND student_id = ANY(ARRAY[{fb_placeholders}]::uuid[])
        """,
        unit_id,
        *id_uuids,
    )

    return {
        "school_id": school_id,
        "unit_id": unit_id,
        "period": period,
        "students_viewed_lesson": students_viewed,
        "lesson_view_pct": round(100.0 * students_viewed / n_enrolled, 1) if n_enrolled else 0.0,
        "avg_lesson_duration_s": avg_duration,
        "audio_play_rate_pct": audio_rate,
        "experiment_view_pct": exp_rate,
        "students_attempted_quiz": students_attempted,
        "quiz_attempt_pct": round(100.0 * students_attempted / n_enrolled, 1)
        if n_enrolled
        else 0.0,
        "first_attempt_pass_rate_pct": pass_rate,
        "avg_score_pct": avg_score,
        "avg_attempts_to_pass": avg_att,
        "attempt_distribution": dist,
        "struggle_flag": struggle_flag,
        "feedback_count": fb_count_row["cnt"] or 0,
        "avg_rating": float(fb_count_row["avg_rating"]) if fb_count_row["avg_rating"] else None,
        "feedback_summary": [
            {
                "feedback_id": r["feedback_id"],
                "category": r["category"],
                "rating": r["rating"],
                "message": r["message"],
                "submitted_at": r["submitted_at"],
            }
            for r in fb_rows
        ],
    }


def _empty_unit_report(school_id: str, unit_id: str, period: str) -> dict:
    return {
        "school_id": school_id,
        "unit_id": unit_id,
        "period": period,
        "students_viewed_lesson": 0,
        "lesson_view_pct": 0.0,
        "avg_lesson_duration_s": 0.0,
        "audio_play_rate_pct": 0.0,
        "experiment_view_pct": None,
        "students_attempted_quiz": 0,
        "quiz_attempt_pct": 0.0,
        "first_attempt_pass_rate_pct": 0.0,
        "avg_score_pct": 0.0,
        "avg_attempts_to_pass": 0.0,
        "attempt_distribution": {"one": 0, "two": 0, "three": 0, "four_plus": 0},
        "struggle_flag": False,
        "feedback_count": 0,
        "avg_rating": None,
        "feedback_summary": [],
    }


# ── Report 3: Student Progress ────────────────────────────────────────────────


async def get_student_report(
    conn: asyncpg.Connection,
    school_id: str,
    student_id: str,
) -> dict:
    """Per-student report card. Raises LookupError if not enrolled."""
    # Verify this student is enrolled in the school
    enrol = await conn.fetchrow(
        "SELECT 1 FROM school_enrolments WHERE school_id = $1 AND student_id = $2 AND status = 'active'",
        uuid.UUID(school_id),
        uuid.UUID(student_id),
    )
    if enrol is None:
        raise LookupError(f"student {student_id} not enrolled in school {school_id}")

    # Student basics
    student = await conn.fetchrow(
        "SELECT name, grade, email FROM students WHERE student_id = $1",
        uuid.UUID(student_id),
    )
    if student is None:
        raise LookupError(f"student {student_id} not found")

    # Last active
    last_lv = await conn.fetchval(
        "SELECT MAX(started_at) FROM lesson_views WHERE student_id = $1",
        uuid.UUID(student_id),
    )
    last_ps = await conn.fetchval(
        "SELECT MAX(started_at) FROM progress_sessions WHERE student_id = $1",
        uuid.UUID(student_id),
    )
    last_active = max(filter(None, [last_lv, last_ps]), default=None)

    # Summary
    summary = await conn.fetchrow(
        """
        SELECT
            COUNT(DISTINCT unit_id) FILTER (WHERE passed)                AS units_completed,
            ROUND(AVG(score) FILTER (WHERE completed)::numeric, 1)       AS avg_score,
            COUNT(*) FILTER (WHERE attempt_number = 1 AND passed AND completed) AS first_pass,
            COUNT(DISTINCT student_id) FILTER (WHERE attempt_number = 1 AND completed) AS first_att_students
        FROM progress_sessions
        WHERE student_id = $1
        """,
        uuid.UUID(student_id),
    )
    units_completed = summary["units_completed"] or 0
    avg_score = float(summary["avg_score"] or 0)
    # Recalculate first attempt pass rate properly
    first_att_row = await conn.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE attempt_number = 1 AND passed AND completed) AS passed,
            COUNT(*) FILTER (WHERE attempt_number = 1 AND completed) AS total
        FROM progress_sessions
        WHERE student_id = $1
        """,
        uuid.UUID(student_id),
    )
    first_pass_rate = (
        round(100.0 * (first_att_row["passed"] or 0) / (first_att_row["total"] or 1), 1)
        if (first_att_row["total"] or 0) > 0
        else 0.0
    )

    # Total time
    time_row = await conn.fetchrow(
        "SELECT COALESCE(SUM(duration_s), 0)::int AS total_s FROM lesson_views WHERE student_id = $1",
        uuid.UUID(student_id),
    )
    total_time = time_row["total_s"] or 0

    # Units in progress (lesson viewed but not yet passed)
    in_progress_row = await conn.fetchrow(
        """
        SELECT COUNT(DISTINCT lv.unit_id) AS cnt
        FROM lesson_views lv
        LEFT JOIN (
            SELECT unit_id FROM progress_sessions
            WHERE student_id = $1 AND passed
        ) ps ON ps.unit_id = lv.unit_id
        WHERE lv.student_id = $1 AND ps.unit_id IS NULL
        """,
        uuid.UUID(student_id),
    )
    units_in_progress = in_progress_row["cnt"] or 0

    # Per-unit breakdown.
    #
    # Grouped by unit_id ONLY (not ps.subject, issue: duplicate unit rows).
    # progress_sessions.subject is a raw stored value that can legitimately
    # differ across sessions for the SAME unit — pre-#524 sessions stored the
    # "unknown" sentinel, later sessions store the real subject code — while
    # the response's display subject is resolved from unit_id alone
    # (resolve_subject_labels / display_subject, below). Grouping on the raw
    # column produced two rows sharing an identical resolved display label,
    # which is exactly the "same unit shown twice" bug a QA tester reported.
    # MAX(ps.subject) just picks a representative raw value for the fallback
    # path in display_subject() — it is never the value actually shown when a
    # curriculum-derived label exists.
    unit_rows = await conn.fetch(
        """
        SELECT
            ps.unit_id,
            MAX(ps.subject)                                      AS subject,
            MAX(ps.attempt_number)                               AS quiz_attempts,
            -- best_score is a PERCENTAGE (issue #463): score is a raw question
            -- count, so divide by total_questions. NULLIF guards divide-by-zero.
            MAX((ps.score::float / NULLIF(ps.total_questions, 0)) * 100)
                FILTER (WHERE ps.completed AND ps.score IS NOT NULL
                              AND ps.total_questions > 0)          AS best_score,
            BOOL_OR(ps.passed)                                   AS passed,
            COUNT(DISTINCT lv.view_id) > 0                       AS lesson_viewed,
            ROUND(AVG(lv.duration_s)::numeric, 1)                AS avg_duration_s
        FROM progress_sessions ps
        LEFT JOIN lesson_views lv ON lv.student_id = ps.student_id AND lv.unit_id = ps.unit_id
        WHERE ps.student_id = $1
        GROUP BY ps.unit_id
        ORDER BY ps.unit_id
        """,
        uuid.UUID(student_id),
    )

    # Get unit_names from curriculum_units
    unit_ids = [r["unit_id"] for r in unit_rows]
    unit_names: dict[str, str] = {}
    if unit_ids:
        name_rows = await conn.fetch(
            "SELECT unit_id, unit_name FROM curriculum_units WHERE unit_id = ANY($1::text[])",
            unit_ids,
        )
        unit_names = {r["unit_id"]: r["unit_name"] for r in name_rows if r["unit_name"]}

    # Resolve human-readable subject names (issue #462).
    subject_labels = await resolve_subject_labels(conn, unit_ids)

    per_unit = [
        {
            "unit_id": r["unit_id"],
            "unit_name": unit_names.get(r["unit_id"]),
            "subject": display_subject(subject_labels, r["unit_id"], r["subject"]),
            "lesson_viewed": bool(r["lesson_viewed"]),
            "quiz_attempts": r["quiz_attempts"] or 0,
            "best_score": min(100.0, round(float(r["best_score"]), 1))
            if r["best_score"] is not None
            else None,
            "passed": bool(r["passed"]),
            "avg_duration_s": float(r["avg_duration_s"] or 0),
        }
        for r in unit_rows
    ]

    # Strongest / needs-attention subject (keyed on the resolved display name)
    subj_scores: dict[str, list[float]] = {}
    for r in unit_rows:
        s = display_subject(subject_labels, r["unit_id"], r["subject"])
        if r["best_score"] is not None:
            subj_scores.setdefault(s, []).append(min(100.0, float(r["best_score"])))
    subj_avg = {s: sum(v) / len(v) for s, v in subj_scores.items() if v}
    strongest = max(subj_avg, key=subj_avg.__getitem__) if subj_avg else None
    needs_att = min(subj_avg, key=subj_avg.__getitem__) if len(subj_avg) > 1 else None

    return {
        "school_id": school_id,
        "student_id": student_id,
        "student_name": student["name"],
        "grade": student["grade"],
        "last_active": last_active,
        "units_completed": units_completed,
        "units_in_progress": units_in_progress,
        "first_attempt_pass_rate_pct": first_pass_rate,
        "overall_avg_score_pct": avg_score,
        "total_time_spent_s": total_time,
        "per_unit": per_unit,
        "strongest_subject": strongest,
        "needs_attention_subject": needs_att,
    }


# ── Report 4: Curriculum Health ───────────────────────────────────────────────


async def get_curriculum_health(
    conn: asyncpg.Connection,
    school_id: str,
    allowed_grades: list[int] | None = None,
    pool=None,
    redis=None,
) -> dict:
    """All units ranked by health tier.

    `allowed_grades` limits the cohort to the caller's assigned grades
    (#576); None means unrestricted (school_admin / internal caller).
    """
    enrolled = await _enrolled_ids(conn, school_id, allowed_grades)
    if not enrolled:
        return {
            "school_id": school_id,
            "total_units": 0,
            "healthy_count": 0,
            "watch_count": 0,
            "struggling_count": 0,
            "no_activity_count": 0,
            "units": [],
        }

    id_uuids = [uuid.UUID(s) for s in enrolled]
    placeholders = ", ".join(f"${i + 1}" for i in range(len(id_uuids)))

    # All units these students have interacted with.
    #
    # Grouped by unit_id ONLY — see the identical comment in get_student_report
    # above. Here it matters even more: this query aggregates across MANY
    # students, so grouping on the raw (possibly-"unknown") subject silently
    # split a single unit's health stats into two partial rows — each with its
    # own (wrong, partial) pass rate / avg score / avg attempts — and inflated
    # total_units / healthy_count / watch_count / struggling_count by double-
    # counting the unit. This field is NOT run through resolve_subject_labels /
    # display_subject downstream, so MAX(ps.subject) is the actual value shown.
    rows = await conn.fetch(
        f"""
        SELECT
            ps.unit_id,
            MAX(ps.subject)                                    AS subject,
            ROUND(
                -- Both sides count distinct students: per unit the population is
                -- STUDENTS, not session rows (#623).
                100.0 * COUNT(DISTINCT ps.student_id) FILTER (WHERE ps.attempt_number = 1 AND ps.passed AND ps.completed)
                / NULLIF(COUNT(DISTINCT ps.student_id) FILTER (WHERE ps.attempt_number = 1 AND ps.completed), 0),
                1
            )                                                   AS first_pass_rate,
            ROUND(AVG(ps.score) FILTER (WHERE ps.completed)::numeric, 1) AS avg_score,
            ROUND(AVG(ps.attempt_number) FILTER (WHERE ps.passed AND ps.completed)::numeric, 1) AS avg_att,
            BOOL_OR(lv.viewed)                                  AS has_lesson_view
        FROM progress_sessions ps
        -- Collapse lesson views to at most ONE row per (student, unit) BEFORE
        -- joining (issue #625). Joining `lesson_views` directly fanned each quiz
        -- session out into one row per view, so a student who opened the lesson
        -- N times was counted N times by every row-based aggregate here:
        --
        --   * the pass-rate numerator counted joined rows against distinct
        --     students and reported 200% / 300% / 800% — this was the actual
        --     cause of #623, which was fixed by making both sides DISTINCT
        --     (immune to fan-out) while the wrong cause was recorded;
        --   * AVG(score) and AVG(attempt_number) are NOT immune, and still
        --     weighted each student by their lesson-view count — the reason a
        --     struggling student who re-read the lesson less could be averaged
        --     away by a strong one who re-read it more.
        --
        -- Same defect and same remedy as #464 in analytics/service.py. Joining
        -- on (student_id, unit_id) keeps the original meaning of has_lesson_view:
        -- "a student with a session on this unit also viewed its lesson".
        LEFT JOIN (
            SELECT student_id, unit_id, TRUE AS viewed
            FROM lesson_views
            WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[])
            GROUP BY student_id, unit_id
        ) lv ON lv.student_id = ps.student_id AND lv.unit_id = ps.unit_id
        WHERE ps.student_id = ANY(ARRAY[{placeholders}]::uuid[])
        GROUP BY ps.unit_id
        ORDER BY ps.unit_id
        """,
        *id_uuids,
    )

    # Get unit_names
    unit_ids = [r["unit_id"] for r in rows]
    unit_names: dict[str, str] = {}
    if unit_ids:
        name_rows = await conn.fetch(
            "SELECT unit_id, unit_name FROM curriculum_units WHERE unit_id = ANY($1::text[])",
            unit_ids,
        )
        unit_names = {r["unit_id"]: r["unit_name"] for r in name_rows if r["unit_name"]}

    # Feedback summary per unit
    fb_rows = await conn.fetch(
        f"""
        SELECT unit_id,
               COUNT(*) AS fb_count,
               ROUND(AVG(rating)::numeric, 1) AS avg_rating
        FROM feedback
        WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[]) AND unit_id IS NOT NULL
        GROUP BY unit_id
        """,
        *id_uuids,
    )
    fb_map = {r["unit_id"]: r for r in fb_rows}

    # Units nobody has touched never appear in `rows`, because those come
    # `FROM progress_sessions` — so the report designed to surface coverage gaps
    # was blind to exactly the units that represent one (#590). Merge the
    # school's real catalog in, so an untouched unit is REPORTED as untouched
    # rather than silently missing from `total_units` and every tier count.
    catalog = (
        await cohort_unit_ids(conn, pool, redis, school_id, allowed_grades)
        if pool is not None and redis is not None
        else set()
    )
    seen = {r["unit_id"] for r in rows}
    untouched = sorted(catalog - seen)

    units = []
    counts = {"healthy": 0, "watch": 0, "struggling": 0, "no_activity": 0}
    for r in rows:
        pass_rate = float(r["first_pass_rate"] or 0)
        avg_att = float(r["avg_att"] or 0)
        avg_score = float(r["avg_score"] or 0)
        has_lv = bool(r["has_lesson_view"])
        tier = _health_tier(pass_rate, avg_att, has_lv)
        action = _recommended_action(tier)
        counts[tier] += 1
        fb = fb_map.get(r["unit_id"])
        units.append(
            {
                "unit_id": r["unit_id"],
                "unit_name": unit_names.get(r["unit_id"]),
                "subject": r["subject"],
                "health_tier": tier,
                "first_attempt_pass_rate_pct": pass_rate,
                "avg_attempts_to_pass": avg_att,
                "avg_score_pct": avg_score,
                "feedback_count": fb["fb_count"] if fb else 0,
                "avg_rating": float(fb["avg_rating"]) if fb and fb["avg_rating"] else None,
                "recommended_action": action,
            }
        )

    if untouched:
        untouched_names = await conn.fetch(
            "SELECT unit_id, unit_name, subject FROM curriculum_units WHERE unit_id = ANY($1::text[])",
            untouched,
        )
        meta = {r["unit_id"]: r for r in untouched_names}
        for unit_id in untouched:
            row = meta.get(unit_id)
            counts["no_activity"] += 1
            units.append(
                {
                    "unit_id": unit_id,
                    "unit_name": row["unit_name"] if row else None,
                    "subject": row["subject"] if row else None,
                    "health_tier": "no_activity",
                    "first_attempt_pass_rate_pct": 0.0,
                    "avg_attempts_to_pass": 0.0,
                    "avg_score_pct": 0.0,
                    "feedback_count": 0,
                    "avg_rating": None,
                    "recommended_action": _recommended_action("no_activity"),
                }
            )

    return {
        "school_id": school_id,
        "total_units": len(units),
        "healthy_count": counts["healthy"],
        "watch_count": counts["watch"],
        "struggling_count": counts["struggling"],
        "no_activity_count": counts["no_activity"],
        "units": units,
    }


# ── Report 5: Feedback Report ─────────────────────────────────────────────────


async def get_feedback_report(
    conn: asyncpg.Connection,
    school_id: str,
    unit_id: str | None = None,
    category: str | None = None,
    reviewed: bool | None = None,
    sort: str = "recent",
    page: int = 1,
    page_size: int = 50,
    allowed_grades: list[int] | None = None,
) -> dict:
    """A page of feedback from enrolled students, newest first by default.

    This used to group by unit and loop, issuing three queries PER UNIT and
    returning every item ever recorded — so both the query count and the
    payload grew with a school's total feedback volume (issue #611). It is now
    three queries regardless of how many units have feedback: the summary, the
    filtered count, and the page itself.
    """
    enrolled = await _enrolled_ids(conn, school_id, allowed_grades)
    if not enrolled:
        return {
            "school_id": school_id,
            "total_feedback_count": 0,
            "unreviewed_count": 0,
            "avg_rating_overall": None,
            "items": [],
            "pagination": {"page": page, "page_size": page_size, "total": 0},
        }

    id_uuids = [uuid.UUID(s) for s in enrolled]

    # 1) Summary over ALL of the school's feedback — the header describes the
    #    school, not whatever the current filters happen to show.
    summary = await conn.fetchrow(
        """
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE NOT reviewed) AS unreviewed,
               ROUND(AVG(rating)::numeric, 1) AS avg_rating
        FROM feedback
        WHERE student_id = ANY($1::uuid[])
        """,
        id_uuids,
    )

    # 2) The filtered set — drives pagination, so it must honour the filters.
    filters = ["student_id = ANY($1::uuid[])"]
    params: list = [id_uuids]
    if unit_id:
        params.append(unit_id)
        filters.append(f"unit_id = ${len(params)}")
    if category:
        params.append(category)
        filters.append(f"category = ${len(params)}")
    if reviewed is not None:
        params.append(reviewed)
        filters.append(f"reviewed = ${len(params)}")
    where = " AND ".join(filters)

    total = await conn.fetchval(f"SELECT COUNT(*) FROM feedback WHERE {where}", *params)

    # 3) The page. feedback_id breaks ties so paging cannot repeat or skip a row
    #    when several arrive in the same instant.
    direction = "ASC" if sort == "oldest" else "DESC"
    offset = max(page - 1, 0) * page_size
    rows = await conn.fetch(
        f"""
        SELECT f.feedback_id::text,
               f.unit_id,
               cu.unit_name,
               f.category,
               f.rating,
               f.helpful,
               f.content_type,
               f.message,
               f.submitted_at,
               f.reviewed
        FROM feedback f
        LEFT JOIN LATERAL (
            SELECT unit_name FROM curriculum_units
            WHERE unit_id = f.unit_id LIMIT 1
        ) cu ON TRUE
        WHERE {where}
        ORDER BY f.submitted_at {direction}, f.feedback_id {direction}
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """,
        *params,
        page_size,
        offset,
    )

    return {
        "school_id": school_id,
        "total_feedback_count": summary["total"] or 0,
        "unreviewed_count": summary["unreviewed"] or 0,
        "avg_rating_overall": float(summary["avg_rating"]) if summary["avg_rating"] else None,
        "items": [dict(r) for r in rows],
        "pagination": {"page": page, "page_size": page_size, "total": total or 0},
    }


async def get_trends(
    conn: asyncpg.Connection,
    school_id: str,
    period: str,
    allowed_grades: list[int] | None = None,
) -> dict:
    """Week-over-week trend data for enrolled students.

    `allowed_grades` limits the cohort to the caller's assigned grades
    (#576); None means unrestricted (school_admin / internal caller).
    """
    n_weeks = _trend_weeks(period)
    now = datetime.now(UTC)

    enrolled = await _enrolled_ids(conn, school_id, allowed_grades)
    id_uuids = [uuid.UUID(s) for s in enrolled]
    # Placeholders for student IDs starting at $3 (after week_start=$1 and week_end=$2).
    # For empty enrollment ARRAY[]::uuid[] is used — PostgreSQL returns 0 counts correctly.
    id_placeholders = ", ".join(f"${i + 3}" for i in range(len(id_uuids)))
    enrolled_filter = (
        f"AND student_id = ANY(ARRAY[{id_placeholders}]::uuid[])" if id_uuids else "AND FALSE"
    )

    # Anchor buckets to ISO weeks (Monday 00:00 UTC) so the week_start labels are
    # always Mondays, regardless of which weekday the report happens to be run on.
    # (Previously week_start = now - N weeks, which tracked today's weekday.)
    this_monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    weeks = []
    for i in range(n_weeks - 1, -1, -1):
        week_start = this_monday - timedelta(weeks=i)
        week_end = week_start + timedelta(weeks=1)

        lv_row = await conn.fetchrow(
            f"""
            SELECT COUNT(DISTINCT student_id) AS active,
                   COUNT(*) AS views,
                   COUNT(*) FILTER (WHERE audio_played) AS audio
            FROM lesson_views
            WHERE started_at >= $1 AND started_at < $2
              {enrolled_filter}
            """,
            week_start,
            week_end,
            *id_uuids,
        )
        ps_row = await conn.fetchrow(
            f"""
            SELECT COUNT(*) AS attempts,
                   ROUND(AVG(score) FILTER (WHERE completed)::numeric, 1) AS avg_score,
                   ROUND(
                       100.0 * COUNT(*) FILTER (WHERE attempt_number = 1 AND passed AND completed)
                       -- count first-attempt SESSIONS, not distinct students (#471)
                       / NULLIF(COUNT(*) FILTER (WHERE attempt_number = 1 AND completed), 0),
                       1
                   ) AS pass_rate
            FROM progress_sessions
            WHERE started_at >= $1 AND started_at < $2
              {enrolled_filter}
            """,
            week_start,
            week_end,
            *id_uuids,
        )
        weeks.append(
            {
                "week_start": week_start.strftime("%Y-%m-%d"),
                "active_students": lv_row["active"] or 0,
                "lessons_viewed": lv_row["views"] or 0,
                "quiz_attempts": ps_row["attempts"] or 0,
                "avg_score_pct": float(ps_row["avg_score"] or 0),
                "first_attempt_pass_rate_pct": float(ps_row["pass_rate"] or 0),
            }
        )

    return {"school_id": school_id, "period": period, "weeks": weeks}


# ── Export ────────────────────────────────────────────────────────────────────


async def trigger_export(
    school_id: str,
    report_type: str,
    filters: dict,
) -> dict:
    """
    Dispatch a CSV export Celery task and return {export_id, download_url}.

    The Celery task writes the CSV to CONTENT_STORE_PATH/exports/{export_id}.csv.
    """
    from src.core.celery_app import celery_app

    export_id = str(uuid.uuid4())
    celery_app.send_task(
        "src.auth.tasks.export_report_task",
        kwargs={
            "export_id": export_id,
            "school_id": school_id,
            "report_type": report_type,
            "filters": filters,
        },
        queue="io",
    )
    return {
        "export_id": export_id,
        "download_url": f"/api/v1/reports/download/{export_id}",
        "status": "queued",
    }


# ── Alerts ────────────────────────────────────────────────────────────────────


async def get_alerts(
    conn: asyncpg.Connection,
    school_id: str,
    allowed_grades: list[int] | None = None,
) -> dict:
    """Return unacknowledged alerts, scoped to the caller's grades (#647).

    Alerts were filtered on school alone, so a Grade-8 teacher's landing page
    listed pass-rate breaches for Grades 5, 10 and 11. Narrower than the #576
    original — unit-level rather than named students — but the same class of
    leak, and on the first screen a teacher sees.

    `allowed_grades=None` is unrestricted (`school_admin`). An EMPTY list means
    a teacher with no assignments, who correctly sees nothing.

    ## Where the grade comes from

    `report_alerts` has no grade column; the only alert type written is
    `pass_rate_breach`, whose `details` carries a `unit_id`. The grade is
    resolved through `curriculum_units -> curricula`. Every alert on the demo
    resolves to exactly one grade, so this is a lookup rather than a guess.

    Adding a `grade` column and populating it at write time would be tidier and
    is worth doing if more alert types arrive — but it needs a migration plus a
    backfill of existing rows via this same join, so the join is the honest
    first step rather than a shortcut.

    ## Unresolvable units fail CLOSED

    An alert whose unit is not in `curriculum_units` has no determinable grade,
    and is withheld from a restricted teacher (admins still see it). This is a
    disclosure fix, so the safe direction is to show less. The cost is real —
    a withheld alert is one a teacher does not act on — which is why the
    resolvability was checked against live data first rather than assumed.
    """
    # `grade` is returned alongside each alert so the page can show which grade
    # it belongs to. Without it, a scoped list is indistinguishable from an
    # unscoped one, and the fix is unverifiable by eye.
    rows = await conn.fetch(
        """
        SELECT a.alert_id::text, a.alert_type, a.school_id::text, a.details,
               a.triggered_at, a.acknowledged,
               (SELECT MIN(c.grade)
                  FROM curriculum_units cu
                  JOIN curricula c ON c.curriculum_id = cu.curriculum_id
                 WHERE cu.unit_id = a.details->>'unit_id') AS grade,
               -- The unit's human name, resolved through the same join the grade
               -- already uses. Without it the inbox shows only `G5-TECH-004`,
               -- which a teacher cannot match to anything on the Subjects page
               -- (reported 2026-08-31). MIN() because a unit id can appear in
               -- more than one curriculum; the title is the same in each.
               (SELECT MIN(cu.title)
                  FROM curriculum_units cu
                 WHERE cu.unit_id = a.details->>'unit_id') AS unit_title
        FROM report_alerts a
        WHERE a.school_id = $1
          AND NOT a.acknowledged
          -- Alerts whose breach has since cleared are withdrawn by the evaluator
          -- (migration 0066) rather than lingering until a human dismisses them.
          AND a.resolved_at IS NULL
        ORDER BY a.triggered_at DESC
        """,
        uuid.UUID(school_id),
    )

    if allowed_grades is not None:
        permitted = set(allowed_grades)
        rows = [r for r in rows if r["grade"] is not None and r["grade"] in permitted]

    return {
        "alerts": [
            {
                "alert_id": r["alert_id"],
                "alert_type": r["alert_type"],
                "school_id": r["school_id"],
                "details": r["details"],
                "triggered_at": r["triggered_at"],
                "acknowledged": r["acknowledged"],
                "grade": r["grade"],
                "unit_title": r["unit_title"],
            }
            for r in rows
        ]
    }


# ── Alert lifecycle ───────────────────────────────────────────────────────────
#
# These live here, rather than inline in `evaluate_report_alerts_task`, so the
# tests exercise the same statements the evaluator runs. A test that re-types the
# SQL only proves the copy is consistent with itself, which is how the original
# bug survived: `ON CONFLICT DO NOTHING` looked like deduplication and had no
# constraint to act on, and nothing ever asserted that a second insert was a
# no-op.


async def raise_pass_rate_alert(
    conn: asyncpg.Connection,
    school_id: str,
    unit_id: str,
    pass_rate: float,
) -> None:
    """Open (or refresh) the single open pass-rate alert for a unit.

    Keyed on the partial unique index from migration 0066, so a unit that keeps
    breaching updates one row rather than appending one per daily run.
    `triggered_at` is deliberately NOT touched: the alert should keep saying how
    long the breach has run, not reset to "new" every morning.
    """
    # `details` is built in SQL from scalars rather than bound as JSON, because
    # this runs on two pools with different codecs: the app pool registers a
    # jsonb codec, the Celery task's raw asyncpg pool does not. A pre-dumped
    # string is double-encoded by the codec and lands as a JSON *string*, so
    # `details->>'unit_id'` reads NULL and both the unique index and every
    # unit-keyed query silently stop matching. jsonb_build_object is immune.
    await conn.execute(
        """
        INSERT INTO report_alerts (school_id, alert_type, details)
        VALUES ($1, 'pass_rate_breach',
                jsonb_build_object('unit_id', $2::text, 'pass_rate', $3::float8))
        ON CONFLICT (school_id, alert_type, (details->>'unit_id'))
            WHERE NOT acknowledged AND resolved_at IS NULL
        DO UPDATE SET details = EXCLUDED.details
        """,
        uuid.UUID(school_id),
        unit_id,
        float(pass_rate or 0),
    )


async def resolve_cleared_alerts(
    conn: asyncpg.Connection,
    school_id: str,
    still_breaching: list[str],
) -> int:
    """Withdraw open pass-rate alerts whose breach has cleared. Returns the count.

    An empty `still_breaching` resolves every open alert, which is correct: no
    unit is breaching. `resolved_at` rather than `acknowledged`, because
    acknowledged records that a PERSON dismissed the alert and folding a machine
    observation into that loses the distinction.
    """
    result = await conn.execute(
        """
        UPDATE report_alerts
           SET resolved_at = NOW()
         WHERE school_id = $1
           AND alert_type = 'pass_rate_breach'
           AND resolved_at IS NULL
           AND NOT acknowledged
           AND NOT (details->>'unit_id' = ANY($2::text[]))
        """,
        uuid.UUID(school_id),
        still_breaching,
    )
    return int(result.split()[-1]) if result else 0


# Server-owned defaults for a school that has never saved its thresholds. The
# client no longer keeps its own copy (#526) — these are the single source.
ALERT_SETTINGS_DEFAULTS = {
    "pass_rate_threshold": 50.0,
    "feedback_count_threshold": 3,
    "inactive_days_threshold": 14,
    "score_drop_threshold": 10.0,
    "new_feedback_immediate": True,
}


async def get_alert_settings(
    conn: asyncpg.Connection,
    school_id: str,
) -> dict:
    """Return the school's saved alert thresholds, or the server defaults if it has
    never saved any. The write existed but nothing read it back, so the form always
    redrew hardcoded defaults and saved values looked lost (#526)."""
    row = await conn.fetchrow(
        """
        SELECT school_id::text, pass_rate_threshold, feedback_count_threshold,
               inactive_days_threshold, score_drop_threshold,
               new_feedback_immediate, updated_at
        FROM report_alert_settings
        WHERE school_id = $1
        """,
        uuid.UUID(school_id),
    )
    if row is not None:
        return dict(row)
    return {"school_id": school_id, **ALERT_SETTINGS_DEFAULTS, "updated_at": None}


async def save_alert_settings(
    conn: asyncpg.Connection,
    school_id: str,
    settings: dict,
) -> dict:
    """Upsert alert threshold settings for a school."""
    row = await conn.fetchrow(
        """
        INSERT INTO report_alert_settings
            (school_id, pass_rate_threshold, feedback_count_threshold,
             inactive_days_threshold, score_drop_threshold, new_feedback_immediate, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (school_id) DO UPDATE SET
            pass_rate_threshold      = EXCLUDED.pass_rate_threshold,
            feedback_count_threshold = EXCLUDED.feedback_count_threshold,
            inactive_days_threshold  = EXCLUDED.inactive_days_threshold,
            score_drop_threshold     = EXCLUDED.score_drop_threshold,
            new_feedback_immediate   = EXCLUDED.new_feedback_immediate,
            updated_at               = NOW()
        RETURNING school_id::text, pass_rate_threshold, feedback_count_threshold,
                  inactive_days_threshold, score_drop_threshold,
                  new_feedback_immediate, updated_at
        """,
        uuid.UUID(school_id),
        settings.get("pass_rate_threshold", ALERT_SETTINGS_DEFAULTS["pass_rate_threshold"]),
        settings.get(
            "feedback_count_threshold", ALERT_SETTINGS_DEFAULTS["feedback_count_threshold"]
        ),
        settings.get("inactive_days_threshold", ALERT_SETTINGS_DEFAULTS["inactive_days_threshold"]),
        settings.get("score_drop_threshold", ALERT_SETTINGS_DEFAULTS["score_drop_threshold"]),
        settings.get("new_feedback_immediate", ALERT_SETTINGS_DEFAULTS["new_feedback_immediate"]),
    )
    return dict(row)


# ── Digest ────────────────────────────────────────────────────────────────────


async def subscribe_digest(
    conn: asyncpg.Connection,
    school_id: str,
    teacher_id: str,
    email: str,
    timezone_str: str,
    enabled: bool,
) -> dict:
    """Upsert weekly digest subscription for a teacher."""
    row = await conn.fetchrow(
        """
        INSERT INTO digest_subscriptions (school_id, teacher_id, email, timezone, enabled)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (school_id, teacher_id) DO UPDATE SET
            email    = EXCLUDED.email,
            timezone = EXCLUDED.timezone,
            enabled  = EXCLUDED.enabled
        RETURNING subscription_id::text, school_id::text, email, timezone, enabled
        """,
        uuid.UUID(school_id),
        uuid.UUID(teacher_id),
        email,
        timezone_str,
        enabled,
    )
    return dict(row)


# ── At-Risk Student Action Queue (#79) ───────────────────────────────────────


async def get_at_risk_students(
    conn: asyncpg.Connection,
    school_id: str,
    allowed_grades: list[int] | None = None,
    pool=None,
    redis=None,
) -> dict:
    """
    Return students who are either inactive beyond the school's threshold or
    have a pass rate below the school's threshold.  Augments each row with
    whether a teacher has already marked the student as "seen".
    """
    # Fetch school-specific thresholds (or defaults if not configured).
    settings_row = await conn.fetchrow(
        """
        SELECT inactive_days_threshold, pass_rate_threshold
        FROM report_alert_settings
        WHERE school_id = $1
        """,
        uuid.UUID(school_id),
    )
    inactive_days_threshold = settings_row["inactive_days_threshold"] if settings_row else 14
    pass_rate_threshold = float(settings_row["pass_rate_threshold"]) if settings_row else 50.0

    rows = await conn.fetch(
        """
        WITH enrolled AS (
            -- Scoped to the caller's assigned grades (#576). This report NAMES
            -- individual students flagged as struggling, so an unscoped row is
            -- an educational record disclosed to a teacher who was never
            -- assigned to that student. Grade lives on both `students` and
            -- `school_enrolments`; the enrolment is the authority for "which
            -- grade at THIS school", so filter on it.
            SELECT s.student_id, s.name, s.grade
            FROM students s
            JOIN school_enrolments se ON se.student_id = s.student_id
            WHERE se.school_id = $1 AND se.status = 'active'
              AND ($4::smallint[] IS NULL OR se.grade = ANY($4::smallint[]))
        ),
        quiz_stats AS (
            SELECT
                ps.student_id,
                MAX(ps.ended_at)                                                          AS last_active,
                COALESCE(
                    100.0 * SUM(CASE WHEN ps.passed THEN 1 END)::float / NULLIF(COUNT(*), 0),
                    0
                )                                                                         AS pass_rate_pct,
                -- DISTINCT units, not passed sessions (#655) — see the student
                -- progress report for the same fix. This one also feeds the
                -- `low_pass_rate` gate below, so an inflated count could mark a
                -- student as having done work they had not.
                COUNT(DISTINCT ps.unit_id) FILTER (WHERE ps.passed)                        AS units_completed
            FROM progress_sessions ps
            WHERE ps.student_id IN (SELECT student_id FROM enrolled)
              AND ps.completed = TRUE
            GROUP BY ps.student_id
        ),
        total_units AS (
            -- Placeholder only. The real denominator is each student's OWN
            -- resolved curriculum, filled in by total_units_by_student (#638);
            -- summing every default curriculum at a grade counted four streams
            -- for one Grade 11 student.
            SELECT NULL::int AS grade, 0 AS total WHERE FALSE
        )
        SELECT
            e.student_id,
            e.name                                    AS student_name,
            e.grade,
            qs.last_active,
            CASE WHEN qs.last_active IS NOT NULL
                THEN EXTRACT(EPOCH FROM (NOW() - qs.last_active)) / 86400
            END::int                                  AS inactive_days,
            qs.pass_rate_pct,
            COALESCE(qs.units_completed, 0)           AS units_completed,
            0                                         AS total_units,
            CASE WHEN qs.last_active IS NULL
                      OR EXTRACT(EPOCH FROM (NOW() - qs.last_active)) / 86400 > $2
                 THEN TRUE ELSE FALSE END             AS inactive,
            CASE WHEN COALESCE(qs.pass_rate_pct, 0) < $3
                      AND COALESCE(qs.units_completed, 0) > 0
                 THEN TRUE ELSE FALSE END             AS low_pass_rate,
            ars.seen_at                               AS seen_at
        FROM enrolled e
        LEFT JOIN quiz_stats qs USING (student_id)
        LEFT JOIN total_units tu ON tu.grade = e.grade
        LEFT JOIN at_risk_seen ars ON ars.school_id = $1::uuid
                                   AND ars.student_id = e.student_id
        WHERE
            qs.last_active IS NULL
            OR EXTRACT(EPOCH FROM (NOW() - qs.last_active)) / 86400 > $2
            OR (COALESCE(qs.pass_rate_pct, 0) < $3 AND COALESCE(qs.units_completed, 0) > 0)
        ORDER BY inactive_days DESC NULLS LAST, pass_rate_pct ASC NULLS FIRST
        """,
        uuid.UUID(school_id),
        inactive_days_threshold,
        pass_rate_threshold,
        allowed_grades,
    )

    # Each student's OWN curriculum decides the denominator (#638).
    totals = (
        await total_units_by_student(pool, redis, rows, school_id)
        if pool is not None and redis is not None
        else {}
    )

    students = [
        {
            "student_id": str(r["student_id"]),
            "student_name": r["student_name"],
            "grade": r["grade"],
            "last_active": r["last_active"],
            "inactive_days": r["inactive_days"],
            "pass_rate_pct": round(float(r["pass_rate_pct"]), 1)
            if r["pass_rate_pct"] is not None
            else None,
            "units_completed": int(r["units_completed"]),
            "total_units": totals.get(str(r["student_id"]), 0),
            "risk_reasons": {
                "inactive": bool(r["inactive"]),
                "low_pass_rate": bool(r["low_pass_rate"]),
            },
            "is_seen": r["seen_at"] is not None,
            "seen_at": r["seen_at"],
        }
        for r in rows
    ]
    return {
        "school_id": school_id,
        "inactive_days_threshold": inactive_days_threshold,
        "pass_rate_threshold": pass_rate_threshold,
        "students": students,
        "total": len(students),
    }


async def mark_at_risk_student_seen(
    conn: asyncpg.Connection,
    school_id: str,
    student_id: str,
    teacher_id: str,
    seen: bool,
) -> dict:
    """Toggle the seen flag for an at-risk student."""
    if seen:
        row = await conn.fetchrow(
            """
            INSERT INTO at_risk_seen (school_id, student_id, seen_by, seen_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (school_id, student_id) DO UPDATE SET
                seen_by = EXCLUDED.seen_by,
                seen_at = NOW()
            RETURNING seen_at
            """,
            uuid.UUID(school_id),
            uuid.UUID(student_id),
            uuid.UUID(teacher_id),
        )
        return {
            "school_id": school_id,
            "student_id": student_id,
            "seen": True,
            "seen_at": row["seen_at"],
        }
    else:
        await conn.execute(
            "DELETE FROM at_risk_seen WHERE school_id = $1 AND student_id = $2",
            uuid.UUID(school_id),
            uuid.UUID(student_id),
        )
        return {"school_id": school_id, "student_id": student_id, "seen": False, "seen_at": None}


async def send_at_risk_reminder(
    conn: asyncpg.Connection,
    school_id: str,
    student_id: str,
) -> dict:
    """
    Queue a push notification nudge for a specific at-risk student.

    Mirrors check_quiz_nudges — sends via the existing push task on the io queue.
    Returns immediately; delivery is fire-and-forget.
    """
    from src.core.celery_app import celery_app

    rows = await conn.fetch(
        """
        SELECT pt.device_token
        FROM push_tokens pt
        WHERE pt.student_id = $1
        """,
        uuid.UUID(student_id),
    )
    queued = False
    for row in rows:
        celery_app.send_task(
            "src.auth.tasks.send_push_notification_task",
            kwargs={
                "device_token": row["device_token"],
                "title": "Your teacher checked in!",
                "body": "Keep going — log in to StudyBuddy and continue where you left off.",
            },
            queue="io",
        )
        queued = True

    log.info(
        "at_risk_reminder_queued",
        school_id=school_id,
        student_id=student_id,
        tokens=len(rows),
    )
    return {"school_id": school_id, "student_id": student_id, "queued": queued}


# ── Refresh ───────────────────────────────────────────────────────────────────


async def refresh_materialized_views(pool: asyncpg.Pool) -> dict:
    """
    Refresh all report materialized views.

    Uses REFRESH MATERIALIZED VIEW (not CONCURRENTLY) so this works even
    when the views have no unique index populated. For production, prefer
    CONCURRENTLY to avoid brief read locks.
    """
    views = ["mv_class_summary", "mv_student_progress", "mv_feedback_summary"]
    async with pool.acquire() as conn:
        for view in views:
            await conn.execute(f"REFRESH MATERIALIZED VIEW {view}")
    log.info("materialized_views_refreshed", views=views)
    return {
        "refreshed_at": datetime.now(UTC),
        "views_refreshed": views,
    }
