# Epic 12 — Teacher Content Authoring

**Status:** 💭 Thinking — open questions below must be resolved before build starts

**Origin:** Demo feedback 2026-04-26 — Venkit P (see
`studybuddy-docs/market_research/demo_feedback.md`, Reviewer 3).

---

## What it is

Add an authoring layer between the AI pipeline and the content serving path so
teachers can write, edit, and own lesson content.

Three authoring modes, all producing content that students receive through the
existing `GET /content/{unit_id}/lesson` endpoint:

| Mode | How content is created | `content_source` value |
|---|---|---|
| **AI-generated** (existing) | Pipeline runs, writes `lesson_en.json` to Content Store | `ai_generated` |
| **AI-assisted** (new) | Teacher clicks "Generate draft" → AI output lands in an editor → teacher edits and saves to DB | `ai_assisted` |
| **Teacher-authored** (new) | Teacher writes from a blank editor, saves to DB; AI pipeline never involved | `teacher_authored` |

The AI pipeline remains the default for school-submitted curriculum definitions.
This epic adds the editing and from-scratch authoring paths alongside it.
Neither replaces the other — they co-exist with provenance clearly stamped.

---

## Current state

### What Phase D built

Phase D (migration 0039) allows a school admin to define a curriculum structure
(grade + subjects + units), submit it for admin approval, and trigger the AI
pipeline. That is a *definition* layer and a *trigger* layer. It stops there.

### What is missing

| Layer | State |
|---|---|
| Write endpoint for lesson/quiz/tutorial/experiment content | **Does not exist.** `content/router.py` has only GET endpoints. |
| DB storage for teacher-authored content | **Does not exist.** Lesson bodies live as flat JSON files on disk / S3 only. |
| Pipeline guard ("skip write if teacher-authored") | **Does not exist.** Pipeline always writes `lesson_{lang}.json`, overwriting any prior file. |
| Serving-path fallback (DB-first, then file) | **Does not exist.** `content/service.py` reads from the file store unconditionally. |
| Teacher-facing lesson editor in the school portal | **Does not exist.** `/school/curriculum/content/[version_id]/unit/[unit_id]` is read-only. |
| `content_source` on lesson, quiz, tutorial, experiment | **Does not exist** on any of these types. `LessonResponse` has no `content_source` field. |

### What already exists and can be reused

- **`content_source` taxonomy** — already defined in the scenario/demo domain:
  `"human_authored" | "ai_generated" | "ai_assisted"` in
  `web/components/demos/scenario/types.ts`. The same three values apply to lesson
  content verbatim (rename `human_authored` → `teacher_authored` for clarity).
- **Scenario builder wizard pattern** — `web/components/demos/scenario/` has
  `StepMetadata`, `StepDialog`, `StepQuiz`, `StepReview` components. The
  field-level editing pattern (inline editor per section, preview panel, save
  on step completion) is directly analogous to what a lesson editor needs.
- **`SBMarkdown` renderer** — `web/components/content/Markdown.tsx` (Epic 11
  C-3). Teacher-authored content in Markdown is rendered by the same component
  as AI-generated content — no renderer changes needed.
- **Admin review queue infrastructure** — `content_subject_versions` +
  `content_reviews` + `content_annotations` tables exist. Teacher-authored
  versions fit the same review lifecycle if review is required (see Q3).
- **`write_audit_log()` helper** — already used for curriculum lifecycle events.
  Teacher content saves and publish actions are natural audit events.

---

## Why it matters

**Adoption blocker, not a nice-to-have.** The Venkit P feedback is not a
feature request — it is a diagnosis. Teachers evaluating the platform ask:
*"Can I correct something the AI got wrong?"* and *"Can I add my own examples?"*
If the answer is no, the platform becomes a read-only content feed that competes
on catalog depth — a comparison it will lose to incumbents with thousands of
resources. The authoring layer transforms the positioning: AI generates the
first draft; the teacher owns the curriculum.

**FERPA attribution.** Under FERPA, educational records are records maintained
by the institution. If a teacher substantially edits AI-generated content and
assigns it to students, the institution is the author of record. Stamping
`content_source` + `last_edited_by` satisfies the attribution requirement and
makes the chain auditable.

