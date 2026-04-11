"""
backend/src/analytics/service.py

Lesson analytics business logic.

lesson_views table lifecycle:
  start_lesson_view() — INSERT row, returns view_id (called by mobile on lesson open)
  end_lesson_view()   — UPDATE row with duration_s, audio_played, experiment_viewed, ended_at

Ownership:
  verify_view_owner() — raises LookupError/PermissionError (same pattern as progress sessions)

Phase 10 extended analytics:
  get_student_metrics()  — self-service per-unit breakdown for a student
  get_class_metrics()    — aggregate per-unit metrics for a school's enrolled students
"""

from __future__ import annotations

import asyncpg

from src.utils.logger import get_logger

log = get_logger("analytics")


async def start_lesson_view(
    conn: asyncpg.Connection,
    student_id: str,
    unit_id: str,
    curriculum_id: str,
) -> dict:
    """
    Open a new lesson view row.

    Returns {view_id}.
    """
    row = await conn.fetchrow(
        """
        INSERT INTO lesson_views (student_id, unit_id, curriculum_id)
        VALUES ($1, $2, $3)
        RETURNING view_id::text
        """,
        student_id,
        unit_id,
        curriculum_id,
    )
    return {"view_id": row["view_id"]}


async def verify_view_owner(
    conn: asyncpg.Connection,
    view_id: str,
    student_id: str,
) -> dict:
    """
    Check that the lesson view exists and belongs to this student.

    Returns the row on success.
    Raises LookupError if not found, PermissionError if owned by another student.
    """
    row = await conn.fetchrow(
        "SELECT student_id::text, ended_at FROM lesson_views WHERE view_id = $1",
        view_id,
    )
    if row is None:
        raise LookupError(f"lesson view {view_id} not found")
    if str(row["student_id"]) != str(student_id):
        raise PermissionError("view belongs to another student")
    return dict(row)


async def end_lesson_view(
    conn: asyncpg.Connection,
    view_id: str,
    duration_s: int,
    audio_played: bool,
    experiment_viewed: bool,
) -> dict:
    """
    Close a lesson view row.

    Sets ended_at = NOW() and records duration/flags.
    Returns {view_id, duration_s}.
    """
    row = await conn.fetchrow(
        """
        UPDATE lesson_views
        SET ended_at          = NOW(),
            duration_s        = $2,
            audio_played      = $3,
            experiment_viewed = $4
        WHERE view_id = $1
        RETURNING view_id::text, duration_s
        """,
        view_id,
        duration_s,
        audio_played,
        experiment_viewed,
    )
    return {"view_id": row["view_id"], "duration_s": row["duration_s"]}


# ── Phase 10: student self-service metrics ─────────────────────────────────────


async def get_student_metrics(
    conn: asyncpg.Connection,
    student_id: str,
) -> dict:
    """
    Aggregate quiz and lesson metrics for a single student.

    Returns summary counters and a per-unit breakdown.
    """
    # Summary counts from progress_sessions
    summary = await conn.fetchrow(
        """
        SELECT
            COUNT(DISTINCT unit_id) FILTER (WHERE completed)            AS units_attempted,
            COUNT(DISTINCT unit_id) FILTER (WHERE passed)               AS units_completed,
            COUNT(DISTINCT unit_id)
                FILTER (WHERE attempt_number = 1 AND passed)            AS units_passed_first_attempt,
            ROUND(AVG(score) FILTER (WHERE completed)::numeric, 1)      AS overall_avg_score_pct,
            COUNT(*) FILTER (WHERE completed)                           AS quizzes_completed
        FROM progress_sessions
        WHERE student_id = $1
        """,
        student_id,
    )

    # Total lesson time
    time_row = await conn.fetchrow(
        """
        SELECT COALESCE(SUM(duration_s), 0)::int AS total_duration_s,
               COUNT(*)                          AS lessons_viewed,
               COUNT(*) FILTER (WHERE audio_played) AS audio_plays
        FROM lesson_views
        WHERE student_id = $1
        """,
        student_id,
    )

    # Per-unit breakdown: join progress_sessions + lesson_views
    unit_rows = await conn.fetch(
        """
        SELECT
            s.unit_id,
            s.subject,
            MAX(s.attempt_number)                                   AS quiz_attempts,
            MAX(s.score) FILTER (WHERE s.completed)                 AS best_score_pct,
            BOOL_OR(s.passed)                                       AS passed,
            COALESCE(SUM(lv.duration_s), 0)::int                    AS total_time_s,
            COUNT(DISTINCT lv.view_id)                              AS lessons_viewed
        FROM progress_sessions s
        LEFT JOIN lesson_views lv
            ON lv.student_id = s.student_id AND lv.unit_id = s.unit_id
        WHERE s.student_id = $1
        GROUP BY s.unit_id, s.subject
        ORDER BY s.unit_id
        """,
        student_id,
    )

    per_unit = [
        {
            "unit_id": r["unit_id"],
            "subject": r["subject"],
            "quiz_attempts": r["quiz_attempts"] or 0,
            "best_score_pct": float(r["best_score_pct"])
            if r["best_score_pct"] is not None
            else None,
            "passed": bool(r["passed"]),
            "total_time_minutes": round((r["total_time_s"] or 0) / 60, 1),
            "lessons_viewed": r["lessons_viewed"] or 0,
        }
        for r in unit_rows
    ]

    # Improvement trajectory: units with >1 attempt
    traj_rows = await conn.fetch(
        """
        SELECT unit_id,
               MIN(score) FILTER (WHERE attempt_number = 1 AND completed) AS attempt_1_score,
               MAX(score) FILTER (WHERE attempt_number > 1 AND completed)  AS best_retry_score
        FROM progress_sessions
        WHERE student_id = $1 AND completed
        GROUP BY unit_id
        HAVING COUNT(*) > 1
        ORDER BY unit_id
        """,
        student_id,
    )
    improvement_trajectory = [
        {
            "unit_id": r["unit_id"],
            "attempt_1_score": r["attempt_1_score"],
            "best_retry_score": r["best_retry_score"],
            "improvement_pct": (
                round(
                    ((r["best_retry_score"] - r["attempt_1_score"]) / max(r["attempt_1_score"], 1))
                    * 100,
                    1,
                )
                if r["attempt_1_score"] is not None and r["best_retry_score"] is not None
                else None
            ),
        }
        for r in traj_rows
    ]

    return {
        "units_attempted": summary["units_attempted"] or 0,
        "units_completed": summary["units_completed"] or 0,
        "units_passed_first_attempt": summary["units_passed_first_attempt"] or 0,
        "overall_avg_score_pct": float(summary["overall_avg_score_pct"])
        if summary["overall_avg_score_pct"]
        else 0.0,
        "quizzes_completed": summary["quizzes_completed"] or 0,
        "total_time_minutes": round((time_row["total_duration_s"] or 0) / 60, 1),
        "lessons_viewed": time_row["lessons_viewed"] or 0,
        "audio_plays": time_row["audio_plays"] or 0,
        "per_unit": per_unit,
        "improvement_trajectory": improvement_trajectory,
    }


