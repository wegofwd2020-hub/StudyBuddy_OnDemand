"""
Pipeline-layer tests for the Curriculum Authoring Studio (PR-A).

Covers the pure structuring + flow-analysis modules and the deterministic
(no-LLM) ordering check. No DB, no real provider — fake providers return
canned JSON.
"""

from __future__ import annotations

import json
import os
import sys

# CI runs pytest from backend/; the `pipeline` package lives at repo root.
# Mirror the sys.path idiom in tests/test_pipeline.py so the imports below
# resolve in CI and in the local container (where repo root resolves to `/`).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pipeline.flow_analyzer import FlowReport, analyze_toc_flow  # noqa: E402
from pipeline.toc_structurer import StructuredTOC, structure_toc  # noqa: E402

from src.admin.authoring_flow import check_topic_ordering  # noqa: E402


class _FakeProvider:
    """Returns a fixed response string; ignores the prompt."""

    def __init__(self, response: str) -> None:
        self._response = response

    def generate(self, prompt: str) -> tuple[str, int, int]:
        return self._response, 100, 200


def test_structure_toc_parses_free_text() -> None:
    response = json.dumps({
        "subjects": [{
            "subject_label": "Motion",
            "units": [
                {"title": "Speed and velocity", "subtopics": ["Speed", "Velocity"],
                 "prerequisites": []},
                {"title": "Acceleration", "subtopics": ["Average", "Instantaneous"],
                 "prerequisites": ["Speed and velocity"]},
            ],
        }]
    })
    raw = "Chapter 1 Motion\n 1.1 Speed and velocity\n 1.2 Acceleration"
    structured = structure_toc(raw, grade=9, provider=_FakeProvider(response))

    assert isinstance(structured, StructuredTOC)
    assert structured.subjects[0].units[0].title == "Speed and velocity"
    assert structured.subjects[0].units[0].subtopics == ["Speed", "Velocity"]


def test_structure_toc_strips_code_fences() -> None:
    fenced = "```json\n" + json.dumps({
        "subjects": [{"subject_label": "Bio",
                      "units": [{"title": "Cells", "subtopics": [], "prerequisites": []}]}]
    }) + "\n```"
    structured = structure_toc("Cells", grade=7, provider=_FakeProvider(fenced))
    assert structured.subjects[0].units[0].title == "Cells"


def test_flow_analyzer_flags_prereq_gap() -> None:
    response = json.dumps({
        "summary": "One ordering issue found.",
        "warnings": [{
            "kind": "prerequisite_after_use",
            "unit": "Acceleration",
            "subject": "Physics",
            "detail": "Acceleration needs Velocity, taught later.",
        }],
    })
    structured = {
        "subjects": [{"subject_label": "Physics", "units": [
            {"title": "Acceleration", "subtopics": [], "prerequisites": ["Velocity"]},
            {"title": "Velocity", "subtopics": [], "prerequisites": []},
        ]}]
    }
    report: FlowReport = analyze_toc_flow(structured, provider=_FakeProvider(response))
    assert any(w.kind == "prerequisite_after_use" for w in report.warnings)


def test_flow_analyzer_never_raises_on_garbage() -> None:
    report = analyze_toc_flow({"subjects": []}, provider=_FakeProvider("not json at all"))
    assert isinstance(report, FlowReport)
    assert report.warnings == []


def test_deterministic_ordering_check_flags_late_prereq() -> None:
    structured = {"subjects": [{"subject_label": "P", "units": [
        {"title": "B", "subtopics": [], "prerequisites": ["A"]},
        {"title": "A", "subtopics": [], "prerequisites": []},
    ]}]}
    warnings = check_topic_ordering(structured)
    assert warnings
    assert warnings[0]["unit"] == "B"
    assert warnings[0]["kind"] == "prerequisite_after_use"


def test_deterministic_ordering_check_clean_when_in_order() -> None:
    structured = {"subjects": [{"subject_label": "P", "units": [
        {"title": "A", "subtopics": [], "prerequisites": []},
        {"title": "B", "subtopics": [], "prerequisites": ["A"]},
    ]}]}
    assert check_topic_ordering(structured) == []


def test_deterministic_ordering_check_flags_missing_prereq() -> None:
    structured = {"subjects": [{"subject_label": "P", "units": [
        {"title": "A", "subtopics": [], "prerequisites": ["Nonexistent"]},
    ]}]}
    warnings = check_topic_ordering(structured)
    assert any(w["kind"] == "missing_prerequisite" for w in warnings)
