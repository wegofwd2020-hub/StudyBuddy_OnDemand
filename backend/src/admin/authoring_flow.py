"""
backend/src/admin/authoring_flow.py

Cheap, deterministic flow checks for the Curriculum Authoring Studio.

This is the no-LLM, no-cost companion to pipeline/flow_analyzer.py. It runs on
every topic change (requirement f) where a paid LLM pass would be too slow and
expensive. It catches the mechanical class of flow breakage — a prerequisite
that is taught *after* the unit that needs it, and prerequisites that name a
unit not present in the curriculum — by inspecting document order alone.

The richer pedagogical analysis (conceptual gaps, redundancy) is left to the
on-demand LLM analyzer.

Pure function, no I/O, no DB — trivially unit-testable.
"""

from __future__ import annotations

from typing import Any


def _norm(title: str) -> str:
    return " ".join(str(title).strip().lower().split())


def _to_plain(structured: Any) -> dict:
    """Accept a StructuredTOC, a pydantic model, or a plain dict."""
    if hasattr(structured, "model_dump"):
        return structured.model_dump()
    return structured or {}


def check_topic_ordering(structured: Any) -> list[dict]:
    """Flag prerequisites that resolve to a later (or missing) unit.

    Args:
        structured: StructuredTOC | dict with shape
            ``{"subjects": [{"subject_label", "units": [{"title",
              "prerequisites": [...]}]}]}``.

    Returns:
        A list of warning dicts, each:
            ``{"kind", "unit", "subject", "detail"}``
        where ``kind`` is "prerequisite_after_use" or "missing_prerequisite".
        Empty list means no mechanical ordering problems were found.
    """
    plain = _to_plain(structured)
    subjects = plain.get("subjects", []) or []

    # Flatten units in document order; map normalised title → first global index.
    ordered: list[tuple[int, str, str]] = []  # (global_index, subject_label, title)
    title_index: dict[str, int] = {}
    idx = 0
    for subject in subjects:
        subject_label = subject.get("subject_label", "")
        for unit in subject.get("units", []) or []:
            title = unit.get("title", "")
            ordered.append((idx, subject_label, title))
            title_index.setdefault(_norm(title), idx)
            idx += 1

    warnings: list[dict] = []
    pos = 0
    for subject in subjects:
        subject_label = subject.get("subject_label", "")
        for unit in subject.get("units", []) or []:
            title = unit.get("title", "")
            for prereq in unit.get("prerequisites", []) or []:
                key = _norm(prereq)
                if key == _norm(title):
                    continue  # a unit listing itself — ignore
                prereq_idx = title_index.get(key)
                if prereq_idx is None:
                    warnings.append(
                        {
                            "kind": "missing_prerequisite",
                            "unit": title,
                            "subject": subject_label,
                            "detail": (
                                f"Prerequisite {prereq!r} is not a unit in this curriculum."
                            ),
                        }
                    )
                elif prereq_idx > pos:
                    warnings.append(
                        {
                            "kind": "prerequisite_after_use",
                            "unit": title,
                            "subject": subject_label,
                            "detail": (
                                f"Unit {title!r} requires {prereq!r}, but {prereq!r} is "
                                f"sequenced after it."
                            ),
                        }
                    )
            pos += 1

    return warnings
