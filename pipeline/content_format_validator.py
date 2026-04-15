"""
pipeline/content_format_validator.py

Epic 11 C-6 — heuristic format drift checks for generated content.

The JSON schema (pipeline/schemas.py) enforces structure — required fields,
types, enum values. It cannot say "this string contains a markdown table" or
"this string contains KaTeX math". C-1 and C-2 added prompt guidance that
tabular content (Balance Sheet, Trial Balance, truth tables, periodic
excerpts) should render as GFM tables, and that formula-heavy sections
should use $...$ delimiters.

This validator runs AFTER the JSON schema passes and emits structured
warnings when a section whose title looks tabular-by-nature contains no
table, or when a formula-section title carries no math delimiter. Warnings
are non-fatal: the content is still written to the store and surfaces in
the review queue. An admin seeing warnings on a version has an early
signal that the prompts have drifted — before a student ever sees the
content.

Design notes:
  - Pure functions. No I/O, no logging side effects (the caller logs).
  - Keyword lists are intentionally conservative — false positives would
    train reviewers to ignore warnings.
  - Works on any of the four content shapes (lesson / tutorial / quiz /
    experiment); most warnings will come from tutorial sections since
    that's where long-form prose with structured expectations lives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Section titles that should almost always contain a markdown table.
# Matched case-insensitively as substrings of the title.
_TABULAR_TITLE_KEYWORDS: tuple[str, ...] = (
    "balance sheet",
    "trial balance",
    "profit and loss",
    "profit & loss",
    "income statement",
    "cash flow",
    "financial statement",
    "truth table",
    "punnett square",
    "periodic table",
    "taxonomy",
    "complexity analysis",
    "big-o",
    "big o notation",
    "comparison table",
    "data table",
)

# Section titles that should almost always contain a KaTeX formula.
_FORMULA_TITLE_KEYWORDS: tuple[str, ...] = (
    "equation",
    "formula",
    "theorem",
    "proof",
    "derivation",
    "laws of motion",
    "gas law",
    "stoichiometry",
    "kinematics",
    "quadratic",
    "pythagoras",
)

_TABLE_SEPARATOR_RE = re.compile(r"\|\s*:?-+:?\s*\|")
_MATH_DELIMITER_RE = re.compile(r"(?<!\\)\$(?!\\)")  # $ not preceded/followed by \


@dataclass(frozen=True)
class FormatWarning:
    """A single format-drift warning on a piece of content."""

    content_type: str  # "lesson" | "tutorial" | "quiz_set_N" | "experiment"
    location: str  # dotted path, e.g. "sections[2].title"
    rule: str  # "expected_table" | "expected_formula"
    title: str  # the offending heading / section title
    detail: str  # human-readable

    def as_dict(self) -> dict:
        return {
            "content_type": self.content_type,
            "location": self.location,
            "rule": self.rule,
            "title": self.title,
            "detail": self.detail,
        }


def _matches_keyword(title: str, keywords: tuple[str, ...]) -> str | None:
    """Return the first keyword found in the (lowercased) title, else None."""
    t = (title or "").lower()
    for kw in keywords:
        if kw in t:
            return kw
    return None


def _has_table(text: str) -> bool:
    """Heuristic: contains a GFM table separator row like |---| or |:---:|."""
    return bool(_TABLE_SEPARATOR_RE.search(text or ""))


def _has_math_delimiter(text: str) -> bool:
    """Heuristic: contains an unescaped $ (inline or display math)."""
    return bool(_MATH_DELIMITER_RE.search(text or ""))


# ── Per-content-type validators ──────────────────────────────────────────────


def check_tutorial(data: dict) -> list[FormatWarning]:
    """Scan tutorial sections for expected-tabular and expected-formula drift."""
    warnings: list[FormatWarning] = []
    sections = data.get("sections") or []
    for i, sec in enumerate(sections):
        if not isinstance(sec, dict):
            continue
        title = sec.get("title", "") or ""
        content = sec.get("content", "") or ""
        location = f"sections[{i}]"

        tab_kw = _matches_keyword(title, _TABULAR_TITLE_KEYWORDS)
        if tab_kw and not _has_table(content):
            warnings.append(
                FormatWarning(
                    content_type="tutorial",
                    location=f"{location}.content",
                    rule="expected_table",
                    title=title,
                    detail=(
                        f"Section title matches '{tab_kw}' which typically "
                        f"renders as a table; no GFM table separator found."
                    ),
                )
            )

        formula_kw = _matches_keyword(title, _FORMULA_TITLE_KEYWORDS)
        if formula_kw and not _has_math_delimiter(content):
            warnings.append(
                FormatWarning(
                    content_type="tutorial",
                    location=f"{location}.content",
                    rule="expected_formula",
                    title=title,
                    detail=(
                        f"Section title matches '{formula_kw}' which typically "
                        f"contains formulae; no KaTeX $ delimiter found."
                    ),
                )
            )
    return warnings


def check_lesson(data: dict) -> list[FormatWarning]:
    """Scan the lesson topic/synopsis for drift. Fewer signals than tutorial."""
    warnings: list[FormatWarning] = []
    topic = data.get("topic", "") or ""
    synopsis = data.get("synopsis", "") or ""

    tab_kw = _matches_keyword(topic, _TABULAR_TITLE_KEYWORDS)
    # Lesson synopsis is usually prose — tables would be in the companion
    # tutorial. We only warn if the TOPIC itself is tabular and the synopsis
    # neglects to mention a table shape exists.
    if tab_kw and not _has_table(synopsis):
        # Advisory only at this level — synopsis is a summary, not content.
        # Skip emitting; the drift will show up on the tutorial.
        pass

    formula_kw = _matches_keyword(topic, _FORMULA_TITLE_KEYWORDS)
    if formula_kw and not _has_math_delimiter(synopsis):
        # Same reasoning — advisory only; tutorial carries the formula.
        pass

    return warnings


def check_experiment(data: dict) -> list[FormatWarning]:
    """Experiment procedure lists don't usually need tables or math, so the
    only realistic drift is in the reflection answers for physics / chemistry
    topics."""
    warnings: list[FormatWarning] = []
    title = data.get("experiment_title", "") or ""
    questions = data.get("questions") or []

    formula_kw = _matches_keyword(title, _FORMULA_TITLE_KEYWORDS)
    if formula_kw:
        # Look for math somewhere in the answers.
        all_answers = " ".join(
            q.get("answer", "") for q in questions if isinstance(q, dict)
        )
        if not _has_math_delimiter(all_answers):
            warnings.append(
                FormatWarning(
                    content_type="experiment",
                    location="questions[].answer",
                    rule="expected_formula",
                    title=title,
                    detail=(
                        f"Experiment title matches '{formula_kw}' but no "
                        f"reflection answer contains KaTeX math."
                    ),
                )
            )
    return warnings


def check_content(content_type: str, data: dict) -> list[FormatWarning]:
    """
    Dispatch to the right per-type checker. Returns [] for content types
    without drift rules (quizzes, meta) — they're structural enough that
    the JSON schema catches the interesting issues.
    """
    if content_type == "tutorial":
        return check_tutorial(data)
    if content_type == "lesson":
        return check_lesson(data)
    if content_type == "experiment":
        return check_experiment(data)
    return []
