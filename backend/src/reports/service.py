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

import csv
import io
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import asyncpg

from src.utils.logger import get_logger

log = get_logger("reports")

_STRUGGLE_PASS   = 50.0   # below this → struggling (or watch)
_HEALTHY_PASS    = 70.0   # at or above this → healthy
_STRUGGLE_ATT    = 2.0    # above this → struggling
_HEALTHY_ATT     = 1.5    # at or below this → healthy


# ── Helpers ───────────────────────────────────────────────────────────────────

def _period_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "30d":
        return now - timedelta(days=30)
    if period == "term":
        year = now.year if now.month >= 9 else now.year - 1
        return datetime(year, 9, 1, tzinfo=timezone.utc)
    return now - timedelta(days=7)   # default: 7d


def _trend_weeks(period: str) -> int:
    return {"4w": 4, "12w": 12, "term": 16}.get(period, 4)


async def _enrolled_ids(conn: asyncpg.Connection, school_id: str) -> list[str]:
    """Return active enrolled student UUIDs (as strings) for a school."""
    rows = await conn.fetch(
        """
        SELECT student_id::text
        FROM school_enrolments
        WHERE school_id = $1 AND status = 'active' AND student_id IS NOT NULL
        """,
        uuid.UUID(school_id),
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
        "healthy":     "none",
        "watch":       "review_content",
        "struggling":  "report_to_admin",
        "no_activity": "add_class_time",
    }.get(tier, "none")


# ── Report 1: Class Overview ──────────────────────────────────────────────────

