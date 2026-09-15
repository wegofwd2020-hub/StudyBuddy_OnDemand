"""Stable identity for a quiz question — ADR-008 Phase 1.

Lives in the backend and is imported BY the pipeline, matching the direction
`pipeline/config.py` already takes (`from src.pricing import AI_COST`). The
reverse does not work: the api container mounts ./pipeline at /pipeline, which is
not on sys.path, so a backend module importing `pipeline.*` fails at boot — which
is how the first draft of this file took the API down.

Every question needs an identity that survives being reshuffled into a different
set, so that what a student answered can be aggregated across attempts, sets and
students. Today `question_id` is `q1…qN` **within a set**, which means `q1` of set
2 is a different question from `q1` of set 1 in the same unit — so the per-answer
data already being recorded (`progress_answers`, including `ms_taken`) cannot be
grouped by anything meaningful. That is the single blocker in front of every other
part of ADR-008.

## Why content-addressed rather than a minted UUID

A UUID would have to be minted at generation and stored, which makes the ~12,500
questions already on disk unreachable without regenerating them — paying the
generation cost twice for content that is otherwise fine. A hash of the question's
own text needs no state, is identical wherever it is computed, and lets existing
content be backfilled in place.

It also collapses the same question appearing in two sets of one unit onto one
identity, which is what you want: those answers describe the same item.

## A revision deliberately produces a NEW id

ADR-008 Decision 4 says the id "does not change when a question is revised into a
new version". That is wrong, and this implementation deliberately departs from it
— see the correction recorded in the ADR.

Reworded questions are, psychometrically, different items: the difficulty and
discrimination measured for the old wording do not describe the new one. Carrying
statistics across an edit would quietly corrupt exactly the analysis Decision 8
depends on. Standard practice re-calibrates a modified item, and a changed hash is
that re-calibration expressed in the identifier.

Continuity across a revision belongs to the question registry in Phase 3, which
can record "v2 supersedes v1" explicitly, rather than to an identifier that
pretends two different texts are one thing.

## Scope of the hash

`curriculum_id | unit_id | lang | question_text`

* **curriculum_id / unit_id** — the same stem asked in two different units is two
  items; each is answered by a different cohort having studied different material.
* **lang** — a translation may be measurably harder or easier than its source, so
  `en` and `fr` are separate items. Deliberate, not an oversight.
* **NOT the set number** — a question appearing in set 1 and set 3 of one unit is
  one item and should accumulate one body of evidence.
* **NOT the options or the correct answer** — re-ordering options, or fixing a
  mis-keyed answer, does not make it a different question. Only the stem does.

Measured against all content on disk before choosing this scope: platform
curricula carry 5,760 questions with **zero** repeated stems inside any one set,
and school forks 1,200 with zero. (Authoring Studio scratch projects do repeat —
81% of 5,608 — which is a content-quality problem there, not an identity problem
here. `stable_question_ids_for_set` reports collisions rather than hiding them.)
"""

from __future__ import annotations

import hashlib
import unicodedata

__all__ = ["QUESTION_ID_LENGTH", "stable_question_id", "stable_question_ids_for_set"]

# 16 hex characters = 64 bits. At ~12.5k questions today, and even at a million,
# collision probability is negligible (birthday bound ~2.7e-8 at 1e6 items), while
# staying short enough to read in a log line or a CSV export.
QUESTION_ID_LENGTH = 16


def _normalise(text: str) -> str:
    """Fold away differences that are not differences.

    Unicode NFC so a composed and a decomposed accent hash alike; whitespace
    collapsed so a reflowed line in the content file does not mint a new identity
    for the same question. Case is NOT folded — a question is not usually made
    different by capitalisation, but neither is it made the same, and lowering it
    would merge stems that a subject like Chemistry distinguishes (`mM` vs `mm`).
    """
    return " ".join(unicodedata.normalize("NFC", text).split())


def stable_question_id(
    curriculum_id: str,
    unit_id: str,
    lang: str,
    question_text: str,
) -> str:
    """The stable identity of one question. Pure, deterministic, no I/O.

    Returns 16 lowercase hex characters. Recomputing it anywhere — pipeline,
    backend, a backfill script — yields the same value for the same question,
    which is the whole point: nothing has to store or look up a mapping.
    """
    payload = "\x1f".join(
        (
            (curriculum_id or "").strip(),
            (unit_id or "").strip(),
            (lang or "").strip().lower(),
            _normalise(question_text or ""),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:QUESTION_ID_LENGTH]


def stable_question_ids_for_set(
    curriculum_id: str,
    unit_id: str,
    lang: str,
    questions: list[dict],
) -> tuple[dict[str, str], list[str]]:
    """Map each question's positional id to its stable id.

    Returns `({positional_id: stable_id}, collisions)`. `collisions` names the
    positional ids whose stem repeats another question in the SAME set — real
    content has none, but Authoring Studio scratch projects do, and a silent
    collision would merge two questions' statistics into one. Reported rather
    than resolved: the fix belongs in the content, not in the identifier.
    """
    mapping: dict[str, str] = {}
    seen: dict[str, str] = {}
    collisions: list[str] = []

    for question in questions:
        positional = question.get("question_id")
        text = question.get("question_text")
        if not positional or not text:
            continue
        sid = stable_question_id(curriculum_id, unit_id, lang, text)
        if sid in seen:
            collisions.append(positional)
        else:
            seen[sid] = positional
        mapping[positional] = sid

    return mapping, collisions
