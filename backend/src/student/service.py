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

from src.core.subjects import display_subject, resolve_subject_labels
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


async def get_dashboard(
    conn: asyncpg.Connection,
    redis,
    student_id: str,
    *,
    pool=None,
    grade: int | None = None,
) -> dict:
    """
    Return dashboard payload.

    Read order:
      1. L1 TTLCache (per-worker, in-process, 60 s) — zero network cost
      2. L2 Redis (shared, 60 s) — single network hop
      3. DB aggregation — falls back and repopulates both caches

    `pool` and `grade` are what let the build resolve the student's curriculum
    properly (see `_build_dashboard`). Both are optional so existing callers and
    tests keep working; without them the build falls back to the curricula the
    student has already touched, which is the pre-#640 behaviour.
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
    payload = await _build_dashboard(conn, redis, student_id, pool=pool, grade=grade)
    dashboard_cache[student_id] = payload
    await redis.setex(cache_key, _DASHBOARD_TTL, json.dumps(payload))
    return payload


# Minimum number of students with scores before a class average is shown.
#
# This is a privacy control, not a noise threshold. The dashboard shows the
# student their own average beside the cohort's; with a cohort of two, "you 80,
# class 70" tells the student the other member scored exactly 60. Small cohorts
# make an aggregate a lookup of one individual's educational record, which is
# the disclosure FERPA is about. Five is the smallest that keeps any single
# member's score genuinely underdetermined.
#
# Below the threshold the standing block is omitted entirely rather than shown
# empty — a tile explaining why it cannot compare you is worse than no tile.
_MIN_COHORT_FOR_STANDING = 5


async def _resolve_dashboard_curriculum(
    conn: asyncpg.Connection,
    redis,
    student_id: str,
    pool,
    grade: int | None,
) -> str | None:
    """Return the curriculum whose units this student's dashboard measures.

    Calls `resolve_curriculum_id` — the same three-step resolution that decides
    which content the student is actually SERVED (school-owned → classroom
    package → `default-{year}-g{grade}`) — then swaps a school fork for its
    source, because a fork carries no rows in `curriculum_units`.

    The dashboard previously derived the curriculum as "any curriculum I already
    have a session or a lesson view in". That is pitfall #31, and it fails in
    the two states §4.2 of the dashboard design calls the common ones:

      - a BRAND NEW student has no sessions, so nothing matched and every
        subject tile rendered empty — blankest for the student who most needs
        direction;
      - a student on a school FORK matched the fork, which holds no units.

    Returns None when there is nothing to resolve against (no grade available),
    leaving the caller to fall back.
    """
    if pool is None or grade is None:
        return None

    from src.content.service import resolve_curriculum_id

    school_row = await conn.fetchrow(
        "SELECT school_id FROM students WHERE student_id = $1", student_id
    )
    school_id = str(school_row["school_id"]) if school_row and school_row["school_id"] else None

    curriculum_id = await resolve_curriculum_id(student_id, grade, pool, redis, school_id=school_id)

    # Fork → source. `resolve_content_curriculum` is keyed by a unit, and we do
    # not have one yet, so borrow any unit of the fork; when the fork has none
    # (the normal case) fall back to its source_curriculum_id directly.
    source = await conn.fetchval(
        "SELECT source_curriculum_id FROM curricula WHERE curriculum_id = $1", curriculum_id
    )
    if source:
        has_own = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM curriculum_units WHERE curriculum_id = $1)",
            curriculum_id,
        )
        if not has_own:
            return source
    return curriculum_id


async def _build_dashboard(
    conn: asyncpg.Connection,
    redis,
    student_id: str,
    *,
    pool=None,
    grade: int | None = None,
) -> dict:
    # ── Summary stats ──────────────────────────────────────────────────────
    stats_row = await conn.fetchrow(
        """
        SELECT
            COUNT(DISTINCT CASE WHEN passed = TRUE THEN unit_id END)    AS units_completed,
            COUNT(CASE WHEN completed = TRUE AND passed = TRUE THEN 1 END) AS quizzes_passed,
            -- Questions right over questions answered (#669). This was an
            -- unweighted mean of per-session percentages while /analytics/
            -- student/stats used a mean of per-DAY means and the per-subject
            -- cards below already used the weighted form — three definitions
            -- of "average score" across two screens, which is what made the
            -- dashboard read 61.8% beside My Stats' 62%.
            SUM(score) FILTER (WHERE completed = TRUE AND score IS NOT NULL)
                AS score_sum,
            SUM(total_questions) FILTER (WHERE completed = TRUE AND score IS NOT NULL)
                AS question_sum
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
    #
    # Answers question 3 of the dashboard design: "my subjects and scores".
    #
    # Measured against the curriculum the student is actually SERVED, resolved
    # once (see _resolve_dashboard_curriculum) rather than inferred from the
    # curricula they happen to have touched.
    curriculum_id = await _resolve_dashboard_curriculum(conn, redis, student_id, pool, grade)

    if curriculum_id:
        unit_rows = await conn.fetch(
            """
            -- The child table is aggregated to one row per unit BEFORE the join.
            -- Joining progress_sessions directly fans the curriculum row out
            -- once per attempt, which silently multiplies counts and corrupts
            -- averages — the defect behind #624/#625.
            WITH unit_stats AS (
                SELECT unit_id,
                       BOOL_OR(passed)      AS ever_passed,
                       SUM(score)           AS score_sum,
                       SUM(total_questions) AS question_sum
                FROM progress_sessions
                WHERE student_id = $1 AND completed = TRUE
                GROUP BY unit_id
            )
            SELECT cu.unit_id, cu.subject, cu.title, cu.sort_order,
                   COALESCE(us.ever_passed, FALSE) AS ever_passed,
                   us.score_sum,
                   us.question_sum
            FROM curriculum_units cu
            -- Joined on unit_id alone: the student's sessions may carry the
            -- FORK's curriculum_id while cu rows live under the source.
            LEFT JOIN unit_stats us ON us.unit_id = cu.unit_id
            WHERE cu.curriculum_id = $2
            ORDER BY cu.sort_order
            """,
            student_id,
            curriculum_id,
        )
    else:
        unit_rows = []

    # Display names, not codes: stream curricula store subject CODES in
    # curriculum_units.subject (G11-PHYS), with the readable name living in
    # content_subject_versions.subject_name (pitfall #32).
    subject_labels = await resolve_subject_labels(conn, [r["unit_id"] for r in unit_rows])

    by_subject: dict[str, dict] = {}
    for r in unit_rows:
        label = display_subject(subject_labels, r["unit_id"], r["subject"])
        agg = by_subject.setdefault(
            label, {"units_total": 0, "units_completed": 0, "score_sum": 0, "question_sum": 0}
        )
        agg["units_total"] += 1
        if r["ever_passed"]:
            agg["units_completed"] += 1
        agg["score_sum"] += int(r["score_sum"] or 0)
        agg["question_sum"] += int(r["question_sum"] or 0)

    subject_progress = [
        {
            "subject": label,
            "units_total": agg["units_total"],
            "units_completed": agg["units_completed"],
            "pct": round(agg["units_completed"] / agg["units_total"] * 100, 1)
            if agg["units_total"]
            else 0.0,
            # Questions right out of questions answered, across every completed
            # quiz in the subject. None — not 0 — when nothing has been
            # answered yet, so the UI can say "not started" instead of showing
            # a student a 0% they did not earn.
            "avg_score": round(agg["score_sum"] / agg["question_sum"] * 100, 1)
            if agg["question_sum"]
            else None,
        }
        for label, agg in sorted(by_subject.items())
    ]

    # ── Next unit ──────────────────────────────────────────────────────────
    #
    # Half of question 1, "what am I doing this week". The other half — am I on
    # PACE — needs the academic calendar (ADR-007) and is deliberately absent
    # rather than approximated.
    #
    # Comes from the rows already fetched: the first unit in curriculum order
    # the student has not yet passed. No second query, and no second definition
    # of done — the same `ever_passed` that fed the subject tiles.
    next_unit = None
    for r in unit_rows:
        if not r["ever_passed"]:
            next_unit = {
                "unit_id": r["unit_id"],
                "title": r["title"] or r["unit_id"],
                "subject": display_subject(subject_labels, r["unit_id"], r["subject"]),
                "estimated_minutes": 20,
            }
            break

    # ── Standing against the class ─────────────────────────────────────────
    standing = await _build_standing(conn, student_id, grade)

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
            "avg_quiz_score": (
                round(int(stats_row["score_sum"]) / int(stats_row["question_sum"]) * 100, 1)
                if stats_row["question_sum"]
                else 0.0
            ),
        },
        "subject_progress": subject_progress,
        "next_unit": next_unit,
        "standing": standing,
        "recent_activity": recent,
    }