async def get_overview(
    conn: asyncpg.Connection,
    school_id: str,
    period: str,
) -> dict:
    """Single-screen class summary for the selected period."""
    start = _period_start(period)

    enrolled = await _enrolled_ids(conn, school_id)
    n_enrolled = len(enrolled)

    if not enrolled:
        return {
            "school_id": school_id, "period": period,
            "enrolled_students": 0, "active_students_period": 0,
            "active_pct": 0.0, "lessons_viewed": 0, "quiz_attempts": 0,
            "first_attempt_pass_rate_pct": 0.0, "audio_play_rate_pct": 0.0,
            "units_with_struggles": [], "units_no_activity": [],
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
        start, *id_uuids,
    )
    active_students = active_row["active_students"] or 0
    lessons_viewed  = active_row["lessons_viewed"] or 0
    audio_plays     = active_row["audio_plays"] or 0

    # Quiz attempts + pass rates in period
    quiz_row = await conn.fetchrow(
        f"""
        SELECT
            COUNT(*) AS quiz_attempts,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE attempt_number = 1 AND passed AND completed)
                / NULLIF(COUNT(DISTINCT student_id) FILTER (WHERE attempt_number = 1 AND completed), 0),
                1
            ) AS first_attempt_pass_rate_pct
        FROM progress_sessions
        WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[])
          AND started_at >= $1
        """,
        start, *id_uuids,
    )
    quiz_attempts      = quiz_row["quiz_attempts"] or 0
    pass_rate          = float(quiz_row["first_attempt_pass_rate_pct"] or 0)

    # Audio play rate
    audio_rate = round(100.0 * audio_plays / lessons_viewed, 1) if lessons_viewed else 0.0

    # Units with struggle (all time for the school)
    struggle_rows = await conn.fetch(
        f"""
        SELECT unit_id,
               ROUND(
                   100.0 * COUNT(*) FILTER (WHERE attempt_number = 1 AND passed AND completed)
                   / NULLIF(COUNT(DISTINCT student_id) FILTER (WHERE attempt_number = 1 AND completed), 0),
                   1
               ) AS first_pass_rate,
               ROUND(AVG(attempt_number) FILTER (WHERE passed AND completed)::numeric, 1) AS avg_att
        FROM progress_sessions
        WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[])
          AND started_at >= $1
        GROUP BY unit_id
        """,
        start, *id_uuids,
    )
    units_with_struggles = [
        r["unit_id"] for r in struggle_rows
        if (float(r["first_pass_rate"] or 0) < _STRUGGLE_PASS or float(r["avg_att"] or 1) > _STRUGGLE_ATT)
    ]

    # Units with NO activity in period
    active_units = {r["unit_id"] for r in struggle_rows}
    all_unit_rows = await conn.fetch(
        f"""
        SELECT DISTINCT unit_id FROM lesson_views
        WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[])
          AND started_at < $1
        """,
        start, *id_uuids,
    )
    ever_active_units = {r["unit_id"] for r in all_unit_rows}
    units_no_activity = sorted(ever_active_units - active_units)

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
) -> dict:
    """Per-unit deep-dive for enrolled students in the period."""
    start = _period_start(period)
    enrolled = await _enrolled_ids(conn, school_id)
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
        unit_id, start, *id_uuids,
    )
    students_viewed = lv_row["students_viewed"] or 0
    total_views     = lv_row["total_views"] or 0
    avg_duration    = float(lv_row["avg_duration_s"] or 0)
    audio_plays     = lv_row["audio_plays"] or 0
    exp_views       = lv_row["exp_views"] or 0
    audio_rate      = round(100.0 * audio_plays / total_views, 1) if total_views else 0.0
    exp_rate        = round(100.0 * exp_views / total_views, 1) if total_views else None

    # Quiz stats
    quiz_rows = await conn.fetch(
        f"""
        SELECT student_id::text, attempt_number, score, passed, completed
        FROM progress_sessions
        WHERE unit_id = $1
          AND started_at >= $2
          AND student_id = ANY(ARRAY[{placeholders}]::uuid[])
        """,
        unit_id, start, *id_uuids,
    )
    students_attempted = len({r["student_id"] for r in quiz_rows if r["completed"]})
    first_pass = sum(
        1 for r in quiz_rows
        if r["attempt_number"] == 1 and r["passed"] and r["completed"]
    )
    first_attempt_students = len({
        r["student_id"] for r in quiz_rows if r["attempt_number"] == 1 and r["completed"]
    })
    pass_rate = round(100.0 * first_pass / first_attempt_students, 1) if first_attempt_students else 0.0

    completed_rows = [r for r in quiz_rows if r["completed"]]
    avg_score = round(
        sum(r["score"] for r in completed_rows if r["score"] is not None) / len(completed_rows), 1
    ) if completed_rows else 0.0

    # Average attempts to pass
    passed_students: dict[str, int] = {}
    for r in quiz_rows:
        if r["passed"] and r["completed"]:
            sid = r["student_id"]
            passed_students[sid] = max(passed_students.get(sid, 0), r["attempt_number"])
    avg_att = round(sum(passed_students.values()) / len(passed_students), 1) if passed_students else 0.0

    # Attempt distribution
    att_counts: dict[str, int] = {}
    for r in quiz_rows:
        if r["completed"]:
            sid = r["student_id"]
            att_counts[sid] = max(att_counts.get(sid, 0), r["attempt_number"])
    dist = {"one": 0, "two": 0, "three": 0, "four_plus": 0}
    for v in att_counts.values():
        if v == 1:   dist["one"] += 1
        elif v == 2: dist["two"] += 1
        elif v == 3: dist["three"] += 1
        else:        dist["four_plus"] += 1

    struggle_flag = pass_rate < _STRUGGLE_PASS or avg_att > _STRUGGLE_ATT

    # Feedback for this unit from enrolled students
    fb_placeholders = ", ".join(f"${i + 2}" for i in range(len(id_uuids)))
    fb_rows = await conn.fetch(
        f"""
        SELECT feedback_id::text, category, rating, message, submitted_at
        FROM feedback
        WHERE unit_id = $1
          AND student_id = ANY(ARRAY[{fb_placeholders}]::uuid[])
        ORDER BY submitted_at DESC
        LIMIT 3
        """,
        unit_id, *id_uuids,
    )
    fb_count_row = await conn.fetchrow(
        f"""
        SELECT COUNT(*) AS cnt, ROUND(AVG(rating)::numeric, 1) AS avg_rating
        FROM feedback
        WHERE unit_id = $1 AND student_id = ANY(ARRAY[{fb_placeholders}]::uuid[])
        """,
        unit_id, *id_uuids,
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
        "quiz_attempt_pct": round(100.0 * students_attempted / n_enrolled, 1) if n_enrolled else 0.0,
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
        "school_id": school_id, "unit_id": unit_id, "period": period,
        "students_viewed_lesson": 0, "lesson_view_pct": 0.0,
        "avg_lesson_duration_s": 0.0, "audio_play_rate_pct": 0.0,
        "experiment_view_pct": None, "students_attempted_quiz": 0,
        "quiz_attempt_pct": 0.0, "first_attempt_pass_rate_pct": 0.0,
        "avg_score_pct": 0.0, "avg_attempts_to_pass": 0.0,
        "attempt_distribution": {"one": 0, "two": 0, "three": 0, "four_plus": 0},
        "struggle_flag": False, "feedback_count": 0, "avg_rating": None,
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
        uuid.UUID(school_id), uuid.UUID(student_id),
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
    first_pass_count = summary["first_pass"] or 0
    first_att = summary["first_att_students"] or 0  # should be unique per unit
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
    first_pass_rate = round(
        100.0 * (first_att_row["passed"] or 0) / (first_att_row["total"] or 1), 1
    ) if (first_att_row["total"] or 0) > 0 else 0.0

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

    # Per-unit breakdown
    unit_rows = await conn.fetch(
        """
        SELECT
            ps.unit_id,
            ps.subject,
            MAX(ps.attempt_number)                               AS quiz_attempts,
            MAX(ps.score) FILTER (WHERE ps.completed)            AS best_score,
            BOOL_OR(ps.passed)                                   AS passed,
            COUNT(DISTINCT lv.view_id) > 0                       AS lesson_viewed,
            ROUND(AVG(lv.duration_s)::numeric, 1)                AS avg_duration_s
        FROM progress_sessions ps
        LEFT JOIN lesson_views lv ON lv.student_id = ps.student_id AND lv.unit_id = ps.unit_id
        WHERE ps.student_id = $1
        GROUP BY ps.unit_id, ps.subject
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

    per_unit = [
        {
            "unit_id": r["unit_id"],
            "unit_name": unit_names.get(r["unit_id"]),
            "subject": r["subject"],
            "lesson_viewed": bool(r["lesson_viewed"]),
            "quiz_attempts": r["quiz_attempts"] or 0,
            "best_score": float(r["best_score"]) if r["best_score"] is not None else None,
            "passed": bool(r["passed"]),
            "avg_duration_s": float(r["avg_duration_s"] or 0),
        }
        for r in unit_rows
    ]

    # Strongest / needs-attention subject
    subj_scores: dict[str, list[float]] = {}
    for r in unit_rows:
        s = r["subject"]
        if r["best_score"] is not None:
            subj_scores.setdefault(s, []).append(float(r["best_score"]))
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
) -> dict:
    """All units ranked by health tier."""
    enrolled = await _enrolled_ids(conn, school_id)
    if not enrolled:
        return {
            "school_id": school_id, "total_units": 0,
            "healthy_count": 0, "watch_count": 0,
            "struggling_count": 0, "no_activity_count": 0,
            "units": [],
        }

    id_uuids = [uuid.UUID(s) for s in enrolled]
    placeholders = ", ".join(f"${i + 1}" for i in range(len(id_uuids)))

    # All units these students have interacted with
    rows = await conn.fetch(
        f"""
        SELECT
            ps.unit_id,
            ps.subject,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE ps.attempt_number = 1 AND ps.passed AND ps.completed)
                / NULLIF(COUNT(DISTINCT ps.student_id) FILTER (WHERE ps.attempt_number = 1 AND ps.completed), 0),
                1
            )                                                   AS first_pass_rate,
            ROUND(AVG(ps.score) FILTER (WHERE ps.completed)::numeric, 1) AS avg_score,
            ROUND(AVG(ps.attempt_number) FILTER (WHERE ps.passed AND ps.completed)::numeric, 1) AS avg_att,
            COUNT(DISTINCT lv.view_id) > 0                      AS has_lesson_view
        FROM progress_sessions ps
        LEFT JOIN lesson_views lv ON lv.student_id = ps.student_id AND lv.unit_id = ps.unit_id
        WHERE ps.student_id = ANY(ARRAY[{placeholders}]::uuid[])
        GROUP BY ps.unit_id, ps.subject
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

    units = []
    counts = {"healthy": 0, "watch": 0, "struggling": 0, "no_activity": 0}
    for r in rows:
        pass_rate  = float(r["first_pass_rate"] or 0)
        avg_att    = float(r["avg_att"] or 0)
        avg_score  = float(r["avg_score"] or 0)
        has_lv     = bool(r["has_lesson_view"])
        tier       = _health_tier(pass_rate, avg_att, has_lv)
        action     = _recommended_action(tier)
        counts[tier] += 1
        fb = fb_map.get(r["unit_id"])
        units.append({
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
        })

    return {
        "school_id": school_id,
        "total_units": len(units),
        "healthy_count":     counts["healthy"],
        "watch_count":       counts["watch"],
        "struggling_count":  counts["struggling"],
        "no_activity_count": counts["no_activity"],
        "units": units,
    }


