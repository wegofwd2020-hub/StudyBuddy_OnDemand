"""
pipeline/flow_analyzer.py — advisory pedagogical-flow analysis of a TOC.

After a free-text TOC has been structured (see toc_structurer.py), the
Authoring Studio runs this LLM pass to surface *advisory* flow problems:
prerequisites used before they're taught, conceptual gaps, redundant topics,
and ordering that fights comprehension.

This is advisory only. It never rewrites the curriculum and never blocks the
operator — it produces a FlowReport the studio renders alongside the editable
topic table. The operator decides what to act on.

For the cheap, deterministic, no-LLM check that runs on every topic edit, see
backend/src/admin/authoring_flow.py::check_topic_ordering — this module is the
richer (paid) analysis run on demand.

Public surface:
  - FlowWarning / FlowReport     Pydantic models
  - analyze_toc_flow()           sync; takes an LLMProvider instance
  - FLOW_PROMPT_TEMPLATE         exposed for tests
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

log = logging.getLogger("pipeline.flow_analyzer")

# Closed-ish set of warning kinds the studio UI knows how to render. The LLM is
# instructed to use these; unknown kinds are kept (forward-compatible) but the
# UI groups them under "other".
FLOW_WARNING_KINDS = (
    "prerequisite_after_use",  # a prereq is taught after the unit that needs it
    "missing_prerequisite",    # a referenced prereq isn't in the curriculum
    "conceptual_gap",          # a jump that skips an expected intermediate topic
    "redundant_topic",         # the same concept is covered twice
    "ordering",                # general sequencing concern
)


class FlowWarning(BaseModel):
    """One advisory flow concern."""

    kind: str = Field(min_length=1)
    unit: str = Field(default="")        # the unit title the warning is about
    subject: str | None = None
    detail: str = Field(default="")      # human-readable explanation


class FlowReport(BaseModel):
    """Advisory flow analysis of a structured TOC."""

    warnings: list[FlowWarning] = Field(default_factory=list)
    summary: str = Field(default="")


FLOW_PROMPT_TEMPLATE = """\
You are a curriculum pedagogy reviewer. Below is a structured table of
contents (subjects → units → subtopics, with optional prerequisites).
Analyse the LEARNING FLOW and report concerns.

Structured TOC (JSON):
{structured_json}

Look for:
- prerequisite_after_use: a unit relies on a concept that is taught in a
  LATER unit (or lists a prerequisite that appears after it).
- missing_prerequisite: a unit lists or clearly needs a prerequisite that is
  nowhere in the curriculum.
- conceptual_gap: the sequence jumps over an expected intermediate concept.
- redundant_topic: two units cover essentially the same concept.
- ordering: any other sequencing issue that would hurt comprehension.

Return ONLY a JSON object (no prose, no markdown fences):
{{
  "summary": "one or two sentences on overall flow health",
  "warnings": [
    {{"kind": "<one of the kinds above>", "unit": "<unit title>",
      "subject": "<subject label or null>", "detail": "<why it matters>"}}
  ]
}}
If the flow is sound, return an empty "warnings" array with a brief positive
summary. Do not invent problems.
"""


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1 :]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _to_plain(structured: Any) -> dict:
    """Accept a StructuredTOC, a pydantic model, or a plain dict."""
    if hasattr(structured, "model_dump"):
        return structured.model_dump()
    return structured


def analyze_toc_flow(
    structured: Any,
    provider,
    settings=None,
) -> FlowReport:
    """Run the advisory LLM flow analysis over a structured TOC.

    Args:
        structured: StructuredTOC | dict — the structured table of contents.
        provider:   An LLMProvider instance.
        settings:   Unused when ``provider`` is supplied; kept for symmetry.

    Returns:
        FlowReport. Never raises on bad LLM output — a malformed response
        yields an empty report with a diagnostic summary, because flow
        analysis is advisory and must not break the authoring workflow.
    """
    plain = _to_plain(structured)
    prompt = FLOW_PROMPT_TEMPLATE.format(
        structured_json=json.dumps(plain, ensure_ascii=False, indent=2),
    )

    try:
        text, _in_tok, _out_tok = provider.generate(prompt)
    except Exception as exc:  # provider SDKs raise their own error types
        log.warning("flow_analyzer: provider failed: %s", exc)
        return FlowReport(summary="flow analysis unavailable (provider error)")

    cleaned = _strip_code_fences(text)
    if not cleaned:
        return FlowReport(summary="flow analysis unavailable (empty response)")

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        log.warning("flow_analyzer: bad JSON: %s", exc)
        return FlowReport(summary="flow analysis unavailable (unparseable response)")

    if not isinstance(parsed, dict):
        return FlowReport(summary="flow analysis unavailable (unexpected shape)")

    warnings: list[FlowWarning] = []
    for i, item in enumerate(parsed.get("warnings", []) or []):
        if not isinstance(item, dict):
            continue
        try:
            warnings.append(FlowWarning(**item))
        except ValidationError as exc:
            log.warning("flow_analyzer: warning %d failed validation: %s", i, exc)

    return FlowReport(warnings=warnings, summary=str(parsed.get("summary", "")))