**Convergence with BriefCase (Epic A baseline).** The same `content_source`
field, "generate draft → edit → save" workflow, and SME review gate are already
specified for the corporate L&D scenario domain in
`studybuddy-docs/market_research/briefcase_fcpa_usecases.md` (UC-301, UC-302).
Building this correctly for lesson content in StudyBuddy creates a reusable
pattern that BriefCase can inherit directly.

---

## Rough scope

| Phase | What gets built | Size |
|---|---|---|
| **TA-1** | **Migration 0050 — `unit_content_overrides` table.** New table: `unit_content_overrides(override_id UUID PK, curriculum_id TEXT, unit_id TEXT, lang TEXT, content_type TEXT, content_source TEXT NOT NULL DEFAULT 'teacher_authored', body JSONB NOT NULL, last_edited_by UUID REFERENCES teachers, edited_at TIMESTAMPTZ, review_status TEXT DEFAULT 'pending', version_number INT DEFAULT 1)`. Unique constraint on `(curriculum_id, unit_id, lang, content_type)`. RLS: school can INSERT/UPDATE/SELECT their own rows (via `curricula.school_id`); service role bypass for pipeline. | S |
| **TA-2** | **Backend write endpoints.** `PUT /schools/{school_id}/content/{curriculum_id}/{unit_id}/{content_type}` — creates or replaces an override row. Request body is the same JSON shape as the existing `LessonResponse`, `QuizResponse`, `TutorialResponse`, `ExperimentResponse`. Validates against the existing Pydantic schemas. Stamps `content_source`, `last_edited_by`, `edited_at`. Fires `write_audit_log` event `content.teacher_authored`. Returns 200 with the saved override. `GET /schools/{school_id}/content/{curriculum_id}/{unit_id}/{content_type}` — returns the override row if one exists, otherwise 404 (not the pipeline content — that path stays separate). | M |
| **TA-3** | **Pipeline guard.** In `pipeline/build_unit.py::build_unit()`, after generating content and before calling `_write_json()`, check `unit_content_overrides` for a row with `(curriculum_id, unit_id, lang, content_type)` where `content_source != 'ai_generated'`. If found, skip the write and log `unit_skip_teacher_authored unit_id=%s lang=%s`. Requires an asyncpg query inside the pipeline — wrap in a `SET app.current_school_id = 'bypass'` block (same pattern as existing pipeline DB calls per pitfall #28 in CLAUDE.md). | S |
| **TA-4** | **Serving path — DB-first fallback.** In `content/service.py`, on every content GET, query `unit_content_overrides` for `(curriculum_id, unit_id, lang, content_type)` before reading from the file store. If a row exists, deserialise `body` and return it. If absent, fall back to the existing file-read path. The fallback is transparent — the student receives the same response shape regardless of source. Add `content_source` to `LessonResponse`, `QuizResponse`, `TutorialResponse`, `ExperimentResponse` (nullable, defaults to `"ai_generated"` if served from file). | M |
| **TA-5** | **Frontend — lesson editor (school portal).** In `/school/curriculum/content/[version_id]/unit/[unit_id]`, add an **Edit** button (visible to `school_admin` and `teacher` roles; hidden for read-only view). On click, the read-only renderer transitions to an edit form: one card per `LessonSection` with a heading input and a Markdown textarea for body; a separate card for `key_points` (add/remove/reorder list). Save calls TA-2 `PUT`. Cancel restores the prior view without saving. Show an "AI-generated" / "Teacher-authored" / "AI-assisted" badge in the header at all times. | M |
| **TA-6** | **Frontend — "Generate draft" flow.** Add a **Generate draft** button in the edit form (TA-5). On click, a Celery task is dispatched (reuses the existing `pipeline/build_unit.py` single-unit path) with `dry_run=True` — the output is returned to the frontend as JSON rather than written to the file store. The frontend populates the edit form fields with the generated output (sections, key_points). `content_source` is set to `'ai_assisted'` in the form state. Teacher still must click **Save** to persist. If the unit already has a saved override, confirm before overwriting the form. | M |
| **TA-7** | **Admin review queue — provenance badge.** In the admin content review UI (`/admin/content-review` and the version detail page), add a `content_source` badge next to each unit in the unit list. Values: `ai_generated` (grey), `ai_assisted` (blue), `teacher_authored` (green). Sourced from `unit_content_overrides.content_source` or the file-based default. No workflow change in this phase — it is visibility only. | S |
| **TA-8** | **Version history in school portal.** On the unit viewer, add a **Version history** panel listing all `unit_content_overrides` rows for `(curriculum_id, unit_id, lang, content_type)` ordered by `version_number` desc. Each row shows: version number, `content_source` badge, `last_edited_by` name, `edited_at`. "Restore this version" button creates a new override row copying the body of the selected version (immutable history — no row is deleted). | M |

**Total estimated size: 4S + 4M ≈ 6–8 engineer-weeks**

---

## Open questions

These must be resolved before TA-1 starts. Fill in **Your answer** and
**Your reasoning** under each.

---

### Q1. Storage: new table vs. extending `content_subject_versions`

`content_subject_versions` tracks which LLM provider generated a batch of
content for a subject. Teacher edits are at the *unit* level within a subject
— a finer granularity than the existing table captures.

- **(a) New `unit_content_overrides` table** (as described in TA-1 above) —
  clean separation, independent versioning per unit, no risk to existing review
  pipeline.
- **(b) Add `override_body JSONB` + `content_source TEXT` columns to
  `curriculum_units`** — simpler schema, one row per unit already exists, but
  conflates structural metadata (title, subject, order) with content body, and
  has no per-lang support.
- **(c) Store teacher content as files in the Content Store** with a
  naming convention like `lesson_en_teacher.json` — avoids DB changes, but
  makes provenance queries (who edited, when) impossible without extra metadata
  files.

**My lean:** (a) — clean, queryable, multi-lang, per-content-type,
versioning-ready.

**Your answer:**

**Your reasoning (optional):**

---

### Q2. Edit granularity — which content types can teachers edit?

- **(a) Lesson only** — the most-read content type; quickest to build.
- **(b) Lesson + Tutorial** — the two narrative types; Quiz and Experiment
  edits deferred to a follow-up phase.
- **(c) All four** — Lesson, Quiz, Tutorial, Experiment — full parity.

The schema in TA-1 supports all four via the `content_type` column.
The frontend work for each is similar but additive.

**My lean:** (b) for TA-5/TA-6, with Quiz and Experiment in a follow-up.
Quiz question editing has special logic (correct answer, options list,
explanation per question) that benefits from its own editor component.

**Your answer:**

**Your reasoning (optional):**

---

### Q3. Should teacher-authored content go through admin review before students see it?

Currently AI-generated content flows: `pipeline generates → content_subject_versions status='pending' → admin reviews → publish`. Teacher-authored content is not AI output — there is no pipeline run to create a `content_subject_versions` row.

- **(a) Teacher-authored content is live immediately** — the teacher is the
  author of record, no review gate. Fast, gives teachers full control.
  Risk: a teacher publishes content that violates content rules (Rule #1 in
  CLAUDE.md — age-appropriate, COPPA, etc.).
- **(b) Teacher-authored content enters the admin review queue** — same
  `content_subject_versions` row is created (or the override row is flagged
  `review_status='pending'`); admin must approve before students see it.
  Slower, but platform retains a content safety gate.
- **(c) Configurable per school** — schools with a history of good content
  get auto-publish; new schools go through review. Platform admin sets the
  flag.

**My lean:** (b) for initial launch — we need the safety net until we have
enough signal that teacher-authored content is consistently safe. Move to (c)
once a track record exists.

**Your answer:**

**Your reasoning (optional):**

---

### Q4. Pipeline re-run behavior when teacher edits exist

When a school re-triggers the pipeline for a curriculum (e.g., to regenerate
content for a new language, or to incorporate a prompt improvement):

- **(a) Pipeline always skips units where `content_source != 'ai_generated'`**
  — teacher edits are always preserved. Teacher must manually use "Generate
  draft" if they want a refreshed AI version. (TA-3 as specced.)
- **(b) Pipeline skips by default but the trigger endpoint accepts a
  `force_overwrite: bool` flag** — operator can override on a per-trigger
  basis with an explicit confirmation.
- **(c) Teacher is prompted** — when a re-trigger is about to overwrite a
  teacher-authored unit, the school portal shows a list of affected units and
  asks the teacher to confirm per-unit.

**My lean:** (b) — (a) is safe as default; (b) gives the operator an escape
hatch for the "our teacher left and we need to regenerate everything" scenario.

**Your answer:**

**Your reasoning (optional):**

---

### Q5. Scope — school-owned curricula only, or also platform default curricula?

RLS (migration 0046) enforces that non-bypass sessions cannot write to
`owner_type='platform'` rows. The current spec naturally gates teacher
authoring to school-owned curricula.

- **(a) School-owned curricula only** — teachers can edit their school's own
  curriculum definitions. Platform default content stays AI-generated and
  read-only. Clean, follows RLS intent.
- **(b) School-owned + platform curricula** — allow teachers to create a
  school-local override on top of a platform curriculum. The student's
  curriculum resolver would need to prefer the school override over the
  platform file. Significantly more complex.

**My lean:** (a) — (b) is a separate feature ("curriculum customization /
overlay") and deserves its own epic. Don't conflate them.

**Your answer:**

**Your reasoning (optional):**

---

### Q6. "Generate draft" — synchronous or Celery task?

The TA-6 "Generate draft" button triggers single-unit content generation.

- **(a) Celery task** — consistent with how all pipeline work is done; returns
  a `job_id` immediately; teacher polls for completion; avoids blocking the
  request. Cold-start latency is 2–5 seconds.
- **(b) Synchronous streaming** — FastAPI streams the LLM response token-by-
  token into the editor, similar to a chat interface. Feels responsive; no
  polling. Requires streaming support in the Claude provider and a
  Server-Sent Events endpoint.
- **(c) Synchronous non-streaming** — simple `await` on the LLM call; returns
  the full draft in one response. Simplest implementation; 10–30s wait is
  acceptable for a draft generation context.

**My lean:** (c) for the initial build — a teacher clicking "Generate draft"
expects a short wait. If generation regularly exceeds 30 seconds (unlikely for
a single lesson with `max_tokens=16384`), upgrade to (a).

**Your answer:**

**Your reasoning (optional):**

---

### Q7. FERPA attribution — what is stored as "author of record"?

When `content_source = 'ai_assisted'` (teacher edited an AI draft):

- **(a) Teacher is the author of record** — `last_edited_by` is the teacher's
  UUID. The AI contribution is noted in the `content_source` field only.
- **(b) Both are recorded** — store `ai_model TEXT` (which LLM was used for
  the draft) alongside `last_edited_by` (the teacher). Full chain of custody.
- **(c) No attribution on `ai_assisted`** — treat it the same as
  `teacher_authored` once the teacher saves.

**My lean:** (b) — FERPA asks "who is responsible for this record?"; the
answer is the teacher (they reviewed and saved it). Recording the LLM model
used is a bonus audit trail that costs nothing to store and is useful if a
model is later found to have produced problematic output for a given prompt.

**Your answer:**

**Your reasoning (optional):**

---

### Q8. Version history retention — how long and what is the rollback target?

- **(a) Keep all versions indefinitely** — append-only, no version is ever
  deleted. Storage cost is trivial (JSONB rows).
- **(b) Keep the last N versions per unit** — rolling window, oldest pruned
  by a Celery sweep.
- **(c) Keep all versions but hide old ones from the UI after 1 year** —
  they remain in DB for audit but the school portal only shows the last 12
  months of history.

**Rollback target — what does "restore" do?**

- **(i) Creates a new version row** copying the body of the selected
  version — the restored content becomes `v(N+1)`. History is never rewritten.
- **(ii) Updates the current row in-place** — simpler, but loses the audit
  trail of who restored when.

**My lean:** (a) + (i) — storage is negligible; immutable history is the
right pattern for educational records (FERPA + our own audit principles).

**Your answer:**

**Your reasoning (optional):**

---

## Test cases

These supplement TC-VP-01…06 in `studybuddy-docs/market_research/demo_feedback.md`.

| ID | Scenario | What is asserted |
|---|---|---|
| TA-TC-01 | Teacher opens a lesson with AI-generated content | Header badge shows `ai_generated`; no Edit button visible to student role |
| TA-TC-02 | Teacher clicks Edit, modifies a section body, saves | Override row created in DB with `content_source='teacher_authored'`; badge updates to `teacher_authored` |
| TA-TC-03 | Student fetches the lesson after teacher edit | `GET /content/{unit_id}/lesson` returns DB content, not file content; `content_source='teacher_authored'` in response |
| TA-TC-04 | Pipeline re-triggered for the curriculum | Units with `content_source != 'ai_generated'` are skipped; `unit_skip_teacher_authored` logged; file not overwritten |
| TA-TC-05 | Teacher clicks "Generate draft" | AI content populates the edit form; `content_source` set to `ai_assisted` in form state; no DB write yet |
| TA-TC-06 | Teacher edits AI draft and saves | Override row created with `content_source='ai_assisted'` and `ai_model` recorded |
| TA-TC-07 | Teacher creates a lesson from blank (no prior AI content for that unit) | Override row created with `content_source='teacher_authored'`; student receives this content; file-based fallback not hit |
| TA-TC-08 | Teacher restores a previous version | New override row created at `version_number = N+1` with the body of the selected historical version; prior versions unchanged |
| TA-TC-09 | Admin opens review queue | Each unit shows a `content_source` badge; teacher-authored units are visually distinct from AI-generated |
| TA-TC-10 | School B cannot read or write School A's override rows | TA-2 `PUT` and `GET` endpoints return 403 when `school_id` in the JWT does not match the curriculum owner |
| TA-TC-11 | `content_source = 'ai_generated'` lesson served when no override exists | Existing file-based path returns content with `content_source='ai_generated'`; DB is queried first and returns nothing |
| TA-TC-12 | Teacher attempts to edit a platform-owned curriculum unit | `PUT` returns 403; no override row created (Q5 = option a enforcement) |

---

## Dependencies and sequencing

```
TA-1 (migration) ──► TA-2 (API) ──► TA-3 (pipeline guard)
                                └──► TA-4 (serving path) ──► TA-5 (editor UI) ──► TA-6 (Generate draft)
                                                          └──► TA-7 (admin badge)
TA-5 ──► TA-8 (version history)
```

TA-3 and TA-4 can be built in parallel after TA-2. TA-7 can be built any time
after TA-1 (it only reads data). TA-8 requires TA-5 to have a usable editor
first.

---

## What this epic does NOT cover

| Out of scope | Reason |
|---|---|
| Teacher editing platform-default curricula | Separate feature ("curriculum overlay") — see Q5 |
| Quiz question editor (individual question level) | Separate phase after TA-5 ships and we validate the pattern |
| Experiment step editor | Same as quiz — additive, deferred |
| AI-generated content for the "Generate draft" path in languages other than `en` | Multi-lang draft generation follows from Epic 1 provider work; not blocked, just not specced here |
| Student-visible content attribution ("This lesson was written by Ms. Ramachandran") | Future UX decision; provenance data will exist in DB once this epic ships |
| Teacher content going through AlexJS content moderation | AlexJS runs at pipeline time on AI output; teacher content would need a separate invocation — deferred |

---

## Relationship to BriefCase (Epic A baseline)

The `content_source` field, "generate draft → edit → save" flow, and the
per-item version history being built here are **identical in structure** to
the scenario authoring workflow in
`studybuddy-docs/market_research/briefcase_fcpa_usecases.md` (UC-301 Edit
AI-Generated Dialog Turn, UC-302 Edit AI-Generated Quiz Question, UC-307
Archive / Version a Published Scenario). Build the lesson-level pattern right
here and BriefCase inherits it directly — no duplication of design decisions.

---

*Spec drafted 2026-04-29. Status: 💭 Thinking — awaiting Q1–Q8 answers.*