# ── Report 5: Feedback Report ─────────────────────────────────────────────────

async def get_feedback_report(
    conn: asyncpg.Connection,
    school_id: str,
    unit_id: Optional[str] = None,
    category: Optional[str] = None,
    reviewed: Optional[bool] = None,
    sort: str = "recent",
) -> dict:
    """Feedback from enrolled students, grouped by unit."""
    enrolled = await _enrolled_ids(conn, school_id)
    if not enrolled:
        return {
            "school_id": school_id,
            "total_feedback_count": 0,
            "unreviewed_count": 0,
            "avg_rating_overall": None,
            "by_unit": [],
        }

    id_uuids = [uuid.UUID(s) for s in enrolled]
    placeholders = ", ".join(f"${i + 1}" for i in range(len(id_uuids)))

    # Summary
    summary = await conn.fetchrow(
        f"""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE NOT reviewed) AS unreviewed,
               ROUND(AVG(rating)::numeric, 1) AS avg_rating
        FROM feedback
        WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[])
        """,
        *id_uuids,
    )

    # Per-unit breakdown
    unit_ids_fb = await conn.fetch(
        f"""
        SELECT DISTINCT COALESCE(unit_id, '') AS unit_id
        FROM feedback
        WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[])
          AND unit_id IS NOT NULL
        """,
        *id_uuids,
    )
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    by_unit = []
    for row in unit_ids_fb:
        uid = row["unit_id"]
        if unit_id and uid != unit_id:
            continue

        # Build filter clause
        extra = []
        extra_params: list = [*id_uuids, uid]
        if category:
            extra.append(f"AND category = ${len(extra_params) + 1}")
            extra_params.append(category)
        if reviewed is not None:
            extra.append(f"AND reviewed = ${len(extra_params) + 1}")
            extra_params.append(reviewed)
        extra_sql = " ".join(extra)

        items = await conn.fetch(
            f"""
            SELECT feedback_id::text, category, rating, message, submitted_at, reviewed
            FROM feedback
            WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[])
              AND unit_id = ${len(id_uuids) + 1}
              {extra_sql}
            ORDER BY submitted_at {'ASC' if sort == 'oldest' else 'DESC'}
            """,
            *extra_params,
        )

        cat_counts = await conn.fetchrow(
            f"""
            SELECT
                COUNT(*) FILTER (WHERE category = 'content') AS content,
                COUNT(*) FILTER (WHERE category = 'ux') AS ux,
                COUNT(*) FILTER (WHERE category = 'general') AS general,
                COUNT(*) FILTER (WHERE submitted_at >= ${len(id_uuids) + 2}) AS recent_7d
            FROM feedback
            WHERE student_id = ANY(ARRAY[{placeholders}]::uuid[]) AND unit_id = ${len(id_uuids) + 1}
            """,
            *id_uuids, uid, seven_days_ago,
        )

        # unit_name lookup
        name_row = await conn.fetchrow(
            "SELECT unit_name FROM curriculum_units WHERE unit_id = $1 LIMIT 1", uid
        )
        unit_name = name_row["unit_name"] if name_row else None

        by_unit.append({
            "unit_id": uid,
            "unit_name": unit_name,
            "feedback_count": len(items),
            "category_breakdown": {
                "content": cat_counts["content"] or 0,
                "ux": cat_counts["ux"] or 0,
                "general": cat_counts["general"] or 0,
            },
            "trending": (cat_counts["recent_7d"] or 0) > 3,
            "feedback_items": [
                {
                    "feedback_id": r["feedback_id"],
                    "category": r["category"],
                    "rating": r["rating"],
                    "message": r["message"],
                    "submitted_at": r["submitted_at"],
                    "reviewed": r["reviewed"],
                }
                for r in items
            ],
        })

    return {
        "school_id": school_id,
        "total_feedback_count": summary["total"] or 0,
        "unreviewed_count": summary["unreviewed"] or 0,
        "avg_rating_overall": float(summary["avg_rating"]) if summary["avg_rating"] else None,
        "by_unit": by_unit,
    }


