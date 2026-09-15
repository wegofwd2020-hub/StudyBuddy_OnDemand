"""
backend/src/reports/activity_summary.py

Helper functions to calculate accurate school activity dates for dashboard messages.
Fixes issue where "Open since" and "nothing opened" calculations were incorrect.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import asyncpg

from src.utils.logger import get_logger

log = get_logger("reports.activity_summary")


async def get_school_activity_summary(conn: asyncpg.Connection, school_id: str) -> dict:
    """Get accurate activity dates for school dashboard messages.

    Returns:
        dict: {
            last_activity_date: datetime | None,
            days_since_activity: int | None,
            days_since_created: int,
            school_created_date: datetime,
            last_lesson_date: datetime | None,
            last_quiz_date: datetime | None,
            lesson_views_count: int,
            quiz_sessions_count: int,
        }
    """

    # Get last lesson activity
    last_lesson = await conn.fetchrow(
        """
        SELECT MAX(lv.started_at) as last_lesson,
               COUNT(*) as lesson_views
        FROM lesson_views lv
        INNER JOIN school_enrolments se ON se.student_id = lv.student_id
        WHERE se.school_id = $1 AND se.status = 'active'
        """,
        uuid.UUID(school_id),
    )

    # Get last quiz activity
    last_quiz = await conn.fetchrow(
        """
        SELECT MAX(ps.started_at) as last_quiz,
               COUNT(*) as quiz_sessions
        FROM progress_sessions ps
        INNER JOIN school_enrolments se ON se.student_id = ps.student_id
        WHERE se.school_id = $1 AND se.status = 'active'
        """,
        uuid.UUID(school_id),
    )

    # Get school creation date
    school_created = await conn.fetchrow(
        "SELECT created_at FROM schools WHERE school_id = $1",
        uuid.UUID(school_id),
    )

    if not school_created:
        log.error("school_not_found", extra={"school_id": school_id})
        return {}

    # Determine last activity date
    lesson_date = last_lesson["last_lesson"] if last_lesson else None
    quiz_date = last_quiz["last_quiz"] if last_quiz else None

    # Use the later of the two activities
    last_activity = None
    if lesson_date and quiz_date:
        last_activity = max(lesson_date, quiz_date)
    elif lesson_date:
        last_activity = lesson_date
    elif quiz_date:
        last_activity = quiz_date

    now = datetime.now(UTC)
    days_since_activity = None
    if last_activity:
        days_since_activity = (now - last_activity).days

    days_since_created = (now - school_created["created_at"]).days

    return {
        "last_activity_date": last_activity,
        "days_since_activity": days_since_activity,
        "days_since_created": days_since_created,
        "school_created_date": school_created["created_at"],
        "last_lesson_date": lesson_date,
        "last_quiz_date": quiz_date,
        "lesson_views_count": last_lesson["lesson_views"] if last_lesson else 0,
        "quiz_sessions_count": last_quiz["quiz_sessions"] if last_quiz else 0,
    }


def format_school_activity_message(activity: dict) -> dict:
    """Format school activity into human-readable messages.

    Args:
        activity: Activity summary from get_school_activity_summary

    Returns:
        dict: {
            status: str,
            detail: str,
            is_active: bool,
        }
    """

    if not activity or not activity.get("school_created_date"):
        return {
            "status": "Unknown",
            "detail": "Unable to determine school status.",
            "is_active": False,
        }

    # No activity recorded
    if not activity["last_activity_date"]:
        days_open = activity["days_since_created"]
        return {
            "status": "No activity",
            "detail": f"School created {days_open} days ago - no student activity recorded",
            "is_active": False,
        }

    days_since_activity = activity["days_since_activity"] or 0
    days_since_created = activity["days_since_created"] or 0

    # Active logic - active if activity in last 14 days
    if days_since_activity <= 14:
        if days_since_activity == 0:
            return {
                "status": "Active",
                "detail": "Students active today",
                "is_active": True,
            }
        elif days_since_activity == 1:
            return {
                "status": "Active",
                "detail": "Last activity yesterday",
                "is_active": True,
            }
        else:
            return {
                "status": "Active",
                "detail": f"Last activity {days_since_activity} days ago",
                "is_active": True,
            }

    # Not active logic
    else:
        # Format the date nicely
        activity_date = activity["last_activity_date"]
        if activity_date:
            # Use local timezone for display
            local_date = activity_date.replace(tzinfo=None).date()
            date_str = local_date.strftime("%d %b %Y")
        else:
            date_str = "unknown date"

        # Determine the "open since" message
        if days_since_created < days_since_activity:
            # School is newer than last activity, use school creation date
            created_date = activity["school_created_date"]
            if created_date:
                local_created = created_date.replace(tzinfo=None).date()
                date_str = local_created.strftime("%d %b %Y")

        # "nothing opened" message
        nothing_opened = f"nothing opened in {days_since_activity} days"

        # Combine messages
        return {
            "status": "Not active",
            "detail": f"Not active – Open since {date_str}",
            "secondary_detail": nothing_opened,
            "is_active": False,
        }
