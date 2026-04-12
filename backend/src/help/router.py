"""
backend/src/help/router.py

Deliver-1 — POST /help/ask

Public endpoint (no JWT required — the portal layouts already enforce auth).
Rate-limited to 10 requests/minute per IP via a Redis-backed Depends() dependency.
Using Depends() rather than the @limiter.limit decorator avoids the known
FastAPI + slowapi + Pydantic v2 incompatibility where the decorator breaks
body parameter introspection on async handlers (see src/core/rate_limit.py).

Request:  { question, page?, role }
Response: { title, steps[], result, related[], sources[] }
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.core.db import get_db
from src.core.rate_limit import ip_help_rate_limit
from src.help.schemas import HelpAskRequest, HelpAskResponse, VALID_PERSONAS
from src.help.service import ask_help
from src.utils.logger import get_logger

log = get_logger("help")
router = APIRouter(tags=["help"])


@router.post(
    "/help/ask",
    response_model=HelpAskResponse,
)
async def help_ask(
    request: Request,
    body: HelpAskRequest,
    _: None = Depends(ip_help_rate_limit),
) -> HelpAskResponse:
    """
    Generate a contextual help response.

    Retrieves the top-3 most relevant sections from the help content library
    using pgvector similarity search, then calls Claude Haiku to produce a
    numbered, role-appropriate step-by-step answer.

    Falls back to PostgreSQL full-text search when VOYAGE_API_KEY is not set.
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
        )

    log.info(
        "help_ask_served",
        persona=body.persona,
        page=body.page,
        steps_count=len(result["steps"]),
        sources_count=len(result["sources"]),
    )
    return HelpAskResponse(**result)
