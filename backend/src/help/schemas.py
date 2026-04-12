"""
backend/src/help/schemas.py

Request and response schemas for POST /help/ask (Layer 2 — AI delivery).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


VALID_PERSONAS = {"school_admin", "teacher", "student"}


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
