"""
backend/src/student/service.py

Aggregation logic for student dashboard, progress map, and stats endpoints.

Caching:
  Dashboard:    L1 TTLCache (60 s) keyed by student_id (per worker);
                L2 Redis (60 s) keyed by "dashboard:{student_id}".
  Progress map: backed by mv_student_curriculum_progress (materialized view);
                no extra caching layer — the view itself is fast.
  Stats:        computed on demand; no cache (low read frequency).

Streak:
  Stored in Redis as JSON at "streak:{student_id}":
    {current: int, longest: int, last_active_date: "YYYY-MM-DD"}
  Updated by the update_streak_task Celery task (called from session/end).
"""

from __future__ import annotations

import json
from datetime import date

import asyncpg

from src.utils.logger import get_logger

log = get_logger("student")

QUIZ_PASS_THRESHOLD = 0.60


# ── Streak helpers ────────────────────────────────────────────────────────────


async def get_streak(redis, student_id: str) -> dict:
    """Read streak data from Redis.  Returns default if absent."""
    raw = await redis.get(f"streak:{student_id}")
    if raw:
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            pass
    return {"current": 0, "longest": 0, "last_active_date": None}


async def update_streak(redis, student_id: str, activity_date: str) -> dict:
    """
    Update streak in Redis for a given activity date.

    Rules:
    - If activity_date == last_active_date: no change (idempotent).
    - If activity_date == last_active_date + 1 day: increment current streak.
    - Otherwise (gap > 1 day): reset current to 1.
    - Always update longest if current > longest.
    - Always update last_active_date.
    """
    streak = await get_streak(redis, student_id)
    last = streak.get("last_active_date")

    if last == activity_date:
        return streak  # Already counted today

    current = streak.get("current", 0)
    longest = streak.get("longest", 0)

    if last is not None:
        try:
            last_date = date.fromisoformat(last)
            today_date = date.fromisoformat(activity_date)
            delta = (today_date - last_date).days
            if delta == 1:
                current += 1
            else:
                current = 1
        except ValueError:
            current = 1
    else:
        current = 1

    if current > longest:
        longest = current

    streak = {"current": current, "longest": longest, "last_active_date": activity_date}
    await redis.setex(f"streak:{student_id}", 60 * 60 * 24 * 90, json.dumps(streak))  # 90d TTL
    return streak


# ── Dashboard ─────────────────────────────────────────────────────────────────

_DASHBOARD_TTL = 60  # seconds (L1 + L2)


async def get_dashboard(conn: asyncpg.Connection, redis, student_id: str) -> dict:
    """
    Return dashboard payload.

    Read order:
      1. L1 TTLCache (per-worker, in-process, 60 s) — zero network cost
      2. L2 Redis (shared, 60 s) — single network hop
      3. DB aggregation — falls back and repopulates both caches
    """
    from src.core.cache import dashboard_cache

    # ── L1 check ──────────────────────────────────────────────────────────────
    cached_l1 = dashboard_cache.get(student_id)
    if cached_l1 is not None:
        return cached_l1

    # ── L2 check ──────────────────────────────────────────────────────────────
    cache_key = f"dashboard:{student_id}"
    raw_l2 = await redis.get(cache_key)
    if raw_l2:
        try:
            payload = json.loads(raw_l2)
            dashboard_cache[student_id] = payload  # backfill L1
            return payload
        except (ValueError, TypeError):
            pass

    # ── DB aggregation ────────────────────────────────────────────────────────
    payload = await _build_dashboard(conn, redis, student_id)
    dashboard_cache[student_id] = payload
    await redis.setex(cache_key, _DASHBOARD_TTL, json.dumps(payload))
    return payload


