# Balanced answer positions in quizzes (#779)

**Status:** approved design, 2026-09-16
**Issue:** [#779](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/779)
**Approach chosen:** A — shuffle stored content (over B, per-session shuffle at serve)

## Problem

Across 6,960 questions in the demo content store the correct option's position is
A 31.2% · B 45.5% · C 21.6% · D 1.7%. A student who always picks B scores about 45%
without reading; D is almost never right, so it carries no information for
ADR-008 item analysis. Cause: the model's ordering habits. Nothing in generation or
serving reorders options.

## Constraints found in the code

- Grading is **positional**. `POST /progress/session/{id}/answer` takes
  `student_answer: int`; `_parse_quiz_answer_key` resolves the correct index as the
  position of the option whose `option_id == correct_option`, plus `accepted` —
  every position whose text matches (#754).
- `stable_question_id` = `curriculum_id|unit_id|lang|question_text`. Option order is
  not part of it, so reordering options keeps identity.
- `question_registry` (migration 0069) stores no option order or correct option.
- Two generation paths call `validate_quiz`: `pipeline/build_unit.py` (also used by
  `build_grade.py`) and `backend/src/admin/authoring_generation.py`.
- The pipeline must not import backend code (layer rules).

## Design

### 1. `pipeline/quiz_options.py`

```python
def balance_options(quiz: dict, *, unit_id: str, lang: str) -> dict
```

Returns a new quiz body (never mutates the input) where each question's options are:

1. **Canonicalised** — sorted by normalised text (whitespace collapsed, as grading
   does), ties broken by original `option_id`. The result depends only on the
   question's content, not on the order it arrived in.
2. **Permuted** by a `random.Random` seeded with
   `sha256(f"{unit_id}|{lang}|{question_text}")`.
3. **Relabelled** `A`, `B`, `C`, `D` by new position.

`correct_option` is set to the new label of the option object that was correct —
it follows the object, not the letter. Every other question field is untouched.

Because step 1 removes the incoming order, `balance_options` is **idempotent**:
applying it to its own output returns the same body. Re-running the migration or
re-publishing content cannot keep reshuffling.

A question whose `correct_option` names no option is left exactly as it was (the
grader already logs and skips it as a content defect; this function must not
paper over one).

### 2. Generation

Called immediately after `validate_quiz` succeeds:

- `pipeline/build_unit.py` — on each generated quiz set, before it is written.
- `backend/src/admin/authoring_generation.py` — on each generated / regenerated
  quiz body, before it is stored as a topic version.

### 3. Existing content — `backend/scripts/rebalance_quiz_options.py`

- Walks `{CONTENT_STORE_PATH}/curricula/*/*/quiz_set_*_*.json`.
- **Dry-run by default:** prints the correct-position distribution before and after
  and the number of files that would change. Writes nothing.
- `--commit` writes changed files. Before writing each one it asserts, per question:
  the option *text multiset* is unchanged, the correct option's text is unchanged,
  and the answer key still resolves (`_parse_quiz_answer_key` yields the same
  question ids with the correct text at `index`). Any violation aborts the run
  before that file is written.
- Skips `dev-placeholder` content (pitfall #36).
- Does not touch teacher overrides (`unit_content_overrides`), which live in the
  database and are school-authored.

### 4. Demo rollout (timing approved by the user at run time)

The demo's `api` image is built from `./backend` alone and its volumes are
overridden to `/data/content`, so **`pipeline` is not in the container**. The
VPS checkout at `/opt/studybuddy` has it; mount it for the one-off run, at the
path `ensure_pipeline_path()` already resolves (`/pipeline`):

```bash
sudo /usr/bin/docker compose -f docker-compose.yml -f docker-compose.demo.yml \
  --env-file .env.demo run --rm -v /opt/studybuddy/pipeline:/pipeline \
  api python /app/scripts/rebalance_quiz_options.py            # dry-run
# ... same with --commit
```

1. No `progress_sessions` row started in the last 30 minutes without `ended_at`.
2. Dry-run; review the distribution.
3. `--commit`.
4. Invalidate the content cache the way `scripts/demo/sync-content.sh` step 5 does
   (fixed in #750): delete Redis `content:*` keys only, never `FLUSHDB` (the same
   Redis holds sessions and rate limits). Content files are cached in L2 only —
   `get_content_file` has no in-process layer — so this is sufficient on the demo,
   which has no CDN in front of the content store.
5. Verify live: distribution ≈ 25% per letter; one quiz answered and graded end to
   end with the correct option at its new position.

## Accepted consequences

- Historical `progress_answers.student_answer` indexes refer to the old option
  order. Nothing reads them per option today; correctness was recorded at the time.
- A quiz session in progress at the moment of the switch could grade later answers
  against the new order — mitigated by the quiet-window check in step 1.
- Per-session shuffling (approach B) is not done. It fits naturally into the
  ADR-008 Phase 3a serving rework if ever wanted.

## Testing

- `balance_options`: correct text preserved; option text multiset preserved;
  idempotent; deterministic; over ≥2,000 synthetic questions whose correct answer
  always starts at A, each letter lands within 25% ± 3%; duplicate-text options
  (#754) still resolve to an accepted index; unresolvable `correct_option` left
  unchanged; input not mutated.
- Both generation paths apply it (patched provider returns an all-A quiz; the
  stored body is balanced).
- Script: dry-run writes nothing; `--commit` output grades identically by text;
  placeholder files skipped; a forced invariant violation aborts without writing.
- Existing grading / quiz tests, and the live quiz suite (`scripts/quiz_suite.sh`)
  before the demo rollout.