async def _build_standing(
    conn: asyncpg.Connection, student_id: str, grade: int | None
) -> dict | None:
    """The student's average score beside their grade cohort's.

    Question 4 of the dashboard design. "Class" means the **grade cohort at
    their school**, not their classroom — decided in §9, because a classroom is
    a teaching group that a student may belong to several of (or none), which
    makes it an unstable thing to be ranked within.

    Returns None — the tile is not drawn at all — when the student has no
    school, no scores of their own, or the cohort is too small to aggregate
    without disclosing an individual's record (see _MIN_COHORT_FOR_STANDING).

    Both averages are questions-right over questions-answered. Deliberately NOT
    an average of per-session percentages: that weights a 4-question quiz the
    same as a 20-question one, which is the flaw still present in the older
    /analytics/student/stats average.
    """
    if grade is None:
        return None

    row = await conn.fetchrow("SELECT school_id FROM students WHERE student_id = $1", student_id)
    if not row or not row["school_id"]:
        return None

    # Cohort membership comes from school_enrolments, the authority for "which
    # grade at THIS school" (#572/#576) — students.grade is the student's own
    # and can differ between the schools they attend.
    stats = await conn.fetch(
        """
        WITH cohort AS (
            SELECT se.student_id
            FROM school_enrolments se
            WHERE se.school_id = $1 AND se.status = 'active' AND se.grade = $2
        ),
        per_student AS (
            SELECT ps.student_id,
                   SUM(ps.score)::float / NULLIF(SUM(ps.total_questions), 0) AS avg_frac
            FROM progress_sessions ps
            WHERE ps.student_id IN (SELECT student_id FROM cohort)
              AND ps.completed = TRUE AND ps.score IS NOT NULL
            GROUP BY ps.student_id
        )
        SELECT student_id, avg_frac FROM per_student WHERE avg_frac IS NOT NULL
        """,
        row["school_id"],
        grade,
    )

    if len(stats) < _MIN_COHORT_FOR_STANDING:
        return None

    mine = next((r["avg_frac"] for r in stats if str(r["student_id"]) == str(student_id)), None)
    if mine is None:
        return None

    return {
        "you": round(mine * 100, 1),
        "cohort": round(sum(r["avg_frac"] for r in stats) / len(stats) * 100, 1),
        "cohort_size": len(stats),
        "grade": grade,
    }


