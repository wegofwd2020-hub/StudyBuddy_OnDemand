# Epic 12 — Teacher Content Authoring

**Status:** ✅ Go — all questions resolved; ready to build from TA-0

**Origin:** Demo feedback 2026-04-26 — Venkit P (see
`studybuddy-docs/market_research/demo_feedback.md`, Reviewer 3).

---

## Content path model — three paths, one serving endpoint

```
PATH 1 — OOB Library (existing)
  AI pipeline generates → Content Store files
  (lesson_en.json, quiz_set_1_en.json, tutorial_en.json, etc.)
  Accessible read-only to all subscribers.
  curriculum_id = 'default-{year}-g{N}' (platform-owned)

PATH 2 — School-imported + customised (this epic)
  Teacher sees OOB lesson or tutorial package → clicks "Import"
  System forks OOB curricula row → school-owned UUID row in curricula table
  unit_content_overrides rows created under the school's UUID
  Teacher edits → saves draft versions
  School admin reviews → approves → publishes to students
  Private: visible only to that school's students.
  curriculum_id = {school-owned UUID}

PATH 3 — School-authored from scratch (future epic)
  Teacher opens blank editor with optional AI assist → writes lesson
  Stored in unit_content_overrides, content_source='teacher_authored'
  No OOB content involved.
  curriculum_id = {school-owned UUID}
```

### Serving priority

```
GET /content/{unit_id}/lesson  (or /tutorial, /quiz/1, etc.)
  │
  ├─► Look up unit_content_active_versions
  │     WHERE (resolved_curriculum_id, unit_id, lang, content_type)
  │     └─► If found: fetch override_id from unit_content_overrides → return body
  │
  └─► Fall back: read lesson_{lang}.json from Content Store  (path 1)
```

The student's resolved `curriculum_id` comes from the existing 3-step curriculum
resolver. Under Option B, once a school's fork is created and
`grade_curriculum_assignments` updated, the resolver naturally returns the
school's UUID — no resolver changes required. Students at schools that
have not yet forked a curriculum continue to resolve to the OOB ID and
receive OOB content from the Content Store.

### `content_source` values

| Value | Meaning |
|---|---|
| `ai_generated` | Served from OOB Content Store file; no school override active |
| `imported` | School copied from OOB; no edits yet |
| `ai_assisted` | School imported from OOB and edited |
| `teacher_authored` | School wrote from blank (Path 3, future) |

---

## School curriculum fork — Option B model

This is the architectural decision that makes Path 2 school-isolated and
future-proof for copyright, backup, and housekeeping features.

**The fork happens at first import.** When a teacher imports any unit from
OOB curriculum X for the first time, the import endpoint:

1. Checks `school_adopted_curricula` — has this school adopted curriculum X? (TA-0 gate)
2. Checks `school_adopted_curricula.forked_curriculum_id` — has a fork already been created?
3. If no fork yet:
   - Creates a new row in `curricula` with a UUID primary key, `school_id` set,
     `is_default=false`, `source_curriculum_id=X` (new column tracking lineage)
   - Updates `school_adopted_curricula.forked_curriculum_id` to the new UUID
   - Upserts `grade_curriculum_assignments (school_id, grade) → new UUID`,
     replacing the OOB ID so the curriculum resolver starts returning the fork UUID
4. Creates `unit_content_overrides` rows keyed by the fork UUID

**Effect on students:** from the moment `grade_curriculum_assignments` is updated,
the resolver returns the school's UUID for those students. Units that have been
imported and published show customised content. Units that have not been imported
still fall back to the OOB Content Store file — the serving path handles this
transparently. Students never see the transition.

**Why this approach:**
- Each school's content lives under a private UUID — no cross-school collision possible
- `unit_content_active_versions` needs no `school_id` column; isolation is guaranteed
  by the UUID itself
- The fork `curricula` row is the natural anchor for copyright, backup, and export
  features — all school content is scoped to one row per adopted curriculum
- `grade_curriculum_assignments` already exists; updating it is a single UPSERT

---

## Content lifecycle — state machine

Every `unit_content_overrides` row body is **append-only** — no body is ever
overwritten; a new row at `version_number = MAX + 1` is always created.
The `review_status` field is **mutable** — status transitions UPDATE the latest
version row in place (not a new row). This is intentional: status changes are
not content changes and should not inflate version counts.

