# Epic 12 — Teacher Content Authoring

**Status:** 💭 Thinking — Q2–Q8 open; Q1 resolved (see below)

**Origin:** Demo feedback 2026-04-26 — Venkit P (see
`studybuddy-docs/market_research/demo_feedback.md`, Reviewer 3).

---

## Content path model — three paths, one serving endpoint

This is the foundational model that shapes every decision in this epic.
All three paths produce content delivered through the same
`GET /content/{unit_id}/lesson` endpoint — the student never knows which
path their content came from.

```
PATH 1 — OOB Library (existing)
  AI pipeline generates → Content Store files
  (lesson_en.json, quiz_set_1_en.json, etc.)
  Accessible read-only to all subscribers.
  curriculum_id = 'default-{year}-g{N}' (platform-owned)

PATH 2 — School-imported + customised (this epic, Phase 1)
  Teacher sees OOB lesson → clicks "Import to our curriculum"
  System copies OOB body → unit_content_overrides row (school's curriculum)
  Teacher edits their copy → saves back to the same row
  Private: visible only to that school's students.
  curriculum_id = {school UUID}

PATH 3 — School-authored from scratch (future phase)
  Teacher opens blank editor → writes lesson → saves
  Stored in same unit_content_overrides table, content_source='teacher_authored'
  No OOB content involved.
  curriculum_id = {school UUID}
```

### Serving priority

```
GET /content/{unit_id}/lesson
  │
  ├─► Check unit_content_overrides WHERE (curriculum_id, unit_id, lang, content_type)
  │     matches the student's resolved curriculum_id
  │     └─► If found: return body from DB  (paths 2 and 3)
  │
  └─► Fall back: read lesson_{lang}.json from Content Store  (path 1)
```

The student's resolved `curriculum_id` comes from the curriculum resolver
(3-step: school-owned → classroom packages → STEM fallback) — unchanged.

### `content_source` values

| Value | Meaning |
|---|---|
| `ai_generated` | Served from OOB file; no school override exists |
| `imported` | School copied from OOB; no edits yet |
| `ai_assisted` | School imported from OOB and then edited |
| `teacher_authored` | School wrote from blank; no AI involvement (Phase 3) |

---

## What it is

Epic 12 builds **Path 2** — the import and edit workflow — for lessons in Phase 1.

The four deliverables:

1. **Import** — teacher clicks "Import to our curriculum" on any OOB lesson;
   a private copy lands in the school's curriculum namespace.
2. **Edit** — teacher edits their copy (sections, key points) and saves.
3. **Provenance** — `content_source` stamped on every piece of content so
   students, teachers, and admins always know the origin.
4. **History** — every save creates a new version row; prior versions are
   never deleted; any version can be restored.

Phase 3 (write from scratch) and other content types (Quiz, Tutorial,
Experiment) are explicitly out of scope for this epic.

---

## Current state

### What exists

| Component | State |
|---|---|
| Phase D definition form | Lets a school define a curriculum structure and trigger the AI pipeline. Stops there — no content editing. |
| `GET /content/{unit_id}/lesson` | Reads from Content Store file unconditionally. No DB lookup. |
| Content Store files | `lesson_en.json` etc. written by the pipeline. Read-only from any school session. |
| `unit_content_overrides` table | **Does not exist.** |
| Import endpoint | **Does not exist.** |
| Write endpoint for lessons | **Does not exist.** `content/router.py` has only GET endpoints. |
| Pipeline guard | **Does not exist.** Pipeline always writes, would overwrite any import. |
| `content_source` on lessons | **Does not exist.** `LessonResponse` has no such field. |
| Lesson editor in school portal | **Does not exist.** Unit viewer is read-only. |

### What can be reused

- **`content_source` taxonomy** — three values already defined in
  `web/components/demos/scenario/types.ts`: `"human_authored" | "ai_generated" | "ai_assisted"`.
  Extend with `"imported"` for the unedited-import state.
- **`SBMarkdown` renderer** — `web/components/content/Markdown.tsx` (Epic 11 C-3).
  No renderer changes needed — imported and edited content uses the same Markdown
  pipeline as AI-generated content.
- **Scenario builder pattern** — `web/components/demos/scenario/` demonstrates
  the section-level editing + preview pattern. The lesson editor follows the same
  structure: one card per section, Markdown textarea, live preview panel.
- **`write_audit_log()`** — existing helper for append-only audit events.
  Import and save actions are both auditable events.
