# Balanced Quiz Answer Positions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the correct answer at a uniformly distributed position (A–D) in every stored and newly generated quiz question, without changing how grading works.

**Architecture:** One pure function, `balance_options`, canonicalises each question's options (sort by text) and applies a permutation seeded by the question's own content, relabelling A–D and moving `correct_option` with the correct option. It runs after validation in both generation paths, and a one-off backend script applies it to the existing content store with per-file equivalence checks.

**Tech Stack:** Python 3.11 stdlib (`hashlib`, `random`, `copy`), pytest in the `api` container, existing `pipeline` and `backend` packages.

**Spec:** `docs/superpowers/specs/2026-09-16-quiz-option-balance-design.md`

## Global Constraints

- `pipeline/` must not import anything from `backend/` (CLAUDE.md layer rules). `backend/` may import `pipeline` via `ensure_pipeline_path()`.
- Grading is positional and must not change: `_parse_quiz_answer_key` (backend/src/content/service.py) stays untouched.
- `balance_options` never mutates its input and is idempotent: `balance_options(balance_options(q)) == balance_options(q)`.
- Whitespace normalisation matches grading: `" ".join(text.split())`. Case is NOT folded (#754).
- Seed: `sha256(f"{unit_id}|{lang}|{question_text}")`, first 8 bytes big-endian → `random.Random`.
- Skip `model == "dev-placeholder"` content (pitfall #36).
- Run tests only via `docker compose exec -T api python -m pytest ...`. Never pass `-e TEST_DB_URL=` to pytest (pitfall #37). Never run two pytest sessions at once (pitfall #41).
- Lint/format backend files with `docker compose exec -T api ruff check <paths>` and `ruff format <paths>` (paths relative to `/app`). The repo's ruff config covers `backend/` only; keep `pipeline/quiz_options.py` in the surrounding pipeline style and do not add lint config.
- Commits end with `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.

## File Structure

| File | Responsibility |
|---|---|
| `pipeline/quiz_options.py` (create) | `balance_options()` — the only place option order is decided |
| `pipeline/build_unit.py` (modify, quiz loop ~L263-275) | apply to each generated quiz set |
| `backend/src/admin/authoring_generation.py` (modify, `generate_one` ~L147) | apply to generated quiz bodies |
| `backend/scripts/rebalance_quiz_options.py` (create) | one-off migration of the content store, dry-run by default |
| `backend/tests/test_quiz_option_balance_779.py` (create) | unit tests for `balance_options` |
| `backend/tests/test_quiz_option_balance_generation_779.py` (create) | both generation paths apply it |
| `backend/tests/test_rebalance_quiz_options_script_779.py` (create) | script behaviour |

---

### Task 1: `balance_options`

**Files:**
- Create: `pipeline/quiz_options.py`
- Test: `backend/tests/test_quiz_option_balance_779.py`

**Interfaces:**
- Produces: `pipeline.quiz_options.balance_options(quiz: dict, *, unit_id: str, lang: str) -> dict`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_quiz_option_balance_779.py`:

```python
"""
tests/test_quiz_option_balance_779.py

`balance_options` puts the correct answer at a uniform position (#779).

Across 6,960 demo questions the correct option sat at A 31.2% / B 45.5% /
C 21.6% / D 1.7%: always picking B scored ~45%. Grading is positional, so the fix
reorders the stored options and moves `correct_option` with the correct option.
"""

from __future__ import annotations

import copy
import os
import sys
from collections import Counter

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pipeline.quiz_options import balance_options  # noqa: E402


def _question(i: int, texts=("Right", "Wrong 1", "Wrong 2", "Wrong 3"), correct="A") -> dict:
    return {
        "question_id": f"q{i}",
        "question_text": f"Synthetic question number {i}?",
        "question_type": "multiple_choice",
        "options": [{"option_id": l, "text": t} for l, t in zip("ABCD", texts)],
        "correct_option": correct,
        "explanation": "Because.",
        "difficulty": "easy",
    }


def _quiz(questions: list[dict]) -> dict:
    return {"unit_id": "U-1", "language": "en", "set_number": 1, "questions": questions}


def _correct_text(q: dict) -> str:
    return next(o["text"] for o in q["options"] if o["option_id"] == q["correct_option"])


def test_the_correct_text_is_preserved():
    quiz = _quiz([_question(i) for i in range(50)])
    out = balance_options(quiz, unit_id="U-1", lang="en")
    for before, after in zip(quiz["questions"], out["questions"]):
        assert _correct_text(after) == _correct_text(before)


def test_the_option_texts_are_preserved_and_relabelled_a_to_d():
    out = balance_options(_quiz([_question(1)]), unit_id="U-1", lang="en")
    q = out["questions"][0]
    assert sorted(o["text"] for o in q["options"]) == ["Right", "Wrong 1", "Wrong 2", "Wrong 3"]
    assert [o["option_id"] for o in q["options"]] == ["A", "B", "C", "D"]


def test_positions_become_uniform():
    """The reported skew, in its worst form: correct is ALWAYS A going in."""
    quiz = _quiz([_question(i) for i in range(2000)])
    out = balance_options(quiz, unit_id="U-1", lang="en")
    share = Counter(q["correct_option"] for q in out["questions"])
    for letter in "ABCD":
        assert 0.22 <= share[letter] / 2000 <= 0.28, share


def test_it_is_deterministic():
    quiz = _quiz([_question(i) for i in range(20)])
    assert balance_options(quiz, unit_id="U-1", lang="en") == balance_options(
        quiz, unit_id="U-1", lang="en"
    )


def test_it_is_idempotent():
    """Re-running the migration or re-publishing must not keep reshuffling."""
    once = balance_options(_quiz([_question(i) for i in range(50)]), unit_id="U-1", lang="en")
    assert balance_options(once, unit_id="U-1", lang="en") == once


def test_the_incoming_order_does_not_matter():
    """Same question, options arriving in a different order -> same result."""
    a = _question(7, texts=("Right", "Wrong 1", "Wrong 2", "Wrong 3"), correct="A")
    b = _question(7, texts=("Wrong 3", "Wrong 1", "Right", "Wrong 2"), correct="C")
    out_a = balance_options(_quiz([a]), unit_id="U-1", lang="en")["questions"][0]
    out_b = balance_options(_quiz([b]), unit_id="U-1", lang="en")["questions"][0]
    assert out_a["options"] == out_b["options"]
    assert out_a["correct_option"] == out_b["correct_option"]


def test_duplicate_text_options_stay_idempotent_and_correct():
    """#754 content: the correct answer appears twice. Grading accepts either copy,
    but the letter must not flip between runs."""
    q = _question(3, texts=("USD 35,000", "USD 35,000", "USD 30,000", "USD 36,500"), correct="B")
    once = balance_options(_quiz([q]), unit_id="U-1", lang="en")
    twice = balance_options(once, unit_id="U-1", lang="en")
    assert twice == once
    assert _correct_text(once["questions"][0]) == "USD 35,000"


def test_an_unresolvable_correct_option_is_left_alone():
    """A content defect the grader logs and skips. Reordering it would hide it."""
    q = _question(1, correct="Z")
    out = balance_options(_quiz([q]), unit_id="U-1", lang="en")
    assert out["questions"][0] == q


def test_the_input_is_not_mutated():
    quiz = _quiz([_question(i) for i in range(5)])
    snapshot = copy.deepcopy(quiz)
    balance_options(quiz, unit_id="U-1", lang="en")
    assert quiz == snapshot


def test_other_fields_are_untouched():
    quiz = _quiz([_question(1)])
    quiz["generated_at"] = "2026-09-16T00:00:00Z"
    out = balance_options(quiz, unit_id="U-1", lang="en")
    assert out["generated_at"] == quiz["generated_at"]
    for key in ("question_id", "question_text", "explanation", "difficulty"):
        assert out["questions"][0][key] == quiz["questions"][0][key]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `docker compose exec -T api python -m pytest tests/test_quiz_option_balance_779.py -q --tb=line -p no:cacheprovider`
Expected: collection error `ModuleNotFoundError: No module named 'pipeline.quiz_options'`

- [ ] **Step 3: Write the implementation**

Create `pipeline/quiz_options.py`:

```python
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
        # "correct" cannot flip between runs (#754 duplicates).
        ordered = sorted(
            options,
            key=lambda o: (
                _normalise(o.get("text")),
                0 if o is correct else 1,
                str(o.get("option_id")),
            ),
        )
        random.Random(
            _seed(unit_id, lang, question.get("question_text") or "")
        ).shuffle(ordered)

        question["correct_option"] = _LABELS[next(i for i, o in enumerate(ordered) if o is correct)]
        question["options"] = [
            {**o, "option_id": _LABELS[i]} for i, o in enumerate(ordered)
        ]
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `docker compose exec -T api python -m pytest tests/test_quiz_option_balance_779.py -q --tb=short -p no:cacheprovider`
Expected: `10 passed`

- [ ] **Step 5: Lint and commit**

```bash
docker compose exec -T api ruff check tests/test_quiz_option_balance_779.py
docker compose exec -T api ruff format tests/test_quiz_option_balance_779.py
git add pipeline/quiz_options.py backend/tests/test_quiz_option_balance_779.py
git commit -m "feat(pipeline): balance_options — uniform correct-answer position (#779)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Apply it in both generation paths

**Files:**
- Modify: `pipeline/build_unit.py` (imports near L42-56; quiz loop ~L263-275)
- Modify: `backend/src/admin/authoring_generation.py` (`generate_one`, the `else: return body, total_tokens` branch ~L152)
- Test: `backend/tests/test_quiz_option_balance_generation_779.py`

**Interfaces:**
- Consumes: `pipeline.quiz_options.balance_options(quiz, *, unit_id, lang) -> dict` (Task 1)
- Produces: nothing new; stored quiz bodies are balanced.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_quiz_option_balance_generation_779.py`:

```python
"""
tests/test_quiz_option_balance_generation_779.py

Both quiz generation paths store balanced options (#779): the content pipeline
(`build_unit`, also used by `build_grade`) and the Authoring Studio
(`authoring_generation.generate_one`). The fixtures return every question with
the correct answer at A, which is the reported skew in its worst form.
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from src.admin import authoring_generation as gen
from tests.test_multi_provider_pipeline import (
    _VALID_LESSON,
    _VALID_QUIZ,
    _VALID_TUTORIAL,
    _make_config,
)


def _correct_text(q: dict) -> str:
    return next(o["text"] for o in q["options"] if o["option_id"] == q["correct_option"])


def _assert_balanced_and_still_correct(quiz: dict) -> None:
    letters = {q["correct_option"] for q in quiz["questions"]}
    # 8 distinct stems, all starting at A: staying all-A would mean nothing ran.
    assert letters != {"A"}, letters
    for q in quiz["questions"]:
        assert _correct_text(q) == "Mass divided by volume"


def test_build_unit_writes_balanced_quiz_sets():
    from pipeline.build_unit import build_unit
    from pipeline.providers.base import LLMProvider

    provider = MagicMock(spec=LLMProvider)
    provider.provider_id = "anthropic"
    provider.model = "claude-sonnet-4-6"
    responses = [
        json.dumps(_VALID_LESSON),
        json.dumps({**_VALID_QUIZ, "set_number": 1}),
        json.dumps({**_VALID_QUIZ, "set_number": 2}),
        json.dumps({**_VALID_QUIZ, "set_number": 3}),
        json.dumps(_VALID_TUTORIAL),
    ]
    calls = [0]

    def _generate(prompt: str):
        text = responses[calls[0] % len(responses)]
        calls[0] += 1
        return text, 100, 200

    provider.generate.side_effect = _generate

    with tempfile.TemporaryDirectory() as tmpdir:
        config = _make_config(tmpdir)
        with (
            patch("pipeline.build_unit.synthesize_lesson"),
            patch("pipeline.build_unit._upload_unit_to_s3"),
            patch(
                "pipeline.alex_runner.run_alex",
                return_value={"warnings_count": 0, "warnings": []},
            ),
        ):
            result = build_unit(
                curriculum_id="default-2026-g8",
                unit_id="G8-SCI-001",
                unit_data={"title": "Density", "subject": "science", "has_lab": False, "grade": 8},
                lang="en",
                config=config,
                force=True,
                provider_id="anthropic",
                provider=provider,
            )
        assert result["status"] == "ok"

        path = os.path.join(tmpdir, "curricula", "default-2026-g8", "G8-SCI-001", "quiz_set_1_en.json")
        with open(path) as f:
            _assert_balanced_and_still_correct(json.load(f))


class _Provider:
    model = "fake-model"

    def __init__(self, text: str) -> None:
        self.text = text

    def generate(self, prompt: str) -> tuple[str, int, int]:
        return self.text, 5, 5


def test_authoring_generate_one_returns_a_balanced_quiz():
    body, _ = gen.generate_one(
        _Provider(json.dumps(_VALID_QUIZ)),
        content_type="quiz_set_1",
        unit_id="G8-SCI-001",
        subject="Science",
        topic="Density",
        grade=8,
        lang="en",
    )
    _assert_balanced_and_still_correct(body)


def test_authoring_generate_one_leaves_non_quiz_content_alone():
    lesson = {**_VALID_LESSON}
    body, _ = gen.generate_one(
        _Provider(json.dumps(lesson)),
        content_type="lesson",
        unit_id="G8-SCI-001",
        subject="Science",
        topic="Density",
        grade=8,
        lang="en",
    )
    assert body == lesson
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `docker compose exec -T api python -m pytest tests/test_quiz_option_balance_generation_779.py -q --tb=line -p no:cacheprovider`
Expected: `2 failed, 1 passed` — both quiz tests fail on `assert letters != {"A"}`; the lesson test passes.

- [ ] **Step 3: Apply in `build_unit.py`**

Add to the `pipeline.*` imports (after `from pipeline.prompts import (...)`):

```python
from pipeline.quiz_options import balance_options
```

In the quiz loop, directly after `_generate_and_validate(...)` returns `quiz_data`:

```python
            quiz_data, in_tok, out_tok = _generate_and_validate(
                provider, prompt, validate_quiz, f"quiz_set_{set_num}"
            )
            # Decide the option order here, not the model (#779): its habit put
            # the correct answer at B 45% of the time and at D under 2%.
            quiz_data = balance_options(quiz_data, unit_id=unit_id, lang=lang)
            quiz_data["generated_at"] = _now_iso()
```

- [ ] **Step 4: Apply in `authoring_generation.generate_one`**

Replace the success branch:

```python
            else:
                return body, total_tokens
```

with:

```python
            else:
                if content_type.startswith("quiz_set_"):
                    # Same rule as the content pipeline (#779): the model's
                    # option order skews the correct answer toward A/B.
                    from pipeline.quiz_options import balance_options

                    body = balance_options(body, unit_id=unit_id, lang=lang)
                return body, total_tokens
```

(`ensure_pipeline_path()` is already called at the top of `generate_one`, so the import resolves in the API process.)

- [ ] **Step 5: Run the new tests and the existing generation tests**

Run: `docker compose exec -T api python -m pytest tests/test_quiz_option_balance_generation_779.py tests/test_multi_provider_pipeline.py tests/test_pipeline.py tests/test_authoring_pr_b.py tests/test_authoring_pipeline.py -q --tb=short -p no:cacheprovider`
Expected: all pass (`3 passed` for the new file; no new failures elsewhere)

- [ ] **Step 6: Lint and commit**

```bash
docker compose exec -T api ruff check src/admin/authoring_generation.py tests/test_quiz_option_balance_generation_779.py
docker compose exec -T api ruff format src/admin/authoring_generation.py tests/test_quiz_option_balance_generation_779.py
git add pipeline/build_unit.py backend/src/admin/authoring_generation.py backend/tests/test_quiz_option_balance_generation_779.py
git commit -m "feat(quiz): balance option order in both generation paths (#779)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Rebalance script for existing content

**Files:**
- Create: `backend/scripts/rebalance_quiz_options.py`
- Test: `backend/tests/test_rebalance_quiz_options_script_779.py`

**Interfaces:**
- Consumes: `balance_options` (Task 1); `src.content.service._parse_quiz_answer_key(data, curriculum_id, unit_id, set_number, lang) -> dict[str, dict]` (existing; each value has `index`, `accepted`)
- Produces:
  - `rebalance(root: str, *, commit: bool) -> Report`
  - `Report` dataclass: `files_seen: int`, `files_changed: int`, `skipped_placeholder: int`, `before: Counter`, `after: Counter`
  - `RebalanceInvariantError(Exception)`
  - `main(argv: list[str] | None = None) -> int` — exit 0 on success, 2 on invariant violation

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_rebalance_quiz_options_script_779.py`:

```python
"""
tests/test_rebalance_quiz_options_script_779.py

The one-off migration that balances existing quiz content (#779).
Dry-run by default; `--commit` writes only files whose answer key still grades
the same question to the same text.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

import pytest

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import rebalance_quiz_options as script  # noqa: E402


def _quiz(unit_id: str, model: str = "claude-sonnet-4-6") -> dict:
    return {
        "unit_id": unit_id,
        "language": "en",
        "set_number": 1,
        "model": model,
        "questions": [
            {
                "question_id": f"q{i}",
                "question_text": f"Rebalance script question {unit_id} {i}?",
                "question_type": "multiple_choice",
                "options": [
                    {"option_id": "A", "text": "Right"},
                    {"option_id": "B", "text": "Wrong 1"},
                    {"option_id": "C", "text": "Wrong 2"},
                    {"option_id": "D", "text": "Wrong 3"},
                ],
                "correct_option": "A",
                "explanation": "Because.",
                "difficulty": "easy",
            }
            for i in range(1, 41)
        ],
    }


def _write(root, cid: str, unit: str, body: dict, name: str = "quiz_set_1_en.json") -> str:
    d = os.path.join(root, "curricula", cid, unit)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, "w") as f:
        json.dump(body, f)
    return path


def _read(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def test_dry_run_writes_nothing(tmp_path):
    path = _write(tmp_path, "c1", "U-1", _quiz("U-1"))
    before = _read(path)

    report = script.rebalance(str(tmp_path), commit=False)

    assert _read(path) == before
    assert report.files_seen == 1
    assert report.files_changed == 1
    assert report.before["A"] == 40
    assert report.after["A"] < 40


def test_commit_writes_balanced_files_that_grade_the_same(tmp_path):
    path = _write(tmp_path, "c1", "U-1", _quiz("U-1"))

    report = script.rebalance(str(tmp_path), commit=True)
    after = _read(path)

    assert report.files_changed == 1
    assert {q["correct_option"] for q in after["questions"]} != {"A"}
    for q in after["questions"]:
        assert next(o["text"] for o in q["options"] if o["option_id"] == q["correct_option"]) == "Right"


def test_a_second_run_changes_nothing(tmp_path):
    _write(tmp_path, "c1", "U-1", _quiz("U-1"))
    script.rebalance(str(tmp_path), commit=True)

    report = script.rebalance(str(tmp_path), commit=True)

    assert report.files_changed == 0


def test_placeholder_content_is_skipped(tmp_path):
    path = _write(tmp_path, "c1", "U-1", _quiz("U-1", model="dev-placeholder"))
    before = _read(path)

    report = script.rebalance(str(tmp_path), commit=True)

    assert _read(path) == before
    assert report.skipped_placeholder == 1


def test_non_quiz_files_are_ignored(tmp_path):
    _write(tmp_path, "c1", "U-1", {"sections": []}, name="lesson_en.json")

    report = script.rebalance(str(tmp_path), commit=True)

    assert report.files_seen == 0


def test_an_invariant_violation_aborts_without_writing(tmp_path):
    path = _write(tmp_path, "c1", "U-1", _quiz("U-1"))
    before = _read(path)

    def _corrupt(quiz, *, unit_id, lang):
        broken = json.loads(json.dumps(quiz))
        broken["questions"][0]["options"][0]["text"] = "Something else"
        return broken

    with patch.object(script, "balance_options", _corrupt):
        with pytest.raises(script.RebalanceInvariantError):
            script.rebalance(str(tmp_path), commit=True)

    assert _read(path) == before


def test_main_returns_2_on_violation(tmp_path):
    _write(tmp_path, "c1", "U-1", _quiz("U-1"))

    def _corrupt(quiz, *, unit_id, lang):
        broken = json.loads(json.dumps(quiz))
        broken["questions"][0]["correct_option"] = "B"
        return broken

    with patch.object(script, "balance_options", _corrupt):
        assert script.main(["--root", str(tmp_path), "--commit"]) == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `docker compose exec -T api python -m pytest tests/test_rebalance_quiz_options_script_779.py -q --tb=line -p no:cacheprovider`
Expected: collection error `ModuleNotFoundError: No module named 'rebalance_quiz_options'`

- [ ] **Step 3: Write the script**

Create `backend/scripts/rebalance_quiz_options.py`:

```python
"""
backend/scripts/rebalance_quiz_options.py

Balance the correct-answer position in every stored quiz set (#779).

    python scripts/rebalance_quiz_options.py                 # dry-run (default)
    python scripts/rebalance_quiz_options.py --commit        # write changes
    python scripts/rebalance_quiz_options.py --root /path    # another store

On the demo `pipeline` is NOT inside the api image; mount it for the run:

    sudo /usr/bin/docker compose -f docker-compose.yml -f docker-compose.demo.yml \\
      --env-file .env.demo run --rm -v /opt/studybuddy/pipeline:/pipeline \\
      api python /app/scripts/rebalance_quiz_options.py

Every file is checked before it is written: same question ids, same option
texts, and the answer key resolves each question to the same correct TEXT. A
violation stops the run before that file is touched (files already written were
each verified). Placeholder content is skipped (pitfall #36). Teacher overrides
live in the database and are not touched.

After a --commit on a live store, clear the Redis `content:*` keys as
scripts/demo/sync-content.sh does (never FLUSHDB).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from src.admin.authoring_service import ensure_pipeline_path  # noqa: E402

ensure_pipeline_path()

from pipeline.quiz_options import balance_options  # noqa: E402
from src.content.service import _parse_quiz_answer_key  # noqa: E402

_QUIZ_FILE = re.compile(r"^quiz_set_(\d+)_([a-z]{2,3})\.json$")
_PLACEHOLDER_MODEL = "dev-placeholder"


class RebalanceInvariantError(Exception):
    """A rebalanced body would not grade identically to the original."""


@dataclass
class Report:
    files_seen: int = 0
    files_changed: int = 0
    skipped_placeholder: int = 0
    before: Counter = field(default_factory=Counter)
    after: Counter = field(default_factory=Counter)


def _correct_texts(body: dict, cid: str, unit: str, set_number: int, lang: str) -> dict[str, str]:
    key = _parse_quiz_answer_key(body, cid, unit, set_number, lang)
    by_id = {q.get("question_id"): q for q in body.get("questions", [])}
    return {
        qid: " ".join((by_id[qid]["options"][entry["index"]].get("text") or "").split())
        for qid, entry in key.items()
    }


def _option_texts(body: dict) -> dict[str, list[str]]:
    return {
        q.get("question_id"): sorted((o.get("text") or "") for o in q.get("options", []))
        for q in body.get("questions", [])
    }


def _verify(original: dict, balanced: dict, cid: str, unit: str, set_number: int, lang: str, path: str) -> None:
    if _option_texts(original) != _option_texts(balanced):
        raise RebalanceInvariantError(f"option texts changed: {path}")
    if _correct_texts(original, cid, unit, set_number, lang) != _correct_texts(
        balanced, cid, unit, set_number, lang
    ):
        raise RebalanceInvariantError(f"correct answer changed: {path}")


def _write_atomic(path: str, body: dict) -> None:
    tmp = f"{path}.rebalance.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def rebalance(root: str, *, commit: bool) -> Report:
    report = Report()
    curricula = os.path.join(root, "curricula")
    if not os.path.isdir(curricula):
        return report

    for cid in sorted(os.listdir(curricula)):
        cdir = os.path.join(curricula, cid)
        if not os.path.isdir(cdir):
            continue
        for unit in sorted(os.listdir(cdir)):
            udir = os.path.join(cdir, unit)
            if not os.path.isdir(udir):
                continue
            for name in sorted(os.listdir(udir)):
                match = _QUIZ_FILE.match(name)
                if not match:
                    continue
                path = os.path.join(udir, name)
                with open(path, encoding="utf-8") as f:
                    original = json.load(f)
                if original.get("model") == _PLACEHOLDER_MODEL:
                    report.skipped_placeholder += 1
                    continue

                report.files_seen += 1
                set_number, lang = int(match.group(1)), match.group(2)
                balanced = balance_options(original, unit_id=unit, lang=lang)
                report.before.update(q.get("correct_option") for q in original.get("questions", []))
                report.after.update(q.get("correct_option") for q in balanced.get("questions", []))

                if balanced == original:
                    continue
                _verify(original, balanced, cid, unit, set_number, lang, path)
                report.files_changed += 1
                if commit:
                    _write_atomic(path, balanced)
    return report


def _share(counter: Counter) -> str:
    total = sum(counter.values()) or 1
    return "  ".join(f"{k}={counter[k]} ({100 * counter[k] / total:.1f}%)" for k in "ABCD")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument("--root", default=None, help="content store root (default: settings.CONTENT_STORE_PATH)")
    parser.add_argument("--commit", action="store_true", help="write changes (default: dry-run)")
    args = parser.parse_args(argv)

    root = args.root
    if root is None:
        from config import settings

        root = settings.CONTENT_STORE_PATH

    try:
        report = rebalance(root, commit=args.commit)
    except RebalanceInvariantError as exc:
        print(f"ABORTED: {exc}", file=sys.stderr)
        return 2

    mode = "COMMIT" if args.commit else "DRY-RUN"
    print(f"[{mode}] root={root}")
    print(f"  quiz files seen: {report.files_seen}  changed: {report.files_changed}  placeholder skipped: {report.skipped_placeholder}")
    print(f"  before: {_share(report.before)}")
    print(f"  after:  {_share(report.after)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `docker compose exec -T api python -m pytest tests/test_rebalance_quiz_options_script_779.py -q --tb=short -p no:cacheprovider`
Expected: `7 passed`

- [ ] **Step 5: Dry-run against the local dev store (read-only)**

Run: `docker compose exec -T api python /app/scripts/rebalance_quiz_options.py`
Expected: `[DRY-RUN]` report; `after` shares each within a few points of 25%; exit 0. Record the numbers for the PR.

- [ ] **Step 6: Lint and commit**

```bash
docker compose exec -T api ruff check scripts/rebalance_quiz_options.py tests/test_rebalance_quiz_options_script_779.py
docker compose exec -T api ruff format scripts/rebalance_quiz_options.py tests/test_rebalance_quiz_options_script_779.py
git add backend/scripts/rebalance_quiz_options.py backend/tests/test_rebalance_quiz_options_script_779.py
git commit -m "feat(scripts): rebalance_quiz_options — migrate stored quizzes (#779)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Full verification and PR

**Files:** none new.

- [ ] **Step 1: Existing grading and quiz tests (alone, not concurrently)**

Run: `docker compose exec -T api python -m pytest tests/test_progress.py tests/test_progress_server_side_grading.py tests/test_duplicate_option_grading_754.py tests/test_quiz_fork_grading_529.py tests/test_resume_quiz_answers_667.py tests/test_content.py tests/test_placeholder_content.py tests/test_question_identity_adr008.py tests/test_feedback_question_grain_adr008.py tests/test_book_export.py -q --tb=short -p no:cacheprovider`
Expected: all pass.

- [ ] **Step 2: Full backend suite, alone**

Run: `docker compose exec -T api python -m pytest -q --tb=short -p no:cacheprovider`
Expected: 0 failures.

- [ ] **Step 3: Push and open the PR**

```bash
git push -u origin feat/779-balance-quiz-options
gh pr create --base main --title "feat(quiz): balanced correct-answer positions (#779)" --body-file /tmp/pr779.md
```

Write `/tmp/pr779.md` (scratchpad) with these sections, filled from this work:
- `Refs #779.` (not `Closes` — the issue stays open until the demo migration runs)
- **What:** `balance_options`, both generation paths, `rebalance_quiz_options.py`.
- **Why:** A 31.2 / B 45.5 / C 21.6 / D 1.7 on 6,960 questions; always-B scores ~45%.
- **Local dry-run:** the exact `before:` / `after:` lines printed in Task 3 Step 5.
- **Not in this PR:** the demo migration — a separate step, timing approved by the user (spec §4).
- **Test plan:** checkbox per test file with its pass count, plus full suite result.
- Last line: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`

---

### Rollout (after merge; user approves timing — not part of the PR)

1. Quiet window on the demo: no `progress_sessions` with `started_at > now() - interval '30 minutes' AND ended_at IS NULL`.
2. Dry-run on demo (command in the script docstring); review distribution.
3. Same command with `--commit`.
4. Delete Redis `content:*` keys only, as `scripts/demo/sync-content.sh` step 5 does.
5. Verify: rerun dry-run → `changed: 0`, after ≈ 25% each; answer one quiz end to end on the demo and confirm grading.