# ── Progress map ──────────────────────────────────────────────────────────────


async def get_progress_map(
    conn: asyncpg.Connection,
    student_id: str,
    *,
    redis=None,
    pool=None,
    grade: int | None = None,
) -> dict:
    """
    Return the curriculum map with per-unit status badges.
    Reads from mv_student_curriculum_progress.

    Curriculum resolution goes through the shared resolver when the caller can
    supply what it needs. This used to pick "any curriculum I have touched,
    LIMIT 1" — pitfall #31 again, and the same defect fixed on the dashboard in
    #640: a brand-new student matched nothing and saw an empty map, and a
    student on a school fork matched a curriculum holding no units.

    It mattered less while nothing called this endpoint. #677 points the
    Subjects page and the Curriculum Map at it, so it matters now.
    """
    curriculum_id = await _resolve_dashboard_curriculum(conn, redis, student_id, pool, grade)

    if not curriculum_id:
        # Fall back to the old behaviour when the caller cannot supply the
        # resolver's inputs, rather than returning nothing to existing callers.
        touched = await conn.fetch(
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
        if not touched:
            return {
                "curriculum_id": "",
                "pending_count": 0,
                "needs_retry_count": 0,
                "subjects": [],
            }
        curriculum_id = touched[0]["curriculum_id"]

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