```
[import or first edit]
        │
        ▼
    [draft]         ← teacher working; only teacher + school admin can preview
        │  Teacher clicks "Submit for review"
        ▼
[pending_review]    ← visible in school admin Content Governance queue
        │  School admin clicks "Approve and publish"  (common path)
        │  OR school admin clicks "Approve only"       (batch path)
        ▼                          ▼
    [active]               [approved]
  unit_content_active      ready to batch-publish;
  _versions updated;       students still see prior version
  students see this

        │  School admin rejects instead
        ▼
   [rejected]       ← teacher sees reason; creates new version from rejected body
```

**Key invariants:**
- A new version never auto-applies to students; publish is always explicit.
- Only `school_admin` can move content to active.
- All version bodies remain in the DB; rollback = publish an older approved version.
- Assigned (active) content cannot be deleted or deactivated.
- The `approved` state exists for batch workflows: approve several units, then
  publish all at once via "Publish all approved" in the governance dashboard.
  For single-unit workflows, "Approve and publish" is the one-click path.

**Rejected version recovery:** the teacher opens the unit editor; the editor
pre-loads the rejected body and displays the rejection reason. The teacher edits
and clicks Save — this creates a new row at `version_number = MAX + 1` with
`review_status='draft'`. The rejected row remains unchanged in the DB as an
audit record.

---

## School Content Governance — role model

| Role | Content permissions |
|---|---|
| `teacher` | Import, write, edit, submit for review |
| `school_admin` | All teacher permissions + approve, reject, publish (activate), retire active version |

Phase 1 uses the existing `school_admin` role. A `head_of_department` role
(subject-scoped governance) is deferred to the follow-on governance epic.
No auth changes are required in this epic.

**Forward-looking governance scope (future epics):**

| Concern | What it means |
|---|---|
| Archive | Retire old content versions or whole curricula |
| Copyright | Track provenance; flag third-party material |
| Backup / export | Export school's fork as portable JSON/ZIP |
| Housekeeping | Prune stale drafts, quota alerts |
| `head_of_department` role | Subject-scoped governance |

---

## Tutorial package — atomic import and edit

Tutorial sections (topics) and Quiz sets are a **single package** — imported,
edited, versioned, and published together via `bundle_id`.

A tutorial package import creates **4 rows in one transaction**:

| Row | `content_type` | `body` shape |
|---|---|---|
| 1 | `tutorial` | `{sections: [{heading, body}, …]}` |
| 2 | `quiz_set_1` | `{questions: [{stem, options, correct_answer, explanation}, …]}` |
| 3 | `quiz_set_2` | same |
| 4 | `quiz_set_N` | one row per quiz set file found in Content Store (variable count) |

The import probes which quiz set files actually exist for the source unit
(`quiz_set_1_{lang}.json`, `quiz_set_2_{lang}.json`, etc.) rather than
assuming exactly 3. All rows share `bundle_id`. Status transitions and
version bumps operate on the bundle atomically.

---

## What it is

Epic 12 builds **Path 2** — school-imported and customised content — for
lessons and tutorial packages.

Five deliverables:

1. **School library** — curriculum adoption tracking, fork creation, onboarding flow (TA-0)
2. **Import** — teacher clicks "Import" on any OOB lesson or tutorial package;
   a private fork is created and content lands in the school's namespace
3. **Edit** — teacher edits sections and quiz questions; saves as draft versions
4. **Governance** — school admin reviews, approves, and publishes; nothing reaches
   students without this step
5. **History** — every save is a new version row; any approved version can be re-published

---

## Current state

### What already exists and where it falls short

| Table | What it tracks | Limitation |
|---|---|---|
| `grade_curriculum_assignments` (0029) | One `curriculum_id` per `(school_id, grade)` | Points to OOB ID for most schools; no fork concept |
| `classroom_packages` (0038) | `(classroom_id, curriculum_id)` | Classroom-level; no school-level catalog |
| `curricula.school_id` (0002) | Owner school for school-owned curricula | No column tracking which OOB curriculum was forked from |
| `GET /curricula/catalog` (Phase C) | OOB curricula and content readiness | Browse-only; no selection persisted |

**Gap:** no school-level record of "we adopted and forked OOB curriculum X."
Addressed by `school_adopted_curricula` (TA-0) and `curricula.source_curriculum_id`.

### What exists (content layer)

