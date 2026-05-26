"""
pipeline/toc_structurer.py — free-text TOC → structured curriculum tree.

The super-admin Curriculum Authoring Studio (Epic: Authoring Studio) lets an
operator paste a rough, free-text table of contents (a textbook index, a
syllabus outline, a bullet list). This module turns that into the canonical
structured shape the rest of the platform speaks:

    {
      "subjects": [
        {"subject_label": "Physics",
         "units": [
           {"title": "Kinematics",
            "subtopics": ["Speed", "Velocity", "Acceleration"],
            "prerequisites": []},
           ...
         ]}
      ]
    }

The LLM's job is *extraction + light normalisation* — group loose lines into
subjects → units → subtopics and surface obvious prerequisite hints. It must
not invent units the operator didn't write; the operator edits the result in
the studio table afterwards.

Public surface:
  - TopicNode / SubjectNode / StructuredTOC   Pydantic models
  - StructureError                            raised on unrecoverable parse failure
  - structure_toc()                           sync; takes an LLMProvider instance
  - STRUCTURE_PROMPT_TEMPLATE                  exposed for tests
"""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field, ValidationError

log = logging.getLogger("pipeline.toc_structurer")


class TopicNode(BaseModel):
    """One unit/topic within a subject."""

    title: str = Field(min_length=1, max_length=300)
    subtopics: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)


class SubjectNode(BaseModel):
    """A subject grouping a list of units."""

    subject_label: str = Field(min_length=1, max_length=200)
    units: list[TopicNode] = Field(default_factory=list)


class StructuredTOC(BaseModel):
    """The full structured table of contents."""

    subjects: list[SubjectNode] = Field(default_factory=list)


class StructureError(RuntimeError):
    """Raised when the LLM output cannot be parsed into a StructuredTOC."""


STRUCTURE_PROMPT_TEMPLATE = """\
You are a curriculum architect. An operator has pasted a rough, free-text
table of contents for educational material{grade_clause}. Turn it into a
clean structured tree.

Raw table of contents:
\"\"\"
{raw_toc}
\"\"\"

Rules:
- Group lines into subjects → units → subtopics, following the operator's
  evident intent. A "subject" is a broad area (e.g. Physics); a "unit" is a
  chapter/topic (e.g. Kinematics); "subtopics" are the finer points listed
  under it.
- If the paste covers a single subject with no explicit subject heading,
  infer ONE reasonable subject_label and put every unit under it.
- Populate "prerequisites" ONLY when the source text makes a dependency
  explicit, or when a unit unmistakably requires an earlier unit's concept.
  Reference prerequisites by the exact unit "title" you assigned. When in
  doubt, leave prerequisites empty — do not guess.
- Do NOT invent units, subtopics, or subjects that are not implied by the
  source. Do NOT drop content the operator wrote.

Return ONLY a JSON object (no prose, no markdown fences) of this exact shape:
{{
  "subjects": [
    {{
      "subject_label": "string",
      "units": [
        {{"title": "string", "subtopics": ["string", ...], "prerequisites": ["string", ...]}}
      ]
    }}
  ]
}}
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


def structure_toc(
    raw_toc: str,
    grade: int | None,
    provider,
    settings=None,
) -> StructuredTOC:
    """Structure a free-text TOC into a StructuredTOC via the given provider.

    Args:
        raw_toc:  The operator's pasted free text.
        grade:    Optional grade (1-12) — included in the prompt for context.
        provider: An LLMProvider instance (``.generate(prompt) -> (text, in, out)``).
        settings: Unused when ``provider`` is supplied; kept for call symmetry.

    Returns:
        StructuredTOC with at least one subject.

    Raises:
        StructureError: the LLM returned something that is not a parseable,
            non-empty StructuredTOC. The caller (analyze task) records this on
            the project so the operator can re-run.
    """
    grade_clause = f" for grade {grade}" if grade else ""
    prompt = STRUCTURE_PROMPT_TEMPLATE.format(
        grade_clause=grade_clause,
        raw_toc=raw_toc,
    )

    try:
        text, _in_tok, _out_tok = provider.generate(prompt)
    except Exception as exc:  # provider SDKs raise their own error types
        raise StructureError(f"provider call failed: {exc}") from exc

    cleaned = _strip_code_fences(text)
    if not cleaned:
        raise StructureError("empty LLM response")

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise StructureError(f"bad JSON from LLM: {exc}") from exc

    try:
        structured = StructuredTOC(**parsed)
    except (ValidationError, TypeError) as exc:
        raise StructureError(f"schema validation failed: {exc}") from exc

    if not structured.subjects or not any(s.units for s in structured.subjects):
        raise StructureError("structured TOC has no subjects/units")

    return structured
