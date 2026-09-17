"""
backend/src/school/answer_review_router.py

Quiz answer review (#762).

Routes (prefixed /api/v1 in src/core/app_factory.py, beside the other school
routers):

  GET /schools/{school_id}/content/{curriculum_id}/units/{unit_id}/answers
      — every quiz question of a unit, this school's copy: correct answer,
        this school's validation state, and how many of this school's own
        students flagged it. Any teacher of the school may view
        (require_curriculum_view); validating/correcting an answer (Tasks 3-4)
        is gated tighter, at require_review.

Curriculum is part of the path, matching the page route and the existing
content endpoints — the school may be reading a platform curriculum through a
classroom package, or its own fork of it, and the two are different content
(design doc 2026-09-17, "API").
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.core.redis_client import get_redis
from src.core.storage import get_storage
from src.school.answer_review_service import list_unit_answers
from src.school.capability_guards import require_curriculum_view
from src.school.schemas import AnswerReviewListResponse
from src.utils.logger import get_logger

log = get_logger("school.answer_review")
router = APIRouter(tags=["school-answer-review"])


@router.get(
    "/schools/{school_id}/content/{curriculum_id}/units/{unit_id}/answers",
    response_model=AnswerReviewListResponse,
)
async def list_answers(
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    lang: str = "en",
) -> AnswerReviewListResponse:
    require_curriculum_view(teacher, school_id, request)

    storage = get_storage(request)
    redis = get_redis(request)

    async with get_db(request) as conn:
        result = await list_unit_answers(
            conn,
            storage,
            redis,
            school_id=school_id,
            curriculum_id=curriculum_id,
            unit_id=unit_id,
            lang=lang,
        )

    return AnswerReviewListResponse(**result)
