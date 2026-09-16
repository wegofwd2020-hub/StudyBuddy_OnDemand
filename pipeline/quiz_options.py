"""
pipeline/quiz_options.py

Balanced answer positions for multiple-choice quizzes (#779).

The model orders options by habit: across 6,960 demo questions the correct
answer sat at A 31.2% / B 45.5% / C 21.6% / D 1.7%, so always picking B scored
~45%. Grading is positional (the student submits an index), so the fix is to
decide the stored order here rather than trust the model's.

Each question's options are
  1. canonicalised -- sorted by normalised text, so the result depends only on
     the question's content, never on the order it arrived in;
  2. permuted by a RNG seeded from the question itself;
  3. relabelled A, B, C, D by position,
and `correct_option` follows the option that was correct, not its old letter.

Step 1 is what makes this idempotent: applying it to its own output returns the
same body, so re-running the migration or re-publishing cannot keep reshuffling.

Stdlib only -- `pipeline` must not import `backend`, and the backend imports this.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random

_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _normalise(text: str | None) -> str:
    # Same collapse grading uses (#754). Case is NOT folded: 'Bb' and 'bB' are
    # different genotypes in this content.
    return " ".join((text or "").split())


def _seed(unit_id: str, lang: str, question_text: str) -> int:
    digest = hashlib.sha256(f"{unit_id}|{lang}|{question_text}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def balance_options(quiz: dict, *, unit_id: str, lang: str) -> dict:
    """Return a copy of `quiz` with every question's options in balanced order."""
    out = copy.deepcopy(quiz)
    for question in out.get("questions") or []:
        options = question.get("options") or []
        correct = next(
            (o for o in options if o.get("option_id") == question.get("correct_option")),
            None,
        )
        if correct is None:
            # A content defect the grader already logs and skips. Leave it exactly
            # as found rather than reorder something that cannot be verified.
            continue

        # Among identical texts the correct option sorts first, so which copy is
        # "correct" cannot flip between runs (#754 duplicates). The final
        # tie-break is the option's full content (excluding option_id, which is
        # position-derived after relabelling and would let a second run reorder
        # whitespace/field variants ~50% of the time) rather than option_id.
        ordered = sorted(
            options,
            key=lambda o: (
                _normalise(o.get("text")),
                0 if o is correct else 1,
                json.dumps(
                    {k: v for k, v in o.items() if k != "option_id"},
                    sort_keys=True,
                    default=str,
                ),
            ),
        )
        random.Random(_seed(unit_id, lang, question.get("question_text") or "")).shuffle(ordered)

        question["correct_option"] = _LABELS[next(i for i, o in enumerate(ordered) if o is correct)]
        question["options"] = [{**o, "option_id": _LABELS[i]} for i, o in enumerate(ordered)]
    return out
