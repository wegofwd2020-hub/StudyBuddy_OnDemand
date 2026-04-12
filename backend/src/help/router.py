"""
backend/src/help/router.py

Deliver-1 + Deliver-3 + Deliver-4 — /help/ask and /help/feedback

Both endpoints are public (no JWT required — the portal layouts already enforce
auth). Rate-limited per IP via Redis-backed Depends() dependencies.

Using Depends() rather than the @limiter.limit decorator avoids the known
FastAPI + slowapi + Pydantic v2 incompatibility where the decorator breaks
body parameter introspection on async handlers (see src/core/rate_limit.py).

POST /help/ask   → { question, page?, role, account_state? }
               ← { title, steps[], result, related[], sources[], interaction_id }

POST /help/feedback → { interaction_id, helpful: bool }
                   ← { ok: true }
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.core.db import get_db
from src.core.rate_limit import ip_help_rate_limit
from src.help.schemas import (
    HelpAskRequest,
    HelpAskResponse,
    HelpFeedbackRequest,
    HelpFeedbackResponse,
    VALID_PERSONAS,
)
from src.help.service import ask_help, log_interaction, record_feedback
from src.utils.logger import get_logger

log = get_logger("help")
router = APIRouter(tags=["help"])


@router.post("/help/ask", response_model=HelpAskResponse)
async def help_ask(
    request: Request,
    body: HelpAskRequest,
    _: None = Depends(ip_help_rate_limit),
) -> HelpAskResponse:
    """
    Generate a contextual help response (Deliver-1 + Deliver-3 + Deliver-4).

    Retrieves the top-3 most relevant sections from the help content library
    using pgvector similarity search (or full-text fallback), calls Claude Haiku
    for a numbered, role-appropriate answer, and logs the interaction for analytics.

    Returns interaction_id so the client can submit thumbs feedback via
    POST /help/feedback.
    """
    if body.role not in VALID_PERSONAS:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_role",
                "detail": f"role must be one of: {', '.join(sorted(VALID_PERSONAS))}",
            },
        )

    async with get_db(request) as conn:
        result = await ask_help(
            conn=conn,
            question=body.question,
            page=body.page,
            persona=body.persona,
            account_state=body.account_state,
        )
        # Log the interaction synchronously so we can return the ID for feedback.
        interaction_id = await log_interaction(
            conn=conn,
            persona=body.persona,
            page=body.page,
            question=body.question,
            response_title=result["title"],
            sources=result["sources"],
        )

    log.info(
        "help_ask_served",
        persona=body.persona,
        page=body.page,
        steps_count=len(result["steps"]),
        sources_count=len(result["sources"]),
        has_account_state=body.account_state is not None,
        interaction_id=interaction_id,
    )
    return HelpAskResponse(**result, interaction_id=interaction_id)


@router.post("/help/feedback", response_model=HelpFeedbackResponse)
async def help_feedback(
    request: Request,
    body: HelpFeedbackRequest,
    _: None = Depends(ip_help_rate_limit),
) -> HelpFeedbackResponse:
    """
    Record thumbs-up or thumbs-down feedback on a help response (Deliver-4).

    The interaction_id is returned by POST /help/ask. Feedback is optional —
    unanswered interactions remain with helpful=NULL. Submitting feedback twice
    for the same interaction_id overwrites the previous value (idempotent).
    Unknown interaction_ids are silently ignored to prevent information leakage.
    """
    async with get_db(request) as conn:
        await record_feedback(
            conn=conn,
            interaction_id=body.interaction_id,
            helpful=body.helpful,
        )
    return HelpFeedbackResponse()
