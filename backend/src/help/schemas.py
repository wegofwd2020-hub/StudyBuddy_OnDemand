"""
backend/src/help/schemas.py

Request and response schemas for POST /help/ask (Layer 2 — AI delivery).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


VALID_PERSONAS = {"school_admin", "teacher", "student"}

# Keys we recognise in account_state. Unknown keys are silently ignored so
# future signals can be added to the frontend before the backend is updated.
_ACCOUNT_STATE_KEYS = frozenset({
    "first_login",
    "teacher_count",
    "student_count",
    "classroom_count",
    "curriculum_assigned",
})


class HelpAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    page: str | None = Field(
        default=None,
        description="Current portal route, e.g. '/school/classrooms'. "
                    "Used to skip irrelevant navigation steps in the answer.",
        max_length=200,
    )
    role: str = Field(
        default="school_admin",
        description="Persona for scoping retrieval. "
                    "One of: school_admin, teacher, student.",
    )
    account_state: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional flat key-value context signals collected by the widget "
            "before submitting the question. Recognised keys: "
            "first_login (bool), teacher_count (int), student_count (int), "
            "classroom_count (int), curriculum_assigned (bool). "
            "Unknown keys are ignored. Values must be str, int, or bool."
        ),
    )

    @property
    def persona(self) -> str:
        """Normalise role → persona key used for DB filtering."""
        return self.role if self.role in VALID_PERSONAS else "school_admin"


class HelpAskResponse(BaseModel):
    title: str
    steps: list[str]
    result: str
    related: list[str]
    sources: list[str] = Field(
        default_factory=list,
        description="Headings of the library sections that were retrieved (for transparency).",
    )
    interaction_id: str | None = Field(
        default=None,
        description="UUID of the logged help_interactions row. "
                    "Pass to POST /help/feedback to record thumbs-up or thumbs-down.",
    )


class HelpFeedbackRequest(BaseModel):
    interaction_id: str = Field(
        ...,
        description="UUID returned by POST /help/ask.",
        min_length=36,
        max_length=36,
    )
    helpful: bool = Field(
        ...,
        description="True for thumbs-up (answer was useful), False for thumbs-down.",
    )


class HelpFeedbackResponse(BaseModel):
    ok: bool = True
