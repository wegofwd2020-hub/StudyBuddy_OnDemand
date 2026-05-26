"""
backend/src/admin/book_export.py

Phase 1 of the "Context Engineering in the Enterprise" content migration
(StudyBuddy_SelfLearner `docs/CONTENT_MIGRATION_CONTEXT_ENGINEERING.md`).

Pure transform layer: turn a *published* authored curriculum (the Curriculum
Authoring Studio's per-topic content) into a StudyBuddy Q-shaped ``Book`` JSON.
Kept free of DB / filesystem / network so the field mappings are unit-testable
without a live database — ``scripts/export_book.py`` is the thin asyncpg shell
that feeds these functions.

This moves *data*, not code: nothing here imports from or is imported by the Q
repo. The emitted JSON is consumed by Q's local-first ``bookStore``. That keeps
Q's ADR-002 one-way-vendoring rule (which forbids *code* cross-import) untouched.

Shape parity (both repos descend from the same vendored ``pipeline/prompts.py``):
- TOC (``structured_toc``) is byte-identical to Q's ``StructuredTOC`` — we only
  inject a stable ``id`` per unit so generated content can be keyed to it.
- Lesson differs from Q's ``LessonOutput`` only by field renames (mapped below).
- Tutorial / quiz / experiment have no Q type yet (migration plan Phase 2). We
  emit them in the vendored-schema shape (snake_case, minus pipeline-only
  metadata) so the Q-side types can mirror this module's output verbatim.
"""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime
from typing import Any

# Deterministic topic ids: uuid5(unit_id) is stable across re-exports, so a
# re-run produces the same Book/topic ids (idempotent import on the Q side).
_TOPIC_NS = uuid.UUID("6f9b1d2e-3c4a-5b6d-8e9f-0a1b2c3d4e5f")


class BookExportError(Exception):
    """Raised when the authored curriculum cannot be assembled into a Book."""


def topic_id_for(unit_id: str) -> str:
    """Stable Q topic id derived from the OnDemand unit_id."""
    return str(uuid.uuid5(_TOPIC_NS, unit_id))


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


# ── Per-content-type transforms (OnDemand body → Q shape) ─────────────────────


def lesson_to_q(body: dict, *, unit_title: str, grade: int | None = None) -> dict:
    """OnDemand lesson body → Q ``LessonOutput``.

    Renames: ``sections[].body`` → ``body_markdown``, ``key_points`` →
    ``key_takeaways``, ``reading_level`` → ``level``. ``further_reading`` has no
    OnDemand counterpart, so it defaults to ``[]``.
    """
    sections = [
        {"heading": s.get("heading", ""), "body_markdown": s.get("body", "")}
        for s in body.get("sections", [])
    ]
    level = body.get("reading_level") or (f"Grade {grade}" if grade is not None else "")
    return {
        "topic": body.get("topic") or unit_title,
        "level": level,
        "language": body.get("language", "en"),
        "synopsis": body.get("synopsis", ""),
        "learning_objectives": list(body.get("learning_objectives", [])),
        "sections": sections,
        "key_takeaways": list(body.get("key_points", [])),
        "further_reading": list(body.get("further_reading", [])),
    }


def tutorial_to_q(body: dict) -> dict:
    """OnDemand tutorial body → Q tutorial shape (pipeline metadata stripped)."""
    return {
        "title": body.get("title", ""),
        "sections": [
            {
                "section_id": s.get("section_id", ""),
                "title": s.get("title", ""),
                "content": s.get("content", ""),
                "examples": list(s.get("examples", [])),
                "practice_question": s.get("practice_question", ""),
            }
            for s in body.get("sections", [])
        ],
        "common_mistakes": list(body.get("common_mistakes", [])),
    }


def quiz_to_q(body: dict) -> dict:
    """OnDemand quiz-set body → Q quiz shape (pipeline metadata stripped)."""
    return {
        "set_number": body.get("set_number"),
        "questions": [
            {
                "question_id": q.get("question_id", ""),
                "question_text": q.get("question_text", ""),
                "question_type": q.get("question_type", "multiple_choice"),
                "options": [
                    {"option_id": o.get("option_id"), "text": o.get("text", "")}
                    for o in q.get("options", [])
                ],
                "correct_option": q.get("correct_option"),
                "explanation": q.get("explanation", ""),
                "difficulty": q.get("difficulty", ""),
            }
            for q in body.get("questions", [])
        ],
        "total_questions": body.get("total_questions"),
        "passing_score": body.get("passing_score"),
        "estimated_duration_minutes": body.get("estimated_duration_minutes"),
    }