async def _build_dashboard(conn: asyncpg.Connection, redis, student_id: str) -> dict:
    # ── Summary stats ──────────────────────────────────────────────────────
    stats_row = await conn.fetchrow(
        """
        SELECT
            COUNT(DISTINCT CASE WHEN passed = TRUE THEN unit_id END)    AS units_completed,
            COUNT(CASE WHEN completed = TRUE AND passed = TRUE THEN 1 END) AS quizzes_passed,
            AVG(CASE WHEN completed = TRUE THEN score::float / NULLIF(total_questions, 0) * 100 END) AS avg_pct
        FROM progress_sessions
        WHERE student_id = $1
        """,
        student_id,
    )

    view_mins_row = await conn.fetchrow(
        """
        SELECT COALESCE(SUM(duration_s), 0) / 60 AS total_minutes
        FROM lesson_views
        WHERE student_id = $1
        """,
        student_id,
    )

    streak = await get_streak(redis, student_id)

    # ── Subject progress ───────────────────────────────────────────────────
    subject_rows = await conn.fetch(
        """
        SELECT
            cu.subject,
            COUNT(DISTINCT cu.unit_id)                                          AS units_total,
            COUNT(DISTINCT CASE WHEN mv.status = 'completed' THEN cu.unit_id END) AS units_completed
        FROM curriculum_units cu
        LEFT JOIN mv_student_curriculum_progress mv
            ON mv.unit_id = cu.unit_id AND mv.curriculum_id = cu.curriculum_id
               AND mv.student_id = $1
        WHERE cu.curriculum_id IN (
            SELECT DISTINCT curriculum_id FROM progress_sessions WHERE student_id = $1
            UNION
            SELECT DISTINCT curriculum_id FROM lesson_views WHERE student_id = $1
        )
        GROUP BY cu.subject
        ORDER BY cu.subject
        """,
        student_id,
    )

    subject_progress = [
        {
            "subject": r["subject"],
            "units_total": r["units_total"],
            "units_completed": r["units_completed"],
            "pct": round(r["units_completed"] / r["units_total"] * 100, 1)
            if r["units_total"]
            else 0.0,
        }
        for r in subject_rows
    ]

    # ── Next unit ──────────────────────────────────────────────────────────
    next_unit_row = await conn.fetchrow(
        """
        SELECT cu.unit_id, cu.title, cu.subject
        FROM curriculum_units cu
        LEFT JOIN mv_student_curriculum_progress mv
            ON mv.unit_id = cu.unit_id AND mv.curriculum_id = cu.curriculum_id
               AND mv.student_id = $1
        WHERE (mv.status IS NULL OR mv.status IN ('not_started', 'needs_retry', 'in_progress'))
          AND cu.curriculum_id IN (
              SELECT DISTINCT curriculum_id FROM progress_sessions WHERE student_id = $1
              UNION
              SELECT DISTINCT curriculum_id FROM lesson_views WHERE student_id = $1
          )
        ORDER BY cu.sort_order
        LIMIT 1
        """,
        student_id,
    )

    next_unit = None
    if next_unit_row:
        next_unit = {
            "unit_id": next_unit_row["unit_id"],
            "title": next_unit_row["title"] or next_unit_row["unit_id"],
            "subject": next_unit_row["subject"],
            "estimated_minutes": 20,
        }

    # ── Recent activity ────────────────────────────────────────────────────
    quiz_activity = await conn.fetch(
        """
        SELECT 'quiz' AS type, ps.unit_id,
               COALESCE(cu.title, ps.unit_id) AS title,
               ps.score,
               ps.ended_at AS at
        FROM progress_sessions ps
        LEFT JOIN curriculum_units cu ON cu.unit_id = ps.unit_id AND cu.curriculum_id = ps.curriculum_id
        WHERE ps.student_id = $1 AND ps.completed = TRUE AND ps.ended_at IS NOT NULL
        ORDER BY ps.ended_at DESC
        LIMIT 5
        """,
        student_id,
    )

    lesson_activity = await conn.fetch(
        """
        SELECT 'lesson' AS type, lv.unit_id,
               COALESCE(cu.title, lv.unit_id) AS title,
               NULL::smallint AS score,
               lv.ended_at AS at
        FROM lesson_views lv
        LEFT JOIN curriculum_units cu ON cu.unit_id = lv.unit_id AND cu.curriculum_id = lv.curriculum_id
        WHERE lv.student_id = $1 AND lv.ended_at IS NOT NULL
        ORDER BY lv.ended_at DESC
        LIMIT 5
        """,
        student_id,
    )

    recent: list[dict] = []
    for r in list(quiz_activity) + list(lesson_activity):
        at_val = r["at"]
        recent.append(
            {
                "type": r["type"],
                "unit_id": r["unit_id"],
                "title": r["title"],
                "score": r["score"],
                "at": at_val.isoformat() if at_val else None,
            }
        )
    recent.sort(key=lambda x: x["at"] or "", reverse=True)
    recent = recent[:5]

    return {
        "summary": {
            "units_completed": stats_row["units_completed"] or 0,
            "quizzes_passed": stats_row["quizzes_passed"] or 0,
            "current_streak_days": streak.get("current", 0),
            "total_time_minutes": int(view_mins_row["total_minutes"] or 0),
            "avg_quiz_score": round(float(stats_row["avg_pct"] or 0), 1),
        },
        "subject_progress": subject_progress,
        "next_unit": next_unit,
        "recent_activity": recent,
    }


# ── Progress map ──────────────────────────────────────────────────────────────