| Component | State |
|---|---|
| `GET /content/{unit_id}/lesson` | Reads Content Store unconditionally. No DB override lookup. |
| `unit_content_overrides` | **Does not exist.** |
| `unit_content_active_versions` | **Does not exist.** |
| `curricula.source_curriculum_id` | **Does not exist.** |
| `school_adopted_curricula.forked_curriculum_id` | **Does not exist** (table doesn't exist yet). |
| Import endpoint | **Does not exist.** |
| Write / governance endpoints | **Do not exist.** `content/router.py` has only GET endpoints. |
| Pipeline guard | **Does not exist.** |
| Lesson / tutorial editor | **Does not exist.** Unit viewer is read-only. |
| School Content Governance dashboard | **Does not exist.** |

### What can be reused

- **`content_source` taxonomy** — `web/components/demos/scenario/types.ts`
- **`SBMarkdown` renderer** — `web/components/content/Markdown.tsx`
- **Scenario builder pattern** — `web/components/demos/scenario/` for section editing
- **`write_audit_log()`** — append-only audit events
- **Curriculum resolver** — unchanged; returns fork UUID once `grade_curriculum_assignments` updated

---

## Why it matters

**Adoption blocker.** Teachers won't use a platform where AI is the sole author.
Import-and-edit gives control without the blank-page problem of Path 3.

**OOB library stays clean.** School edits never touch platform files or OOB rows.

**FERPA provenance.** `content_source` + `last_edited_by` + `edited_at` + `ai_model`
+ `source_curriculum_id` on every version gives a complete chain of custody.

**Governance foundation.** The school admin publish gate, fork model, and version
history established here are the foundation for copyright, backup, and
housekeeping features. Build it right once.

**BriefCase reuse.** Same fork/import pattern, content_source taxonomy, version
history, and governance workflow needed for BriefCase scenario authoring
(UC-301, UC-302, UC-307, UC-308).

---

## Rough scope

| Phase | What gets built | Size |
|---|---|---|
| **TA-0** | School curriculum library — adoption tracking, fork columns, onboarding empty-state | M |
| **TA-1** | Migration 0051 — `unit_content_overrides` + `unit_content_active_versions` | S |
| **TA-2** | Import endpoint — fork creation pre-flight + lesson (1 row) + tutorial package (N rows) | M |
| **TA-3** | Edit endpoint + status-transition endpoints (submit / approve / reject / activate) | M |
| **TA-4** | Pipeline guard — skip units with school overrides | S |
| **TA-5** | Serving path — DB-first via `unit_content_active_versions` | M |
| **TA-6a** | Unit status list page — teacher content overview for a curriculum | S |
| **TA-6** | Teacher editor — lesson editor + tutorial package editor | M |
| **TA-6b** | School Content Governance dashboard — queue, diff view, approve, publish, batch | M |
| **TA-7** | Platform admin review queue — provenance badge | S |
| **TA-8** | Version history panel — bundle history, restore | M |

**Total estimated size: 4S + 7M ≈ 9–11 engineer-weeks**

---

### TA-0 detail — School curriculum library

**TA-0a — Migration 0050.**

```sql
-- Add fork lineage column to curricula
ALTER TABLE curricula
    ADD COLUMN source_curriculum_id TEXT
        REFERENCES curricula(curriculum_id) ON DELETE SET NULL;

-- School-level curriculum adoption catalog
CREATE TABLE school_adopted_curricula (
    adoption_id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id             UUID         NOT NULL
                                       REFERENCES schools(school_id) ON DELETE CASCADE,
    curriculum_id         TEXT         NOT NULL
                                       REFERENCES curricula(curriculum_id) ON DELETE RESTRICT,
    forked_curriculum_id  TEXT
                                       REFERENCES curricula(curriculum_id) ON DELETE SET NULL,
    grade                 INTEGER      CHECK (grade BETWEEN 1 AND 12),
    adopted_by            UUID         REFERENCES teachers(teacher_id) ON DELETE SET NULL,
    adopted_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    status                TEXT         NOT NULL DEFAULT 'active'
                                       CHECK (status IN ('active', 'deactivated')),
    notes                 TEXT,
    UNIQUE (school_id, curriculum_id)
);
```

`curriculum_id` = the OOB curriculum adopted from the catalog.
`forked_curriculum_id` = the school-owned `curricula` row created at first import
(NULL until then).
`source_curriculum_id` on `curricula` tracks which OOB curriculum a school row
was forked from — enables pipeline guard and future content lineage queries.

RLS on `school_adopted_curricula`: school session SELECT/INSERT/UPDATE WHERE
`school_id = current_school_id`. Service role bypass.

Deletion guard: `PATCH .../library/{adoption_id}` (deactivate) returns 409 if
the curriculum (or its fork) has rows in `classroom_packages` or
`grade_curriculum_assignments` for this school.

> **Table relationships:**
> `grade_curriculum_assignments (school_id, grade) → curriculum_id` answers
> "what curriculum is Grade 8 studying right now?"
> `school_adopted_curricula` answers "what OOB curricula has this school adopted,
> and what is their private fork UUID?"
> `curricula.source_curriculum_id` answers "which OOB curriculum was this
> school-owned curricula row forked from?"

**TA-0b — Onboarding empty-state.**

When `school_adopted_curricula` count is zero, the school portal home shows:

> *"Your content library is empty. Browse the catalog to add curricula
> and get started."*

Single **Browse catalog** CTA. Disappears once the first curriculum is adopted.

**TA-0c — Backend endpoints.**

| Endpoint | What it does |
|---|---|
| `GET /schools/{school_id}/library` | All adopted curricula with metadata, fork status, content readiness. Filterable by `status`, `grade`. |
| `POST /schools/{school_id}/library` | Body: `{curriculum_id, grade?, notes?}`. Adopts OOB curriculum. `forked_curriculum_id` starts NULL. Returns 409 if already adopted. Fires `curriculum.adopted` audit event. |
| `PATCH /schools/{school_id}/library/{adoption_id}` | Body: `{status?, notes?}`. Deactivate/reactivate. Blocked if assigned (deletion guard). |

**TA-0d — School portal "Our Library" page** at `/school/library`.

Columns: Curriculum name, Grade, Owner, Content readiness bar, Fork status
(Not started / Imported N units), Status badge, Adopted by, Adopted at.

Actions per row: **Assign to grade**, **Browse content**, **Deactivate**.

**Browse OOB catalog** links to `/school/catalog` where an
**Add to our library** button calls `POST /schools/{id}/library`.

---

### TA-1 detail — Migrations

**Migration 0051a — `unit_content_overrides`**

```sql
CREATE TABLE unit_content_overrides (
    override_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id            UUID        NOT NULL REFERENCES schools(school_id),
    curriculum_id        TEXT        NOT NULL,   -- school's forked UUID
    unit_id              TEXT        NOT NULL,
    lang                 TEXT        NOT NULL DEFAULT 'en',
    content_type         TEXT        NOT NULL DEFAULT 'lesson',
    bundle_id            UUID,                   -- links tutorial package rows
    content_source       TEXT        NOT NULL
                                     CHECK (content_source IN
                                     ('imported','ai_assisted','teacher_authored')),
    source_curriculum_id TEXT,                   -- OOB curriculum imported from
    body                 JSONB       NOT NULL,   -- append-only; never updated
    ai_model             TEXT,                   -- LLM that generated OOB original
    last_edited_by       UUID        REFERENCES teachers(teacher_id),
    edited_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    review_status        TEXT        NOT NULL DEFAULT 'draft'
                                     CHECK (review_status IN
                                     ('draft','pending_review','approved','rejected')),
    version_number       INT         NOT NULL DEFAULT 1,
    UNIQUE (curriculum_id, unit_id, lang, content_type, version_number)
);

CREATE INDEX idx_uco_bundle ON unit_content_overrides (bundle_id)
    WHERE bundle_id IS NOT NULL;
```

**Body is append-only; `review_status` is mutable.** New content = new row at
`version_number = MAX + 1`. Status transitions = UPDATE `review_status` on the
latest row.

To prevent version number races on concurrent edits, TA-3 must acquire
`SELECT ... FOR UPDATE` on the latest version row before computing `MAX + 1`.

**Migration 0051b — `unit_content_active_versions`**

```sql
CREATE TABLE unit_content_active_versions (
    school_id      UUID         NOT NULL REFERENCES schools(school_id),
    curriculum_id  TEXT         NOT NULL,
    unit_id        TEXT         NOT NULL,
    lang           TEXT         NOT NULL,
    content_type   TEXT         NOT NULL,
    override_id    UUID         NOT NULL
                                REFERENCES unit_content_overrides(override_id),
    activated_by   UUID         REFERENCES teachers(teacher_id),
    activated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (school_id, curriculum_id, unit_id, lang, content_type)
);
```

`school_id` is included in the PK for RLS simplicity even though the
fork UUID in `curriculum_id` already guarantees school isolation under Option B.
One row per `(school_id, curriculum_id, unit_id, lang, content_type)` — the
mutable pointer to the version students currently see. `unit_content_overrides`
is body-append-only; this table is the only fully mutable state in the content layer.

---

### TA-2 detail — Import endpoint

`POST /schools/{school_id}/curricula/{curriculum_id}/units/{unit_id}/import`

`{curriculum_id}` in the URL is the **school's fork UUID** (obtained from
`school_adopted_curricula.forked_curriculum_id` or created in step 3 below).
Clients that do not yet have a fork UUID should call
`GET /schools/{school_id}/library` first to retrieve or trigger fork creation.

