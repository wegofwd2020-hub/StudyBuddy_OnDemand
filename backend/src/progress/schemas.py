"""
backend/src/progress/schemas.py

Pydantic schemas for progress tracking endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Request schemas ───────────────────────────────────────────────────────────


class StartSessionRequest(BaseModel):
    unit_id: str = Field(..., min_length=1, max_length=64)
    curriculum_id: str = Field(..., min_length=1, max_length=64)


class RecordAnswerRequest(BaseModel):
    """
    The client submits only WHAT the student picked — never whether it was right.

    `correct_answer` and `correct` used to be accepted here and stored verbatim,
    which let any student mark their own answers correct. Grading is now done
    server-side from the content store; anything the client claims about
    correctness is ignored.
    """

    question_id: str = Field(..., min_length=1, max_length=128)
    student_answer: int = Field(ge=0)
    ms_taken: int = Field(ge=0)
    event_id: str | None = Field(None, max_length=64)  # offline dedup key


class EndSessionRequest(BaseModel):
    """
    No score field. The score is computed server-side from the answers actually
    graded during the session — the client cannot assert one.

    `total_questions` is an optional hint used only if the server cannot resolve
    the quiz's real length (e.g. the content file has since been removed); the
    answer key is preferred whenever it is available.
    """

    total_questions: int | None = Field(None, ge=1)


# ── Response schemas ──────────────────────────────────────────────────────────


class StartSessionResponse(BaseModel):
    session_id: str
    unit_id: str
    curriculum_id: str
    attempt_number: int
    started_at: str


class RecordAnswerResponse(BaseModel):
    """
    The server's verdict on the answer, plus the reveal.

    `correct_index` and `explanation` are returned HERE rather than shipped inside
    the quiz payload, so the answer key never sits in the browser before the
    student has committed to a choice.
    """

    answer_id: str
    correct: bool
    correct_index: int
    explanation: str = ""


class EndSessionResponse(BaseModel):
    session_id: str
    score: int
    total_questions: int
    passed: bool
    attempt_number: int
    ended_at: str


class ProgressAnswerRecord(BaseModel):
    answer_id: str
    question_id: str
    student_answer: int | None
    correct_answer: int | None
    correct: bool | None
    ms_taken: int | None
    recorded_at: str


class SessionRecord(BaseModel):
    session_id: str
    unit_id: str
    curriculum_id: str
    grade: int
    subject: str
    started_at: str
    ended_at: str | None
    score: int | None
    total_questions: int | None
    completed: bool
    passed: bool | None
    attempt_number: int
    answers: list[ProgressAnswerRecord] = []


class ProgressHistoryResponse(BaseModel):
    student_id: str
    sessions: list[SessionRecord]
    total: int