async def get_progress_map(conn: asyncpg.Connection, student_id: str) -> dict:
    """
    Return the curriculum map with per-unit status badges.
    Reads from mv_student_curriculum_progress.
    """
    # Get all curricula this student has interacted with
    curriculum_ids = await conn.fetch(
        """
        SELECT DISTINCT curriculum_id FROM (
            SELECT curriculum_id FROM progress_sessions WHERE student_id = $1
            UNION
            SELECT curriculum_id FROM lesson_views WHERE student_id = $1
        ) t
        LIMIT 1
        """,
        student_id,
    )

    if not curriculum_ids:
        return {"curriculum_id": "", "pending_count": 0, "needs_retry_count": 0, "subjects": []}

    curriculum_id = curriculum_ids[0]["curriculum_id"]

    # All units in this curriculum
    units = await conn.fetch(
        """
        SELECT cu.unit_id, cu.subject, COALESCE(cu.title, cu.unit_id) AS title, cu.sort_order,
               COALESCE(mv.status, 'not_started') AS status,
               mv.best_score,
               mv.attempts,
               mv.last_attempt_at
        FROM curriculum_units cu
        LEFT JOIN mv_student_curriculum_progress mv
            ON mv.unit_id = cu.unit_id AND mv.curriculum_id = cu.curriculum_id
               AND mv.student_id = $1
        WHERE cu.curriculum_id = $2
        ORDER BY cu.subject, cu.sort_order
        """,
        student_id,
        curriculum_id,
    )

    subjects: dict[str, list] = {}
    for u in units:
        subj = u["subject"]
        if subj not in subjects:
            subjects[subj] = []
        subjects[subj].append(
            {
                "unit_id": u["unit_id"],
                "title": u["title"],
                "status": u["status"],
                "best_score": u["best_score"],
                "attempts": u["attempts"] or 0,
                "last_attempt_at": u["last_attempt_at"].isoformat()
                if u["last_attempt_at"]
                else None,
            }
        )

    pending_count = sum(1 for u in units if u["status"] in ("not_started", "in_progress"))
    needs_retry_count = sum(1 for u in units if u["status"] == "needs_retry")

    subjects_list = [
        {
            "subject": subj,
            "units_total": len(unit_list),
            "units_completed": sum(1 for u in unit_list if u["status"] == "completed"),
            "units": unit_list,
        }
        for subj, unit_list in subjects.items()
    ]

    return {
        "curriculum_id": curriculum_id,
        "pending_count": pending_count,
        "needs_retry_count": needs_retry_count,
        "subjects": subjects_list,
    }


# ── Stats ─────────────────────────────────────────────────────────────────────


def _period_days(period: str) -> int | None:
    if period == "7d":
        return 7
    if period == "30d":
        return 30
    return None  # "all"


async def get_stats(conn: asyncpg.Connection, redis, student_id: str, period: str) -> dict:
    """
    Return usage statistics for a period (7d | 30d | all).
    """
    days = _period_days(period)
    if days is not None:
        date_filter = f"AND started_at >= NOW() - INTERVAL '{days} days'"
    else:
        date_filter = ""

    # Quiz stats
    quiz_row = await conn.fetchrow(
        f"""
        SELECT
            COUNT(CASE WHEN completed = TRUE THEN 1 END)           AS quizzes_completed,
            COUNT(CASE WHEN completed = TRUE AND passed = TRUE THEN 1 END) AS quizzes_passed,
            AVG(CASE WHEN completed = TRUE THEN score::float / NULLIF(total_questions, 0) * 100 END) AS avg_pct
        FROM progress_sessions
        WHERE student_id = $1 {date_filter}
        """,
        student_id,
    )

    # Lesson stats
    lesson_row = await conn.fetchrow(
        f"""
        SELECT
            COUNT(*)                              AS lessons_viewed,
            COALESCE(SUM(duration_s), 0) / 60    AS total_minutes,
            COUNT(CASE WHEN audio_played THEN 1 END) AS audio_plays
        FROM lesson_views
        WHERE student_id = $1 {date_filter}
        """,
        student_id,
    )

    # Streak
    streak = await get_streak(redis, student_id)

    # Daily activity
    daily_rows = await conn.fetch(
        f"""
        SELECT
            DATE(started_at)::text AS day,
            COUNT(*) FILTER (WHERE source = 'lesson') AS lessons,
            COUNT(*) FILTER (WHERE source = 'quiz' AND completed) AS quizzes,
            COALESCE(SUM(dur_s), 0) / 60 AS minutes
        FROM (
            SELECT started_at, 'lesson' AS source, duration_s AS dur_s, FALSE AS completed
            FROM lesson_views WHERE student_id = $1 {date_filter}
            UNION ALL
            SELECT started_at, 'quiz' AS source, 0 AS dur_s, completed
            FROM progress_sessions WHERE student_id = $1 {date_filter}
        ) t
        GROUP BY DATE(started_at)
        ORDER BY day DESC
        """,
        student_id,
    )

    daily_activity = [
        {
            "date": r["day"],
            "lessons": r["lessons"] or 0,
            "quizzes": r["quizzes"] or 0,
            "minutes": int(r["minutes"] or 0),
        }
        for r in daily_rows
    ]

    return {
        "period": period,
        "lessons_viewed": lesson_row["lessons_viewed"] or 0,
        "quizzes_completed": quiz_row["quizzes_completed"] or 0,
        "quizzes_passed": quiz_row["quizzes_passed"] or 0,
        "avg_quiz_score": round(float(quiz_row["avg_pct"] or 0), 1),
        "total_time_minutes": int(lesson_row["total_minutes"] or 0),
        "audio_plays": lesson_row["audio_plays"] or 0,
        "streak_current_days": streak.get("current", 0),
        "streak_longest_days": streak.get("longest", 0),
        "daily_activity": daily_activity,
    }
