"""
backend/src/notifications/service.py

Push notification business logic.

FCM delivery:
  send_push_notification() calls the FCM HTTP v1 API if FCM_SERVER_KEY is set.
  If the key is absent (local dev), the send is silently skipped and logged.

Token lifecycle:
  register_token()   — upserts (student_id, device_token); updates updated_at on conflict.
  deregister_token() — removes token for this student if it exists.

Preferences:
  get_preferences()    — reads notification_preferences; returns defaults if row absent.
  update_preferences() — upserts notification_preferences.
"""

from __future__ import annotations

import asyncpg

from src.utils.logger import get_logger

log = get_logger("notifications")


async def register_token(
    conn: asyncpg.Connection,
    student_id: str,
    device_token: str,
    platform: str,
) -> dict:
    """
    Upsert a push token for a student.
    If the (student_id, device_token) pair already exists, update updated_at.
    """
    row = await conn.fetchrow(
        """
        INSERT INTO push_tokens (student_id, device_token, platform)
        VALUES ($1, $2, $3)
        ON CONFLICT (student_id, device_token)
            DO UPDATE SET updated_at = NOW(), platform = EXCLUDED.platform
        RETURNING token_id::text, platform
        """,
        student_id,
        device_token,
        platform,
    )
    return {"token_id": row["token_id"], "platform": row["platform"]}


async def deregister_token(
    conn: asyncpg.Connection,
    student_id: str,
    device_token: str,
) -> bool:
    """Remove a push token. Returns True if a row was deleted."""
    result = await conn.execute(
        "DELETE FROM push_tokens WHERE student_id = $1 AND device_token = $2",
        student_id,
        device_token,
    )
    return result != "DELETE 0"


async def get_preferences(
    conn: asyncpg.Connection,
    student_id: str,
) -> dict:
    """Return notification preferences; defaults if row absent."""
    row = await conn.fetchrow(
        "SELECT streak_reminders, weekly_summary, quiz_nudges FROM notification_preferences WHERE student_id = $1",
        student_id,
    )
    if row is None:
        return {"streak_reminders": True, "weekly_summary": True, "quiz_nudges": True}
    return {
        "streak_reminders": row["streak_reminders"],
        "weekly_summary": row["weekly_summary"],
        "quiz_nudges": row["quiz_nudges"],
    }


async def update_preferences(
    conn: asyncpg.Connection,
    student_id: str,
    streak_reminders: bool,
    weekly_summary: bool,
    quiz_nudges: bool,
) -> dict:
    """Upsert notification preferences."""
    await conn.execute(
        """
        INSERT INTO notification_preferences (student_id, streak_reminders, weekly_summary, quiz_nudges)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (student_id)
            DO UPDATE SET
                streak_reminders = EXCLUDED.streak_reminders,
                weekly_summary   = EXCLUDED.weekly_summary,
                quiz_nudges      = EXCLUDED.quiz_nudges,
                updated_at       = NOW()
        """,
        student_id,
        streak_reminders,
        weekly_summary,
        quiz_nudges,
    )
    return {
        "streak_reminders": streak_reminders,
        "weekly_summary": weekly_summary,
        "quiz_nudges": quiz_nudges,
    }


async def send_push_notification(
    device_token: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> bool:
    """
    Send a push notification via FCM HTTP v1 API.

    Returns True on success, False on failure.
    Silently skips (returns False) if FCM_SERVER_KEY is not set.
    """
    from config import settings

    fcm_key = getattr(settings, "FCM_SERVER_KEY", None)
    if not fcm_key:
        log.debug("fcm_key_absent_skipping_push device_token=%s", device_token[:16])
        return False

    try:
        import httpx

        payload = {
            "to": device_token,
            "notification": {"title": title, "body": body},
            "data": data or {},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://fcm.googleapis.com/fcm/send",
                json=payload,
                headers={
                    "Authorization": f"key={fcm_key}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
        if resp.status_code == 200:
            log.info("push_sent device_token=%s title=%s", device_token[:16], title)
            return True
        else:
            log.warning(
                "push_failed device_token=%s status=%d", device_token[:16], resp.status_code
            )
            return False
    except Exception as exc:
        log.warning("push_exception device_token=%s error=%s", device_token[:16], exc)
        return False
