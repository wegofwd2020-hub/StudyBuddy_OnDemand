# Pipeline Classification — Workflow, Not Agent

**Status:** Reference (no code change implied)
**Date:** 2026-05-09
**Audience:** engineering · sales · investor materials · product copy
**Companion docs:**
- [`DESIGN_demo_videos.md`](./DESIGN_demo_videos.md) — the demo videos showcase what this pipeline produces
- [Anthropic — Building effective agents](https://www.anthropic.com/research/building-effective-agents) — the canonical workflow-vs-agent taxonomy this doc maps to

This doc fixes the answer to a question that comes up repeatedly:
**"Is the curriculum content pipeline an AI agent?"**

Short answer: **no — it's an LLM-powered workflow.** Both terms describe
real architectures, but they aren't synonyms; conflating them creates
problems with sophisticated technical reviewers (investors, integration
partners, security reviewers) who *will* ask precise follow-up questions.

## 1 · What the code actually does

The pipeline lives at `pipeline/` at the repo root (not `backend/src/pipeline`):

| File | Role |
|---|---|
| `pipeline/build_grade.py` | CLI entry point — loads `data/grade{N}_stem.json`, upserts curriculum row, iterates *subjects → units → languages*, calls `build_unit()` per combination, tracks cumulative spend, aborts on `SpendCapExceeded` |
| `pipeline/build_unit.py` | Core per-unit generator. `build_unit()` at line 141 is the function the launch plan + `DEMO_HOSTING_GUIDE.md` refer to as "the pipeline" |
| `pipeline/prompts.py` | `build_lesson_prompt`, `build_quiz_prompt`, `build_tutorial_prompt`, `build_experiment_prompt` — string-template prompt builders |
| `pipeline/schemas.py` | `validate_lesson`, `validate_quiz` etc. — JSON-schema validators |
| `pipeline/providers/` | LLM provider abstraction; `anthropic.py`, `registry.py`, support for Anthropic / OpenAI / Google |
| `pipeline/config.py` | `PipelineSettings` — cost-per-token table, spend cap, content store path, `CONTENT_VERSION`, `DEFAULT_PROVIDER` |

`build_unit()` per invocation, for one `(curriculum_id, unit_id, lang)`:

1. **Idempotency check** (`build_unit.py:188-212`) — if `meta.json` shows the
   same `CONTENT_VERSION` + provider + lang, and all expected files exist
   on disk, return `status: skipped` immediately. No LLM call.
2. **Lesson generation** (`:243-252`) — render lesson prompt → call LLM via
   provider → parse JSON → validate against `lesson` schema → retry up to
   3× on parse/validation failure → stamp model name + ISO timestamp.
3. **Quiz sets** (`:255-265`) — same pattern, repeated `num_quiz_sets` times
   (default 3).
4. **Tutorial** (`:268-277`) — same pattern.
5. **Experiment**, only if `has_lab` (`:280-290`) — same pattern.
6. **Spend cap check** (`:298-304`) — if accumulated tokens × cost-per-token
   exceeds `MAX_PIPELINE_COST_USD`, raise `SpendCapExceeded` for the
   caller to handle.
7. **Persist** — write each `*.json` to disk, then mirror to S3 if
   configured (`_upload_unit_to_s3` at `:434`).

The retry loop is at `_generate_and_validate` (`build_unit.py:87-126`):
identical-prompt re-call up to 3× on JSON-decode or schema-validation
errors. No prompt mutation, no error reflection, no critique.

## 2 · Workflow vs. agent — the distinction

Anthropic's [taxonomy](https://www.anthropic.com/research/building-effective-agents)
draws the line on **who decides the next step**.

| Question | Workflow | Agent |
|---|---|---|
| Who decides what step runs next? | The code (a fixed switch / for-loop / DAG) | The LLM (based on what it just observed) |
| Who decides when to stop? | The code (steps complete / loop exits) | The LLM (decides it's done) or step-budget cap |
| What does the LLM produce? | Structured output (JSON, text, classification) consumed by code | Tool calls + reasoning that the runtime executes |
| How does it recover from a bad step? | Code retries with the same prompt, or fails | LLM reflects on the mistake, picks a different action |
| What's the goal? | Produce a specific artefact (a lesson, a quiz set, a translation) | Achieve an open-ended goal (resolve this support ticket, refactor this codebase) |

**The StudyBuddy content pipeline maps cleanly to "workflow":**

- ✓ `build_unit()` is a fixed switch over content types — *we* wrote
  "lesson, then N quizzes, then tutorial, then maybe experiment"
- ✓ The LLM produces JSON content blobs; code parses + validates +
  persists. The LLM never calls a tool.
- ✓ Retries reuse the *same* prompt. There's no critique step that
  reasons about why the previous attempt failed; the schema check is
  binary.
- ✓ Termination is "we ran the fixed steps." There's no LLM-driven
  "I think we're done" decision.
- ✓ The goal is a specific artefact set on disk, not an open-ended
  outcome.

The pipeline has substantial engineering — multi-provider abstraction,
cost capping, idempotency, structured-output validation, retry-on-fail —
but those are properties of *good production LLM use*, not of agency.

## 3 · How to talk about it

### By audience

| Audience | Recommended framing | Why |
|---|---|---|
| Engineering / technical reviewers | "LLM-powered content generation **pipeline**" or "content build **workflow**" | Precise; maps to actual code shape; passes scrutiny |
| Sales / partner conversations | "AI content engine" / "AI-generated curriculum" / "AI-powered study material" | Honest — emphasises AI dependency without overpromising autonomy |
| Investor pitch | Avoid "AI agent" unless prepared to explain what you mean | Sophisticated investors *will* ask "what does it decide on its own?"; you'd have to walk it back |
| Product copy on demo.studybuddy.app home page | "AI-generated lessons, quizzes, and tutorials — pre-built per grade" | Already what the hero says today; matches reality |
| Press / blog post | "We use Claude to generate every lesson and quiz set" | Concrete and credit-giving |

### What NOT to claim

These statements would be inaccurate as of `pipeline/build_unit.py` 2026-05-09:

- ❌ "An AI agent that authors curricula on demand"
- ❌ "Self-improving content that learns from student responses"
- ❌ "Autonomous AI tutors"
- ❌ "Agentic content authoring"

Each of these implies a control loop where the LLM is making
decisions; the actual code does none of that.

### What you CAN claim

These are all true and supportable:

- ✓ "Every lesson and quiz set is generated by Claude (or the configured
  provider) before students see it"
- ✓ "Content is JSON-schema validated; failed generations are retried up
  to 3 times before being flagged"
- ✓ "Content is rebuilt only when the curriculum changes — versioning
  prevents wasteful regeneration"
- ✓ "The provider is swappable — Anthropic, OpenAI, or Google work
  through the same interface"
- ✓ "Total spend is capped per pipeline run; the run aborts before
  exceeding budget"

## 4 · When (and how) it could become an agent

The natural evolution path, if a future product requirement demanded
LLM-driven decision-making:

### 4.A · Add a reflection loop

After `_generate_and_validate` accepts content on schema, run an
**LLM-based critic** that scores it on dimensions schema can't capture:
clarity, age-appropriateness, factual coverage, alignment with the
unit's stated learning objectives. The LLM (not code) decides:

- Accept (current behaviour)
- Regenerate with a richer prompt that includes the previous attempt's
  weaknesses
- Refine specific sections without regenerating the whole

This is a **single-step agent** — minimal autonomy, low risk. Could ship
inside `_generate_and_validate` as an optional flag.

### 4.B · Tool-use for citations + standards alignment

Give the LLM tools: `search_curriculum_standards(grade, subject)`,
`cite_source(claim, source_url)`, `regenerate_section(section_id)`.
Let it call these as needed during lesson generation. The LLM is now
making decisions ("I should cite this; I should regenerate this section
because it doesn't ground in a standard").

This is **agentic content authoring**. Larger surface; needs careful
spend-cap re-thinking because tool-loop iterations multiply token cost.

### 4.C · Planning at the curriculum-graph level

Replace `data/grade{N}_stem.json` (a static JSON list of units) with a
**curriculum-planner agent** that, given a grade and a curriculum
standard, proposes the unit list, reasons about prerequisite ordering,
and decides which units to deepen. The LLM is now driving the curriculum
shape, not just filling in templated content.

This is the deepest level of agency on this codebase; effectively a
distinct product surface. Not on any current roadmap.

**None of (4.A–C) is needed for what the platform does today.** Workflow
is the right architecture for "every grade × subject × unit × language
gets exactly one lesson, three quizzes, one tutorial, optionally one
experiment, validated against schema." Adding agency without a clear
quality-or-capability gain would multiply complexity, cost, and failure
modes for no return.

## 5 · One-line summary for headers / decks

> *StudyBuddy uses Claude to author every lesson and quiz before
> students see it — a structured content workflow with schema-validated
> outputs, retry-on-failure, and per-run spend caps.*

This sentence is honest, scannable, and survives technical follow-up.
"Agent" appears nowhere in it.

## Change Log

| Date | Change |
|---|---|
| 2026-05-09 | Initial — captured after a "is this an AI agent?" question; codified the workflow-not-agent classification with code references, audience-specific framing, and the evolution path. |