# ── Phase 10: class analytics (teacher view) ─────────────────────────────────

_STRUGGLE_PASS_THRESHOLD = 50.0  # < 50% first-attempt pass rate
_STRUGGLE_ATTEMPTS_THRESHOLD = 2.0  # > 2 mean attempts to pass


async def get_class_metrics(
    conn: asyncpg.Connection,
    school_id: str,
    grade: int | None = None,
    subject: str | None = None,
) -> dict:
    """
    Aggregate per-unit quiz metrics for all enrolled students in a school.

    struggle_flag = True when first_attempt_pass_rate_pct < 50% OR mean_attempts_to_pass > 2.
    """
    # All enrolled student IDs for the school (exclude rows where student hasn't linked yet).
    enrolled = await conn.fetch(
        "SELECT student_id::text FROM school_enrolments WHERE school_id = $1 AND status = 'active' AND student_id IS NOT NULL",
        __import__("uuid").UUID(school_id),
    )
    enrolled_ids = [r["student_id"] for r in enrolled]
    total_enrolled = len(enrolled_ids)

    if not enrolled_ids:
        return {"school_id": school_id, "enrolled_students": 0, "metrics_per_unit": []}

    # Build IN clause for student IDs ($1, $2, ...).
    placeholders = ", ".join(f"${i + 1}" for i in range(len(enrolled_ids)))
    params: list = [__import__("uuid").UUID(sid) for sid in enrolled_ids]

    grade_filter = ""
    subject_filter = ""
    if grade is not None:
        params.append(grade)
        grade_filter = f"AND ps.grade = ${len(params)}"
    if subject is not None:
        params.append(subject)
        subject_filter = f"AND ps.subject = ${len(params)}"

    rows = await conn.fetch(
        f"""
        SELECT
            ps.unit_id,
            ps.subject,
            COUNT(DISTINCT lv.view_id)                                           AS students_with_lesson_view,
            COUNT(DISTINCT ps.session_id)                                        AS total_quiz_attempts,
            COUNT(DISTINCT ps.student_id) FILTER (WHERE ps.completed)           AS unique_students_attempted,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE ps.attempt_number = 1 AND ps.passed AND ps.completed)
                / NULLIF(COUNT(DISTINCT ps.student_id) FILTER (WHERE ps.attempt_number = 1 AND ps.completed), 0),
                1
            )                                                                    AS first_attempt_pass_rate_pct,
            ROUND(AVG(ps.score) FILTER (WHERE ps.completed)::numeric, 1)        AS mean_score_pct,
            ROUND(AVG(ps.attempt_number) FILTER (WHERE ps.passed AND ps.completed)::numeric, 1) AS mean_attempts_to_pass
        FROM progress_sessions ps
        LEFT JOIN lesson_views lv
            ON lv.student_id = ps.student_id AND lv.unit_id = ps.unit_id
        WHERE ps.student_id = ANY(ARRAY[{placeholders}]::uuid[])
              {grade_filter}
              {subject_filter}
        GROUP BY ps.unit_id, ps.subject
        ORDER BY ps.unit_id
        """,
        *params,
    )

    metrics_per_unit = []
    for r in rows:
        first_pass = float(r["first_attempt_pass_rate_pct"] or 0)
        mean_attempts = float(r["mean_attempts_to_pass"] or 1)
        struggle_flag = (
            first_pass < _STRUGGLE_PASS_THRESHOLD or mean_attempts > _STRUGGLE_ATTEMPTS_THRESHOLD
        )
        lv_count = r["students_with_lesson_view"] or 0
        metrics_per_unit.append(
            {
                "unit_id": r["unit_id"],
                "subject": r["subject"],
                "students_with_lesson_view": lv_count,
                "lesson_view_pct": round(100 * lv_count / total_enrolled, 1)
                if total_enrolled
                else 0,
                "total_quiz_attempts": r["total_quiz_attempts"] or 0,
                "unique_students_attempted": r["unique_students_attempted"] or 0,
                "first_attempt_pass_rate_pct": first_pass,
                "mean_score_pct": float(r["mean_score_pct"] or 0),
                "mean_attempts_to_pass": mean_attempts,
                "struggle_flag": struggle_flag,
            }
        )

    return {
        "school_id": school_id,
        "enrolled_students": total_enrolled,
        "metrics_per_unit": metrics_per_unit,
    }