# ── Report 6: Trends ──────────────────────────────────────────────────────────

async def get_trends(
    conn: asyncpg.Connection,
    school_id: str,
    period: str,
) -> dict:
    """Week-over-week trend data for enrolled students."""
    n_weeks = _trend_weeks(period)
    now = datetime.now(timezone.utc)

    enrolled = await _enrolled_ids(conn, school_id)
    id_uuids = [uuid.UUID(s) for s in enrolled]
    # Placeholders for student IDs starting at $3 (after week_start=$1 and week_end=$2).
    # For empty enrollment ARRAY[]::uuid[] is used — PostgreSQL returns 0 counts correctly.
    id_placeholders = ", ".join(f"${i + 3}" for i in range(len(id_uuids)))
    enrolled_filter = f"AND student_id = ANY(ARRAY[{id_placeholders}]::uuid[])" if id_uuids else "AND FALSE"

    weeks = []
    for i in range(n_weeks - 1, -1, -1):
        week_end   = now - timedelta(weeks=i)
        week_start = week_end - timedelta(weeks=1)

        lv_row = await conn.fetchrow(
            f"""
            SELECT COUNT(DISTINCT student_id) AS active,
                   COUNT(*) AS views,
                   COUNT(*) FILTER (WHERE audio_played) AS audio
            FROM lesson_views
            WHERE started_at >= $1 AND started_at < $2
              {enrolled_filter}
            """,
            week_start, week_end, *id_uuids,
        )
        ps_row = await conn.fetchrow(
            f"""
            SELECT COUNT(*) AS attempts,
                   ROUND(AVG(score) FILTER (WHERE completed)::numeric, 1) AS avg_score,
                   ROUND(
                       100.0 * COUNT(*) FILTER (WHERE attempt_number = 1 AND passed AND completed)
                       / NULLIF(COUNT(DISTINCT student_id) FILTER (WHERE attempt_number = 1 AND completed), 0),
                       1
                   ) AS pass_rate
            FROM progress_sessions
            WHERE started_at >= $1 AND started_at < $2
              {enrolled_filter}
            """,
            week_start, week_end, *id_uuids,
        )
        weeks.append({
            "week_start": week_start.strftime("%Y-%m-%d"),
            "active_students": lv_row["active"] or 0,
            "lessons_viewed":  lv_row["views"] or 0,
            "quiz_attempts":   ps_row["attempts"] or 0,
            "avg_score_pct":   float(ps_row["avg_score"] or 0),
            "first_attempt_pass_rate_pct": float(ps_row["pass_rate"] or 0),
        })

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
    from src.auth.tasks import celery_app

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
) -> dict:
    """Return unacknowledged alerts for the school."""
    rows = await conn.fetch(
        """
        SELECT alert_id::text, alert_type, school_id::text, details, triggered_at, acknowledged
        FROM report_alerts
        WHERE school_id = $1 AND NOT acknowledged
        ORDER BY triggered_at DESC
        """,
        uuid.UUID(school_id),
    )
    return {
        "alerts": [
            {
                "alert_id": r["alert_id"],
                "alert_type": r["alert_type"],
                "school_id": r["school_id"],
                "details": r["details"],
                "triggered_at": r["triggered_at"],
                "acknowledged": r["acknowledged"],
            }
            for r in rows
        ]
    }


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
        settings.get("pass_rate_threshold", 50.0),
        settings.get("feedback_count_threshold", 3),
        settings.get("inactive_days_threshold", 14),
        settings.get("score_drop_threshold", 10.0),
        settings.get("new_feedback_immediate", True),
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
        "refreshed_at": datetime.now(timezone.utc),
        "views_refreshed": views,
    }
