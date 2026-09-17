"""
backend/src/school/answer_review_router.py

Quiz answer review (#762).

Routes (prefixed /api/v1 in src/core/app_factory.py, beside the other school
routers):

  GET /schools/{school_id}/content/{curriculum_id}/units/{unit_id}/answers
      — every quiz question of a unit, this school's copy: correct answer,
        this school's validation state, and how many of this school's own
        students flagged it. Any teacher of the school may view
        (require_curriculum_view).

  POST /schools/{school_id}/content/{curriculum_id}/units/{unit_id}
       /answers/{stable_question_id}/validate
      — record that this school has checked that question's correct answer,
        snapshotting the answer's TEXT so the tick can later be shown as
        "needs re-checking" rather than vouching for an answer nobody checked.
        Gated tighter than the read, at require_review (`curriculum.review`;
        `school_admin` is an implicit superset, not a special case here).

Curriculum is part of the path, matching the page route and the existing
content endpoints — the school may be reading a platform curriculum through a
classroom package, or its own fork of it, and the two are different content
(design doc 2026-09-17, "API").
"""

from __future__ import annotations

import uuid
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.core.events import write_audit_log
from src.core.redis_client import get_redis
from src.core.storage import get_storage
from src.school.answer_review_service import (
    QuestionNotInUnit,
    list_unit_answers,
    validate_answer,
)
from src.school.capability_guards import require_curriculum_view, require_review
from src.school.schemas import AnswerReviewListResponse, AnswerValidationResponse
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
    # Constrained because it is interpolated into a content-store filename and
    # `LocalStorage._full` has no traversal guard of its own. The shape is the
    # one the sibling content endpoints accept (src/school/content_router.py).
    lang: str = Query("en", min_length=2, max_length=5, pattern=r"^[a-z]{2}(-[A-Z]{2})?$"),
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


@router.post(
    "/schools/{school_id}/content/{curriculum_id}/units/{unit_id}"
    "/answers/{stable_question_id}/validate",
    response_model=AnswerValidationResponse,
)
async def validate_answer_endpoint(
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    # Bounded only in length: the value is a content-addressed hash whose width
    # is `QUESTION_ID_LENGTH`, and pinning a pattern here would silently 422
    # every existing tick the day that constant changes. An id that is not in
    # this unit is refused below, on the strongest possible evidence — that the
    # listing does not contain it.
    stable_question_id: Annotated[str, Path(min_length=1, max_length=128)],
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    lang: str = Query("en", min_length=2, max_length=5, pattern=r"^[a-z]{2}(-[A-Z]{2})?$"),
) -> AnswerValidationResponse:
    # Tighter than the GET's require_curriculum_view: looking is for any teacher
    # with a curriculum capability, vouching for an answer is for reviewers.
    require_review(teacher, school_id, request)

    storage = get_storage(request)
    redis = get_redis(request)
    teacher_id = teacher.get("teacher_id")

    async with get_db(request) as conn:
        try:
            result = await validate_answer(
                conn,
                storage,
                redis,
                school_id=school_id,
                curriculum_id=curriculum_id,
                unit_id=unit_id,
                lang=lang,
                stable_question_id=stable_question_id,
                teacher_id=teacher_id,
            )
        except QuestionNotInUnit:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "That question is not in this unit's quiz sets.",
                    "correlation_id": getattr(request.state, "correlation_id", ""),
                },
            ) from None
        except asyncpg.ForeignKeyViolationError:
            # `validated_by` is a FK to `teachers`, and a JWT outlives the row
            # it names: `scripts/purge_account.py` hard-deletes a teacher, so a
            # token minted minutes earlier still passes the guard and then dies
            # on the insert. Answer the caller instead of 500ing at them.
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": "This account no longer exists. Please sign in again.",
                    "correlation_id": getattr(request.state, "correlation_id", ""),
                },
            ) from None

    # Fire-and-forget (Celery dispatch, never awaited) — the tick is already
    # written, and an audit backlog must not fail a reviewer's click.
    write_audit_log(
        event_type="quiz_answer.validated",
        actor_type="teacher",
        actor_id=_as_uuid(teacher_id),
        target_type="quiz_question",
        target_id=None,
        metadata={
            "school_id": school_id,
            "curriculum_id": curriculum_id,
            "unit_id": unit_id,
            "lang": lang,
            "stable_question_id": stable_question_id,
            "correct_text": result["correct_text"],
            "actor_role": teacher.get("role"),
        },
    )

    return AnswerValidationResponse(**result)


def _as_uuid(value: str | None) -> uuid.UUID | None:
    """`write_audit_log` takes a UUID; a malformed actor id must not cost the
    caller their write, which has already happened by the time we audit."""
    try:
        return uuid.UUID(value) if value else None
    except (TypeError, ValueError):
        return None
