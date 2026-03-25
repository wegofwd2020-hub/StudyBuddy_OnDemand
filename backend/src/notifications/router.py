"""
backend/src/notifications/router.py

Push notification endpoints.

Routes (all prefixed /api/v1 in main.py):
  POST   /notifications/token                 → RegisterTokenResponse
  DELETE /notifications/token                 → 200
  GET    /notifications/preferences           → NotificationPreferencesResponse
  PUT    /notifications/preferences           → NotificationPreferencesResponse

Security:
  All routes require a valid student JWT.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.dependencies import get_current_student
from src.core.db import get_db
from src.notifications.schemas import (
    NotificationPreferences,
    NotificationPreferencesResponse,
    RegisterTokenRequest,
    RegisterTokenResponse,
)
from src.notifications.service import (
    deregister_token,
    get_preferences,
    register_token,
    update_preferences,
)
from src.utils.logger import get_logger

log = get_logger("notifications")
router = APIRouter(tags=["notifications"])


@router.post("/notifications/token", response_model=RegisterTokenResponse, status_code=200)
async def register_push_token(
    request: Request,
    body: RegisterTokenRequest,
    student: Annotated[dict, Depends(get_current_student)],
) -> RegisterTokenResponse:
    """Register or refresh an FCM push token for the authenticated student."""
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        try:
            result = await register_token(
                conn,
                student_id=student_id,
                device_token=body.device_token,
                platform=body.platform,
            )
        except Exception as exc:
            log.error("register_token_failed", error=str(exc), correlation_id=cid)
            raise HTTPException(
                status_code=500,
                detail={"error": "internal_error", "detail": "Could not register token.", "correlation_id": cid},
            )

    return RegisterTokenResponse(**result)


@router.delete("/notifications/token", status_code=200)
async def deregister_push_token(
    request: Request,
    body: RegisterTokenRequest,
    student: Annotated[dict, Depends(get_current_student)],
) -> dict:
    """Remove an FCM push token for the authenticated student."""
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        try:
            await deregister_token(conn, student_id=student_id, device_token=body.device_token)
        except Exception as exc:
            log.error("deregister_token_failed", error=str(exc), correlation_id=cid)
            raise HTTPException(
                status_code=500,
                detail={"error": "internal_error", "detail": "Could not deregister token.", "correlation_id": cid},
            )

    return {"status": "ok"}


@router.get("/notifications/preferences", response_model=NotificationPreferencesResponse, status_code=200)
async def get_notification_preferences(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
) -> NotificationPreferencesResponse:
    """Return notification preferences for the authenticated student."""
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        try:
            prefs = await get_preferences(conn, student_id=student_id)
        except Exception as exc:
            log.error("get_preferences_failed", error=str(exc), correlation_id=cid)
            raise HTTPException(
                status_code=500,
                detail={"error": "internal_error", "detail": "Could not fetch preferences.", "correlation_id": cid},
            )

    return NotificationPreferencesResponse(**prefs)


@router.put("/notifications/preferences", response_model=NotificationPreferencesResponse, status_code=200)
async def update_notification_preferences(
    request: Request,
    body: NotificationPreferences,
    student: Annotated[dict, Depends(get_current_student)],
) -> NotificationPreferencesResponse:
    """Update notification preferences for the authenticated student."""
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        try:
            prefs = await update_preferences(
                conn,
                student_id=student_id,
                streak_reminders=body.streak_reminders,
                weekly_summary=body.weekly_summary,
                quiz_nudges=body.quiz_nudges,
            )
        except Exception as exc:
            log.error("update_preferences_failed", error=str(exc), correlation_id=cid)
            raise HTTPException(
                status_code=500,
                detail={"error": "internal_error", "detail": "Could not update preferences.", "correlation_id": cid},
            )

    return NotificationPreferencesResponse(**prefs)