**Pre-flight: fork creation (runs once per adoption)**

1. Verify `school_adopted_curricula` row exists for `(school_id, source_curriculum_id)`
   with `status='active'`. Returns 403 if not adopted.
2. Check `school_adopted_curricula.forked_curriculum_id` — is a fork already created?
3. If NULL (first import for this adoption):
   - INSERT into `curricula`: new UUID, `school_id`, `is_default=false`,
     `grade` and `name` copied from source, `source_curriculum_id = source`
   - UPDATE `school_adopted_curricula.forked_curriculum_id = new UUID`
   - UPSERT `grade_curriculum_assignments (school_id, grade) → new UUID`
     (replaces OOB ID; resolver now returns fork UUID for this school's students)
4. Use `forked_curriculum_id` as `curriculum_id` for all override rows.

**Lesson import** (`content_type: "lesson"`):

1. Pre-flight above.
2. Read `lesson_{lang}.json` from Content Store for `source_curriculum_id`.
3. Create one `unit_content_overrides` row: `content_source='imported'`,
   `version_number=1`, `review_status='draft'`, `bundle_id=NULL`.
4. Returns 201. Returns 409 if override already exists.
5. Fires `content.imported` audit event.

**Tutorial package import** (`content_type: "tutorial_package"`):

1. Pre-flight above.
2. Read `tutorial_{lang}.json` from Content Store.
3. Probe for quiz set files: read `quiz_set_1_{lang}.json`, `quiz_set_2_{lang}.json`,
   etc. until a file is not found. Record the actual count N (typically 1–3).
4. Generate `bundle_id = gen_random_uuid()`.
5. In one transaction, create N+1 rows (tutorial + quiz_set_1…quiz_set_N)
   all sharing `bundle_id`, `version_number=1`, `review_status='draft'`,
   `content_source='imported'`.
6. Returns 201 with `{bundle_id, override_ids: [...]}`.
7. Returns 409 if any row already exists.
8. Fires `content.tutorial_package_imported` audit event.

---

### TA-3 detail — Edit and governance endpoints

**Edit (teacher):**

`PUT /schools/{school_id}/curricula/{curriculum_id}/units/{unit_id}/content`

Body: `{lang, content_type, body}`.

- Acquires `SELECT ... FOR UPDATE` on the latest version row (or bundle) to
  prevent concurrent version number races.
- Creates new row(s) at `version_number = MAX + 1`, `review_status='draft'`.
- For tutorial packages: splits body into tutorial + quiz_set rows, writes all
  atomically, re-uses existing `bundle_id`.
- Validates `body` against Pydantic schema for `content_type`.
- Sets `content_source='ai_assisted'` if prior version was `'imported'` and
  body has changed.
- Fires `content.edited` audit event.

**Status transitions:**

| Endpoint | Actor | What it does |
|---|---|---|
| `POST .../submit` | Teacher | UPDATEs `review_status='pending_review'` on latest version (or bundle). Fires `content.submitted_for_review`. |
| `POST .../approve` | School admin | UPDATEs `review_status='approved'`. Does NOT yet update `unit_content_active_versions`. Fires `content.approved`. Used for batch workflows. |
| `POST .../approve-and-publish` | School admin | UPDATEs `review_status='approved'` AND upserts `unit_content_active_versions` in one transaction. Students see this version immediately. Fires `content.approved` + `content.activated`. The common single-unit path. |
| `POST .../reject` | School admin | UPDATEs `review_status='rejected'`. Body: `{reason}` stored in audit event. Fires `content.rejected`. |
| `POST .../activate` | School admin | Upserts `unit_content_active_versions` for any approved version or bundle. Used to batch-publish all `approved` units. Fires `content.activated`. |

For tutorial packages, all transitions operate on the bundle atomically.

**Rejected version recovery:** the teacher opens the unit editor; the editor
calls `GET .../content?draft=true` which returns the latest version (the
rejected body). The editor displays the rejection reason fetched from the
latest `content.rejected` audit event. Teacher edits and calls this PUT
endpoint — a new row is created at `version_number = MAX + 1` with
`review_status='draft'`. The rejected row is untouched.

---

### TA-4 detail — Pipeline guard

In `pipeline/build_unit.py::build_unit()`, before `_write_json()`, check
whether any school has imported this unit from this OOB curriculum:

```python
rows = await conn.fetch("""
    SELECT 1 FROM unit_content_overrides uco
    JOIN curricula c ON c.curriculum_id = uco.curriculum_id
    WHERE c.source_curriculum_id = $1
      AND uco.unit_id = $2
      AND uco.lang = $3
      AND uco.content_type = $4
    LIMIT 1
""", oob_curriculum_id, unit_id, lang, content_type)

if rows:
    log.info("unit_skip_school_override", unit_id=unit_id, lang=lang)
    return
```

Uses `SET app.current_school_id = 'bypass'` per pitfall #28.

This query works under Option B: school overrides are keyed by the fork UUID,
and `curricula.source_curriculum_id` links the fork back to the OOB ID the
pipeline is processing.

---

### TA-5 detail — Serving path

In `content/service.py`, on every `GET /content/{unit_id}/lesson`
(and `/tutorial`, `/quiz/{set_number}`):

1. Resolve `curriculum_id` for the requesting student (existing resolver,
   unchanged — returns fork UUID if school has imported, OOB ID otherwise).
2. Look up `unit_content_active_versions` for
   `(school_id, curriculum_id, unit_id, lang, content_type)`.
3. If found: fetch `override_id` from `unit_content_overrides`; return body
   with `content_source` from the row.
4. If not found: read Content Store file; return with `content_source='ai_generated'`.

Teachers and school admins may append `?preview=true` to see the latest draft
version (any `review_status`). This parameter is silently ignored for student JWTs.

Add `content_source: str | None` to `LessonResponse` and `TutorialResponse`
(defaults `'ai_generated'` when served from file).

---

### TA-6a detail — Unit status list page (prerequisite for TA-6)

At `/school/content/[curriculum_id]` — the teacher's content home for a
given curriculum.

Table of all units in the curriculum with columns:
Unit name, Subject, Grade, Override status badge, Latest version #,
Review status badge, Last edited by, Last edited at.

**Override status badge values:**
- `OOB` (grey) — no import; students see AI-generated content
- `Imported` (yellow) — imported, not yet edited
- `Draft` (orange) — has unpublished edits
- `Pending review` (blue) — submitted, awaiting school admin
- `Published` (green) — active version live for students
- `Rejected` (red) — latest submission rejected; needs revision

Actions per row: **Import** (if OOB), **Edit** (if imported/draft/rejected),
**View** (if published).

This page is the entry point for all teacher-side customization. It is
reachable from the school portal nav under **Content**.

---

### TA-6 detail — Teacher editor

**Lesson editor** at `/school/content/[curriculum_id]/units/[unit_id]/lesson`:

- **No override (OOB):** read-only renderer + **Import lesson** button.
  On click calls TA-2; page refreshes in edit mode.
- **Override exists (imported / ai_assisted):** edit form — one card per
  `LessonSection` (heading input + Markdown textarea + live preview side-by-side),
  one card for `key_points` (add/remove/reorder).
  **Save draft** calls TA-3 edit endpoint.
  **Submit for review** calls TA-3 submit endpoint.
- **Rejected:** editor pre-loaded with rejected body; rejection reason shown
  in a dismissible banner at top.
- `content_source` badge + review status badge always visible.

**Tutorial package editor** at `.../units/[unit_id]/tutorial`:

- Import button creates the full tutorial package.
- Two tabs: **Topics** (section CRUD — add/delete/reorder, edit heading + body)
  and **Quizzes** (question CRUD across all quiz sets — add/delete/reorder,
  edit stem/options/correct answer/explanation).
- Save and submit operate on the bundle atomically.
- Same badges as lesson editor.

---

### TA-6b detail — School Content Governance dashboard

At `/school/governance` (`role='school_admin'` only).

**Pending reviews panel:**
- All `unit_content_overrides` rows (or bundles) with `review_status='pending_review'`.
- Columns: Unit name, Content type, Version, Submitted by, Submitted at.
- **Review** → opens unit viewer showing the pending version.
- **Diff** → side-by-side comparison of the pending version body against the
  current active version body (or OOB content if no active version exists yet).
  Word-level diff highlighting. Essential for meaningful review.
- **Approve and publish** (single-unit path) and **Approve only** (batch path)
  buttons.
- **Reject** with reason input.

**Active versions panel:**
- All `unit_content_active_versions` rows for the school.
- Columns: Unit name, Content type, Active version #, `content_source` badge,
  Activated by, Activated at.
- **Publish all approved** batch action — activates all rows with
  `review_status='approved'` for this school in one transaction.
- **Revert to previous** quick action — re-activates the immediately preceding
  published version without a new review cycle (school admin is the same actor
  who published; no second approval needed).
- **View history** → TA-8 version history panel.

---

### TA-7 detail — Platform admin provenance badge

Add `content_source` badge to each unit row in `/admin/content-review` and
the version detail page. Values and colours match TA-6. Source: query
`unit_content_overrides` (highest approved/draft version) via fork
`curricula.source_curriculum_id`. Visibility only — no workflow change.

---

### TA-8 detail — Version history panel

In the school portal unit viewer, below the content: a **Version history**
collapsible panel listing all `unit_content_overrides` rows for
`(curriculum_id, unit_id, lang, content_type)` ordered by `version_number` desc.

For tutorial packages: shows the bundle as one entry (not 4 separate rows).

Each row: version number, `content_source` badge, review status badge,
editor name, `edited_at`.

**Restore:** creates a new row at `version_number = MAX + 1` copying the
selected version's body. For previously approved versions, the school admin
can choose **Restore and publish** — which skips re-review and directly
upserts `unit_content_active_versions`. For draft/rejected versions,
restore creates a new draft requiring the normal review cycle.

---

## Open questions — all resolved

| Q | Decision |
|---|---|
| Q1. Storage model | Fork/import (Option B): school-owned UUID; OOB files never written to |
| Q2. Edit granularity | Lesson + Tutorial package (sections + quiz sets atomic) in Phase 1 |
| Q3. Review gate | School admin controls approve + publish; teacher writes only |
| Q4. Pipeline re-run | (a) Always skip units with any override row; OOB and school content evolve independently |
| Q5. Scope | Resolved by Q1 — schools import into own namespace only |
| Q6. Generate draft | (a) Deferred to Phase 3 (write from scratch) |
| Q7. FERPA attribution | (b) Full chain: `last_edited_by`, `ai_model`, `source_curriculum_id` |
| Q8. Version retention | (a) Keep all versions indefinitely; copyright/archive/housekeeping will manage lifecycle |

---

## Test cases

| ID | Scenario | What is asserted |
|---|---|---|
| TA-TC-00a | New school onboards | Portal home shows empty-state + Browse catalog CTA |
| TA-TC-00b | School admin adds OOB curriculum to library | `school_adopted_curricula` row created, `forked_curriculum_id=NULL`; empty-state gone |
| TA-TC-00c | School admin deactivates adopted curriculum with no classroom assignments | Row updated to `status='deactivated'` |
| TA-TC-00d | School admin deactivates adopted curriculum assigned to a classroom | Returns 409; row unchanged |
| TA-TC-00e | Two schools adopt the same OOB curriculum | Each has their own adoption row; no collision |
| TA-TC-01 | Teacher imports a lesson for the first time (no fork yet) | Fork `curricula` row created; `school_adopted_curricula.forked_curriculum_id` updated; `grade_curriculum_assignments` upserted; one `unit_content_overrides` row created |
| TA-TC-02 | Teacher imports a second lesson from the same curriculum | No new fork row; existing fork UUID reused; one new `unit_content_overrides` row |
| TA-TC-03 | Student fetches lesson immediately after import (not yet published) | `unit_content_active_versions` has no entry; resolver returns fork UUID; serving falls back to OOB Content Store file |
| TA-TC-04 | Teacher imports tutorial package | Fork created (if first import); N+1 rows created atomically with shared `bundle_id`; N = actual quiz set count in Content Store |
| TA-TC-05 | Tutorial import from source with only 2 quiz sets | 3 rows created (tutorial + quiz_set_1 + quiz_set_2); no error for missing quiz_set_3 |
| TA-TC-06 | Teacher edits lesson, saves | New row at `version_number=2`, `content_source='ai_assisted'`, `review_status='draft'`; version 1 row unchanged |
| TA-TC-07 | Teacher edits tutorial package, saves | All N+1 bundle rows advance to `version_number=2` atomically; `bundle_id` unchanged |
| TA-TC-08 | Two teachers edit same unit concurrently | One succeeds; other receives conflict error (FOR UPDATE prevents race); no duplicate version_number |
| TA-TC-09 | Teacher submits lesson for review | `review_status` → `pending_review`; visible in governance queue |
| TA-TC-10 | School admin clicks "Approve and publish" | `review_status='approved'` AND `unit_content_active_versions` upserted atomically; students see new version |
| TA-TC-11 | School admin clicks "Approve only" on three units, then "Publish all approved" | All three `unit_content_active_versions` rows upserted in one transaction |
| TA-TC-12 | School admin rejects with reason | `review_status='rejected'`; teacher opens editor → rejection reason shown; editor pre-loaded with rejected body |
| TA-TC-13 | Teacher saves after seeing rejection | New row at `version_number=MAX+1`, `review_status='draft'`; rejected row unchanged |
| TA-TC-14 | School admin opens governance diff view | Side-by-side word-level diff of pending version vs. current active (or OOB fallback) |
| TA-TC-15 | School admin clicks "Revert to previous" | Previous active version's `override_id` upserted directly into `unit_content_active_versions`; no review cycle needed |
| TA-TC-16 | Pipeline re-triggered for OOB curriculum | Guard queries `curricula.source_curriculum_id`; units with school overrides skipped; `unit_skip_school_override` logged |
| TA-TC-17 | Teacher opens unit status list | All units shown with correct override status badge; OOB units show OOB badge |
| TA-TC-18 | School admin opens governance dashboard | Pending panel + active versions panel render correctly; batch publish button enabled only if approved rows exist |
| TA-TC-19 | School B attempts to read School A's override via edit endpoint | Returns 403; RLS on `unit_content_overrides` (school_id) prevents access |
| TA-TC-20 | Import from curriculum not in library | Returns 403; no rows created |
| TA-TC-21 | Import for unit that already has an override | Returns 409; no duplicate row |
| TA-TC-22 | Import against platform-owned target `curriculum_id` | Returns 403; school cannot create overrides under a platform curriculum |
| TA-TC-23 | Teacher saves edit with invalid body (missing required field) | Returns 422; no new version row created |
| TA-TC-24 | Teacher appends `?preview=true` as student JWT | Parameter silently ignored; active version served |
| TA-TC-25 | School admin views version history for tutorial package | Bundle shown as one entry per version; Restore creates new bundle at MAX+1 |
| TA-TC-26 | Platform admin opens review queue | `content_source` badges visible; `imported` / `ai_assisted` visually distinct from `ai_generated` |

---

## Dependencies and sequencing

```
TA-0  (school_adopted_curricula + curricula.source_curriculum_id + onboarding)
  └──► TA-1  (unit_content_overrides + unit_content_active_versions migrations)
               └──► TA-2  (import — fork creation + lesson + tutorial package)
               └──► TA-3  (edit + governance endpoints)    ┐
               └──► TA-4  (pipeline guard)                 │ parallel after TA-1
               └──► TA-5  (serving — active versions)      ┘
                            └──► TA-6a (unit status list — teacher content home)
                            └──► TA-6  (teacher editor — lesson + tutorial)
                            └──► TA-6b (governance dashboard + diff)
                                          └──► TA-8 (version history + restore)
               └──► TA-7  (admin provenance badge — any time after TA-1)
```

TA-2, TA-3, TA-4, TA-5 are independent backend tasks, parallel after TA-1.
TA-6a, TA-6, TA-6b all require TA-2 + TA-3 + TA-5.
TA-8 lives within TA-6b; build TA-6b first.

---

## What this epic does NOT cover

| Out of scope | Reason |
|---|---|
| Path 3 — write from scratch | Separate epic; blank-editor + AI-assist is a product in itself |
| Experiment import + edit | Phase 2 of this epic once Lesson + Tutorial pattern is validated |
| `head_of_department` role | Deferred to governance epic |
| Copyright management | Follow-on governance epic |
| Backup / export of school content | Follow-on governance epic |
| Housekeeping (stale draft pruning) | Follow-on governance epic |
| Multi-language simultaneous import | Per-lang for Phase 1; multi-lang import is follow-up |
| Student-visible attribution | Future UX; provenance data is in DB |
| AlexJS on teacher edits | School accepts content safety responsibility for edited content; platform AlexJS integration deferred to governance epic |
| Notifications (email/in-app) on status changes | Deferred to notifications epic; teachers/admins must check UI proactively in Phase 1 |
| Progress record versioning | Quiz answer records remain tied to `unit_id`; version-aware progress history deferred |

---

## Relationship to BriefCase

`unit_content_overrides`, `unit_content_active_versions`, the fork model,
`content_source` taxonomy, append-only version history, and the governance
workflow map directly to BriefCase UC-301, UC-302, UC-307, UC-308.
Build this pattern here; BriefCase inherits the schema and workflow.

---

*Spec finalized 2026-04-29. All questions resolved. Option B (school-owned fork
UUID) adopted for namespace isolation and governance foundation. Ready to build
from TA-0.*