- **Curriculum resolver** — the 3-step resolver already returns a `curriculum_id`
  per student. Path 2 content is keyed by the school's own `curriculum_id`, so
  the resolver needs no changes.

---

## Why it matters

**Adoption blocker.** Teachers won't adopt a platform where the AI is the only
author. The import-and-edit model gives teachers control without requiring them
to write from scratch — the AI provides the first draft, the teacher owns the
final version.

**OOB library stays clean.** The fork model means platform content is never at
risk from school edits. Schools work in their own namespace. Other schools and
new subscribers always see the original AI-generated content.

**FERPA provenance.** When a teacher edits and publishes content to students,
the institution is the author of record. `content_source` + `last_edited_by` +
`edited_at` gives a complete, immutable chain of custody per version.

**Reusable for BriefCase.** The same fork/import pattern, `content_source`
taxonomy, and version-history mechanism are specified for the BriefCase scenario
authoring workflow (UC-301, UC-302, UC-307 in
`studybuddy-docs/market_research/briefcase_fcpa_usecases.md`). Build it right
here, BriefCase inherits it.

---

## Rough scope

| Phase | What gets built | Size |
|---|---|---|
| **TA-1** | **Migration 0050 — `unit_content_overrides` table.** Schema: `override_id UUID PK`, `school_id UUID NOT NULL REFERENCES schools`, `curriculum_id TEXT NOT NULL`, `unit_id TEXT NOT NULL`, `lang TEXT NOT NULL DEFAULT 'en'`, `content_type TEXT NOT NULL DEFAULT 'lesson'`, `content_source TEXT NOT NULL CHECK (content_source IN ('imported','ai_assisted','teacher_authored'))`, `source_curriculum_id TEXT` (nullable — which OOB curriculum was imported from), `body JSONB NOT NULL`, `ai_model TEXT` (nullable — which LLM if `ai_assisted`), `last_edited_by UUID REFERENCES teachers`, `edited_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `review_status TEXT NOT NULL DEFAULT 'draft' CHECK (review_status IN ('draft','pending_review','approved','rejected'))`, `version_number INT NOT NULL DEFAULT 1`. Unique index on `(curriculum_id, unit_id, lang, content_type, version_number)`. RLS: school session can INSERT/UPDATE/SELECT rows WHERE `school_id = current_school_id`; service role bypass for serving path. | S |
| **TA-2** | **Import endpoint.** `POST /schools/{school_id}/curricula/{curriculum_id}/units/{unit_id}/import` — body: `{source_curriculum_id, lang, content_type}`. Reads the OOB lesson file from the Content Store for `source_curriculum_id` / `unit_id` / `lang`. Creates a new `unit_content_overrides` row with `content_source='imported'`, `source_curriculum_id` recorded, `version_number=1`. Returns 201 with the new override row. Returns 409 if an override already exists for `(curriculum_id, unit_id, lang, content_type)` — must call the edit endpoint instead. Fires `write_audit_log` event `content.imported`. | S |
| **TA-3** | **Write (edit) endpoint.** `PUT /schools/{school_id}/curricula/{curriculum_id}/units/{unit_id}/content` — body: `{lang, content_type, body, content_source}`. Validates `body` against the existing Pydantic schema for the `content_type` (e.g. `LessonResponse`). If an override row exists, creates a new version row (`version_number = MAX + 1`) — never updates in place. Stamps `last_edited_by`, `edited_at`, `ai_model` (if `content_source='ai_assisted'`). Sets `review_status='draft'`. Fires `content.edited` audit event. Returns 200 with the new version row. | M |
| **TA-4** | **Pipeline guard.** In `pipeline/build_unit.py::build_unit()`, after generating content and before `_write_json()`, query `unit_content_overrides` for any row with `(curriculum_id, unit_id, lang, content_type)` — any `content_source` value qualifies. If found, skip `_write_json()` and log `unit_skip_school_override unit_id=%s lang=%s`. Uses `SET app.current_school_id = 'bypass'` per pitfall #28. | S |
| **TA-5** | **Serving path — DB-first fallback.** In `content/service.py`, on every `GET /content/{unit_id}/lesson` (and quiz / tutorial / experiment), first query `unit_content_overrides` for `(resolved_curriculum_id, unit_id, lang, content_type)` returning the row with the highest `version_number` and `review_status='approved'` (or `='draft'` if the requesting JWT is a teacher/school_admin). If found, deserialise `body` and return it. Otherwise fall back to the Content Store file. Add `content_source: str | None` to `LessonResponse` (defaults to `'ai_generated'` when served from file). | M |
| **TA-6** | **Frontend — unit viewer with Import and Edit actions.** In `/school/curriculum/content/[version_id]/unit/[unit_id]`: (a) When the unit has no override (`content_source='ai_generated'`), show an **Import to our curriculum** button. On click, calls TA-2 import endpoint; the page refreshes showing the imported content with `content_source='imported'` badge. (b) When an override exists (`imported`, `ai_assisted`), show an **Edit** button. On click, the read-only renderer transitions to an edit form: one card per `LessonSection` (heading input + Markdown textarea), one card for `key_points` (add/remove/reorder). Save calls TA-3 write endpoint. Cancel discards edits. Always show a `content_source` badge: `ai_generated` (grey) / `imported` (yellow) / `ai_assisted` (blue). | M |
| **TA-7** | **Admin review queue — provenance badge.** Add `content_source` badge to each unit row in `/admin/content-review` and the version detail page. Values and colours match TA-6. Source: query `unit_content_overrides` for the highest approved/draft version; fall back to `'ai_generated'`. Visibility only — no workflow change in this phase. | S |
| **TA-8** | **Version history in school portal.** On the unit viewer, below the content, add a **Version history** collapsible panel listing all `unit_content_overrides` rows for `(curriculum_id, unit_id, lang, content_type)` ordered by `version_number` desc. Each row shows: version number, `content_source` badge, editor name, `edited_at`. **Restore** button calls TA-3 with the selected version's `body`, creating a new `version_number = MAX + 1` row. No version is ever deleted. | M |

**Total estimated size: 3S + 4M ≈ 5–7 engineer-weeks**

---

## Open questions

Q1 is resolved. Q2–Q8 need answers before TA-1 starts.

---

### Q1. Storage model — RESOLVED

**Your answer (2026-04-29):**

Three content paths:

1. **OOB library** — AI-generated, accessible read-only to all subscribers.
2. **School-imported + customised** — school imports content from the OOB
   library into their own curriculum namespace. The customised copy is
   private to that school. Modifications not visible to others.
3. (Future) **School-authored from scratch** — teacher writes from blank.

For Phase 1 of editing: import from OOB library and modify lesson content
only.

**Architectural consequence:** new `unit_content_overrides` table (option a
from the original question) keyed by the **school's** `curriculum_id`. The OOB
files are never written to. The serving path checks for a school override first;
if absent, falls back to the OOB file. This also resolves Q5 (scope): schools
can import and customise content from the OOB library without violating RLS,
because the imported copy is stored in the school's namespace under the school's
`curriculum_id`.

---

### Q2. Edit granularity — which content types can teachers edit in Phase 1?

Per the Q1 answer, Phase 1 is lessons only. But confirming the full sequence:

- **(a) Lesson only for Phase 1** — matches Q1 answer; Quiz and Tutorial in a
  follow-up phase (Phase 2 of this epic or a new epic). The schema in TA-1
  supports all types via `content_type` — no migration needed to extend.
- **(b) Lesson + Tutorial in Phase 1** — Tutorial sections follow the same
  heading + body shape as Lesson sections, so the editor component is nearly
  identical. Low extra cost.
- **(c) All four in Phase 1** — Quiz questions have distinct structure (options,
  correct answer, explanation per question). Experiment steps are distinct too.
  Significantly more frontend work.

**My lean:** (a) — validate the import + edit pattern with lessons first. Add
Tutorial in a fast follow-up once the editor component is proven.

**Your answer:**

**Your reasoning (optional):**

---

### Q3. Should imported/edited content require admin review before students see it?

The OOB library goes through admin review before it is published. When a school
imports and edits content, there is no admin review step today.

- **(a) Live immediately for school's own students** — teacher edits their
  private copy; it goes live to their school's students on save. Fastest; gives
  teachers full control. Risk: content safety gate is removed for school-edited
  content (COPPA, age-appropriate rules per CLAUDE.md content rules).
- **(b) School-internal review** — `review_status` starts as `'draft'`; school
  admin must approve before students see it. Teachers write; school admin (or a
  head of department) approves. Platform admin is not in the loop for school-
  owned content.
- **(c) Platform admin review** — same queue that AI-generated content goes
  through. Ensures a consistent platform-level content bar. Slower; adds admin
  workload; less appropriate as school count grows.

**My lean:** (b) — the school is accountable for their content; a school-
internal approval step (school admin clicks Approve in the school portal) is
the right gate. Platform admin only intervenes if they receive a report.
`review_status` in TA-1 supports this: `draft → pending_review → approved`.

**Your answer:**

**Your reasoning (optional):**

---

### Q4. Pipeline re-run behavior when a school override exists

When a school re-triggers the pipeline for their curriculum (e.g., to add a
new language):

- **(a) Pipeline always skips units that have any override row** — any import
  or edit is preserved unconditionally. Teacher must explicitly delete the
  override to get fresh AI content. (TA-4 as specced.)
- **(b) Pipeline skips by default; accepts `force_overwrite_school_content: bool`
  flag on the trigger endpoint** — operator override for edge cases (teacher
  left, school wants to reset to AI-generated). Requires a confirmation step in
  the school portal trigger UI.
- **(c) Pipeline skips `imported` and `ai_assisted` rows but regenerates
  `imported` rows** — unedited imports (school copied but hasn't edited yet)
  are treated as disposable; edited versions are preserved.

**My lean:** (a) — once a school has imported or edited content, any pipeline
run should leave it alone. If the school wants a fresh AI version, they delete
their override. The school curriculum and the OOB library evolve independently.

**Your answer:**

**Your reasoning (optional):**

---

### Q5. Scope — school-owned curricula only, or also OOB-library curricula? — RESOLVED BY Q1

The fork/import model resolves this. Schools never write to OOB
`curriculum_id` rows. They import into their own `curriculum_id`. RLS is not
violated. The OOB library is always intact.

**Resolved: schools import into their own curriculum namespace only.**

---

### Q6. "Generate draft" — is this needed in Phase 1?

Under the import model, the teacher already has an AI-generated starting point
(the imported OOB lesson). A separate "Generate draft" button (which calls the
LLM fresh) is most useful when a school wants to generate a lesson for a unit
that was never in the OOB library — i.e., a school-defined unit with no OOB
content to import.

- **(a) Defer to Phase 2** — Phase 1 import path gives teachers an AI draft
  (the OOB lesson). "Generate draft" is only needed when there is no OOB
  lesson to import (school-defined units). Phase 3 (create from scratch) is
  the right home for this.
- **(b) Include in Phase 1** — even for units that have an OOB lesson, teachers
  may want to generate a different take (different context, different examples).
  Synchronous `await` on the LLM call; 10–30s wait is acceptable.

**My lean:** (a) — Phase 1 is "import OOB + edit". Generate draft belongs with
Phase 3 (write from scratch). Do not scope-creep Phase 1.

**Your answer:**

**Your reasoning (optional):**

---

### Q7. FERPA attribution — what is stored for `ai_assisted` content?

When a teacher imports an OOB lesson and edits it (`content_source='ai_assisted'`):

- **(a) Teacher is the sole author of record** — `last_edited_by` is the teacher
  UUID. `content_source='ai_assisted'` implies AI was involved. No further fields.
- **(b) Full chain recorded** — `last_edited_by` (teacher), `ai_model` (which LLM
  generated the OOB original), `source_curriculum_id` (which OOB curriculum was
  imported from). Complete audit trail.
- **(c) No attribution distinction** — treat `ai_assisted` the same as
  `teacher_authored` for FERPA purposes once the teacher saves.

**My lean:** (b) — `ai_model` and `source_curriculum_id` are already in the TA-1
schema. They cost nothing to store and give a complete lineage: "teacher X edited
AI-generated content from OOB curriculum Y generated by model Z". FERPA requires
the institution to be able to produce this record on demand.

**Your answer:**

**Your reasoning (optional):**

---

### Q8. Version history — retention and rollback

Every save via TA-3 creates a new version row (append-only). Rollback = create
`version_number = MAX + 1` copying the selected version's body.

- **(a) Keep all versions indefinitely** — JSONB rows are cheap. Matches FERPA
  retention requirement (educational records for the duration of the account).
- **(b) Keep the last N versions** — rolling window; older versions pruned by a
  Celery task.
- **(c) Keep all versions in DB but hide versions older than 1 year in the UI**
  — audit coverage retained; UI stays clean.

**My lean:** (a) — trivial storage cost; strong FERPA argument for keeping all.
No Celery complexity needed.

**Your answer:**

**Your reasoning (optional):**

---

## Test cases

Replaces TC-VP-01…06 in `studybuddy-docs/market_research/demo_feedback.md`
(those are now superseded by this fuller set).

| ID | Scenario | What is asserted |
|---|---|---|
| TA-TC-01 | Teacher opens a unit with no school override | Badge shows `ai_generated`; **Import** button visible; no **Edit** button |
| TA-TC-02 | Teacher clicks **Import to our curriculum** | `unit_content_overrides` row created with `content_source='imported'`, `source_curriculum_id` set, `version_number=1`; badge updates to `imported` |
| TA-TC-03 | Student fetches the lesson after import (no edits yet) | `GET /content/{unit_id}/lesson` returns the imported DB row; `content_source='imported'` in response; original OOB file untouched |
| TA-TC-04 | Teacher clicks **Edit**, modifies section body, saves | New override row created at `version_number=2` with `content_source='ai_assisted'`; `last_edited_by` and `edited_at` stamped |
| TA-TC-05 | Student fetches the lesson after teacher edit | Returns `version_number=2` row; `content_source='ai_assisted'` |
| TA-TC-06 | Pipeline re-triggered for school curriculum | Units with any override row are skipped; `unit_skip_school_override` logged; OOB files not re-written; override rows untouched |
| TA-TC-07 | Teacher opens version history panel | All versions listed newest-first; version 1 shows `imported`, version 2 shows `ai_assisted` |
| TA-TC-08 | Teacher clicks **Restore** on version 1 | New row created at `version_number=3` with `body` copied from version 1 and `content_source='imported'`; versions 1 and 2 unchanged |
| TA-TC-09 | Admin opens review queue | Each unit shows `content_source` badge; `imported` and `ai_assisted` visually distinct from `ai_generated` |
| TA-TC-10 | School B attempts to read School A's override row via the edit endpoint | Returns 403; RLS prevents cross-school reads |
| TA-TC-11 | Unit has no override; OOB file served transparently | `GET /content/{unit_id}/lesson` returns file content with `content_source='ai_generated'`; DB is queried first and returns empty |
| TA-TC-12 | Import endpoint called for a unit that already has an override | Returns 409 Conflict; no duplicate row created |
| TA-TC-13 | Import endpoint called against a platform-owned target `curriculum_id` | Returns 403; school cannot create overrides under a platform `curriculum_id` |
| TA-TC-14 | Teacher saves an edit that fails Pydantic validation (missing required section field) | Returns 422; no new version row created |

---

## Dependencies and sequencing

```
TA-1 (migration)
  └──► TA-2 (import endpoint)
  └──► TA-3 (edit endpoint)  ┐
  └──► TA-4 (pipeline guard) │ can build in parallel after TA-1
  └──► TA-5 (serving path)   ┘
         └──► TA-6 (school portal UI — import + edit)
                └──► TA-8 (version history UI)
  └──► TA-7 (admin badge — can build any time after TA-1)