def experiment_to_q(body: dict) -> dict:
    """OnDemand experiment body → Q experiment shape (pipeline metadata stripped)."""
    return {
        "experiment_title": body.get("experiment_title", ""),
        "materials": list(body.get("materials", [])),
        "safety_notes": list(body.get("safety_notes", [])),
        "steps": [
            {
                "step_number": s.get("step_number"),
                "instruction": s.get("instruction", ""),
                "expected_observation": s.get("expected_observation", ""),
            }
            for s in body.get("steps", [])
        ],
        "questions": [
            {"question": q.get("question", ""), "answer": q.get("answer", "")}
            for q in body.get("questions", [])
        ],
        "conclusion_prompt": body.get("conclusion_prompt", ""),
    }


# ── Assembly ──────────────────────────────────────────────────────────────────


def assemble_book(
    project: dict,
    units: list[dict],
    versions: list[dict],
    *,
    lang: str = "en",
    now: str | None = None,
) -> tuple[dict, list[str]]:
    """Build a Q ``Book`` dict from a published authored curriculum.

    Args:
        project: ``{project_id, title, grade, structured_toc}`` (structured_toc
            is the StructuredTOC dict).
        units: ``curriculum_units`` rows ordered by ``sort_order`` —
            ``[{unit_id, title}, ...]``. This is the authoritative unit list and
            its order matches ``materialize()``'s nested TOC walk, so it zips
            positionally with the flattened TOC units.
        versions: active+accepted topic versions —
            ``[{unit_id, content_type, lang, body}, ...]`` (body is a dict).
        lang: language to export (only this lang's versions are used).
        now: ISO timestamp for createdAt/updatedAt/generatedAt (defaults to UTC now).

    Returns:
        ``(book, warnings)``. ``warnings`` lists units skipped for lacking a
        lesson (Q's GeneratedTopic requires a lesson).
    """
    now = now or _iso_now()
    toc = copy.deepcopy(project.get("structured_toc") or {})
    grade = project.get("grade")

    flat_units = [u for s in toc.get("subjects", []) for u in (s.get("units") or [])]
    if len(flat_units) != len(units):
        raise BookExportError(
            f"TOC unit count ({len(flat_units)}) != curriculum_units count "
            f"({len(units)}); cannot align topics to content"
        )

    # Group bodies by unit, for the requested language.
    bodies_by_unit: dict[str, dict[str, Any]] = {}
    for v in versions:
        if v.get("lang") != lang:
            continue
        bodies_by_unit.setdefault(v["unit_id"], {})[v["content_type"]] = v["body"]

    content: dict[str, dict] = {}
    warnings: list[str] = []

    for toc_unit, cu in zip(flat_units, units, strict=True):
        unit_id = cu["unit_id"]
        tid = topic_id_for(unit_id)
        toc_unit["id"] = tid  # key the TOC unit to its generated content

        bodies = bodies_by_unit.get(unit_id, {})
        lesson_body = bodies.get("lesson")
        if not lesson_body:
            warnings.append(f"unit {unit_id} ({cu.get('title', '')!r}) has no lesson — skipped")
            continue

        topic_title = cu.get("title", "") or toc_unit.get("title", "")
        gen: dict[str, Any] = {
            "topicId": tid,
            "title": topic_title,
            "generatedAt": now,
            "lesson": lesson_to_q(lesson_body, unit_title=topic_title, grade=grade),
        }
        if "tutorial" in bodies:
            gen["tutorial"] = tutorial_to_q(bodies["tutorial"])
        quiz_types = sorted(ct for ct in bodies if ct.startswith("quiz_set_"))
        if quiz_types:
            gen["quizSets"] = [quiz_to_q(bodies[ct]) for ct in quiz_types]
        if "experiment" in bodies:
            gen["experiment"] = experiment_to_q(bodies["experiment"])

        content[tid] = gen

    book = {
        "id": f"authored-{project['project_id']}",
        "title": project.get("title", ""),
        "toc": toc,
        "createdAt": now,
        "updatedAt": now,
        "content": content,
    }
    return book, warnings