```

TA-2, TA-3, TA-4, TA-5 are all independent backend tasks that can proceed in
parallel after TA-1 lands. TA-6 and TA-7 require both the endpoints (TA-2/TA-3)
and the serving path (TA-5) to be complete.

---

## What this epic does NOT cover

| Out of scope | Reason |
|---|---|
| Write from scratch (Path 3, `teacher_authored`) | Separate phase — import model gives teachers an AI first draft; blank authoring is a different UX and content governance problem |
| Quiz, Tutorial, Experiment import + edit | Phase 2 of this epic once Lesson pattern is validated |
| "Generate draft" button (fresh LLM call) | Deferred to Phase 3 (write from scratch) per Q6 discussion |
| School customising content across multiple languages simultaneously | Import and edit is per-lang; multi-lang import is a follow-up |
| Student-visible attribution ("edited by Ms. Ramachandran") | Future UX; provenance data exists in DB after this epic |
| AlexJS content moderation on teacher edits | AlexJS runs at pipeline time; teacher content moderation is a separate concern |
| Platform admin reviewing school-edited content | School-internal review (Q3 option b) keeps platform admin out of school-owned content |

---

## Relationship to BriefCase

The `unit_content_overrides` table, `content_source` taxonomy, and append-only
version history defined here map directly to BriefCase's scenario versioning
(UC-307) and dialog/quiz editing (UC-301, UC-302) in
`studybuddy-docs/market_research/briefcase_fcpa_usecases.md`.
The import step (copy AI draft → editor) is the same as BriefCase's UC-308
(human-authored path) and UC-301 (edit AI-generated dialog).
Build the pattern here; BriefCase inherits the schema and the workflow.

---

*Spec rebuilt 2026-04-29 following Q1 answer (fork/import model). Status: 💭
Thinking — Q2, Q3, Q4, Q6, Q7, Q8 await answers.*
