# Quiz answer review and validation for school reviewers (#762)

**Status:** design for approval, 2026-09-17
**Issue:** [#762](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/762)
**Approach chosen:** B — correct anywhere, adopting the curriculum as part of the first correction (over A "only where already adopted" and C "validation only")

## What was asked

> View all quiz questions and their correct answers · Validate that answers are
> correct · Edit incorrect answers · Track which answers have been validated.

## Decisions already taken (user, 2026-09-16/17)

1. **Scope is the school's own copy.** A correction never changes another
   school's content or the platform default.
2. **Reviewers only.** `school_admin` plus teachers holding `curriculum.review`
   may validate and correct. Any teacher may look.
3. **A correction is live immediately**, audited, with the previous version kept.
4. **Approach B**, with the fork made explicit rather than silent.

## What the code already gives us

- `POST /schools/{id}/content/{curriculum}/units/{unit}/approve` with
  `publish=true` sets `review_status='approved'` and upserts
  `unit_content_active_versions` in one transaction
  (`backend/src/school/router.py:3145-3175`). Approach B needs no new
  approve/publish machinery.
- Serving and grading agree: `get_active_override` (content/service.py:553-602)
  is the single lookup, and `resolve_quiz_answer_key` (810-841) checks the
  override before falling back to the OOB source (regression #529). A corrected
  answer is therefore graded as corrected.
- Capability guards exist: `require_review` gates `curriculum.review`
  (`school/capability_guards.py:61`); `school_admin` is an implicit superset
  (`permissions.py:110`).

## The blocker this design exists to solve

Editing requires a school-owned fork, which only exists after the school adopts
the curriculum and imports the unit (`import_unit_content`, router.py:2176-2224;
`_assert_school_owns_curriculum`, 2339-2349). Classroom packages bypass adoption
entirely (`assign_package_endpoint`, 1311-1353).

Measured on the demo (2026-09-17): **no curriculum that any class actually uses
is adopted.** ABC School — 4 adoptions, 1 fork, 10 overrides, but its 3 classroom
curricula are all unadopted. MilfordWaterford Local — 7 classroom curricula, 0
adoptions. So today neither school can correct a single question its students sit.

## Design

### 1. Where it lives

A new page: **`/school/content/[curriculum_id]/units/[unit_id]/answers`**, beside
the existing unit editor. The curriculum is in the route on purpose — a unit id
alone is ambiguous once a school has a fork, and serving already resolves
fork → source by curriculum (content/service.py). It lists every question of
every quiz set for that unit, in the language served, showing:

- the question text and its options, with the **correct one marked**;
- **Checked** state (who, when) for this school;
- **flag count** — how many of this school's students reported that question;
- a **Correct** control (reviewers only) that changes which option is correct;
- a link to the full unit editor for anything beyond the correct answer.

Questions come from the same resolution students get: the school's active
override if there is one, otherwise the content store (`get_active_override` →
store), so a reviewer always reviews what is actually served.

**Ruling:** this page changes only *which option is correct*. Editing question or
option TEXT stays in the existing unit editor. A wrong answer key is the reported
problem; rewriting content is a different job with a different review path.

**Entry points.** The school content page lists units only for curricula the
school has adopted — which, on the demo today, is none of the ones classes use.
So the primary entry point is the **Unit Performance report**, which lists the
units students actually sit: each row gains a "Review answers" link carrying that
row's curriculum. The unit editor page links to it as well, for schools that do
have adoptions.

### 2. Validation state — new table `question_validations` (migration 0072)

| column | |
|---|---|
| `school_id` | FK schools, part of PK |
| `stable_question_id` | part of PK; content-addressed (ADR-008, migration 0067) |
| `correct_text` | the correct option's normalised text at validation time |
| `validated_by` | teacher id |
| `validated_at` | timestamptz |

RLS `tenant_isolation` on `school_id`, as migration 0059 does for
`teacher_capabilities`.

Keyed by `stable_question_id` (not position) because `q1` names a slot, not a
question, and the same question appears in several sets. `correct_text` is a
snapshot: when the current correct answer no longer matches it, the page shows
**"needs re-checking"** rather than a stale tick. A correction re-validates
automatically, by the reviewer who made it.

Not stored in `question_registry` (migration 0069): that table is platform-wide
with no writer in the app, and validation is per school.

### 3. Correcting — and the adoption it may trigger

On **Correct**, the backend resolves what the school owns for that unit:

1. **Already has an active override** → new override version with the corrected
   `correct_option`, approved and published in one call.
2. **Owns a fork but no override for this unit** → import the unit, then as above.
3. **No adoption at all** (today's demo) → create the adoption, the fork, import
   the unit, then as above.

Case 3 is a real consequence: the school takes its own copy of that unit and it
stops tracking platform regeneration. So it is **not silent**:

- the reviewer sees a confirmation naming the effect before the first correction
  in a curriculum ("your school will keep its own copy of this unit; platform
  updates will no longer reach it");
- afterwards the unit is labelled **school-edited** wherever it is listed;
- the response says which of the three cases happened, and the page says so.

**Ruling:** the confirmation is per curriculum, not per question — a reviewer
fixing four questions in a unit should not confirm four times.

### 4. Who may do what

- **View** the page: any teacher of the school (`require_curriculum_view`).
- **Validate** and **Correct**: `require_review` (so `curriculum.review` holders
  and `school_admin`).
- Client-side gating hides controls, but the backend guard is the control
  (the pattern `AdministrationMenu.tsx` documents).

### 5. Audit

`write_audit_log` (`core/events.py:47-81`) on both actions:
`quiz_answer.validated` and `quiz_answer.corrected` (school, unit, stable
question id, old and new correct text, whether an adoption/fork/import was
created). None of the existing content endpoints audit today; this design adds it
for its own two actions only, and does not retrofit the others.

### 6. Student flags on the page

Per-question student feedback exists (`feedback.stable_question_id`, migration
0068) but is exposed only to platform admins (`feedback:view`). This design adds
a school-scoped, aggregate-only read: **count per question for this school's own
students**, no student identity, no free text (FERPA — the count is what tells a
reviewer where to look). Sorting the page by flag count is the default.

## API

Curriculum is part of every path, matching the page route and the existing
content endpoints — the school may be reading a platform curriculum it reaches
through a classroom package, or its own fork of it, and the two are different
content.

- `GET  /schools/{school_id}/content/{curriculum_id}/units/{unit_id}/answers?lang=en`
  → questions with correct option, validation state, flag count, and what the
  school owns for this unit (`none|fork|override`).
- `POST /schools/{school_id}/content/{curriculum_id}/units/{unit_id}/answers/{stable_question_id}/validate`
- `POST /schools/{school_id}/content/{curriculum_id}/units/{unit_id}/answers/{stable_question_id}/correct`
  body `{ "correct_option": "C", "confirm_fork": true }` — `confirm_fork` is
  required only in case 3 and only for the first correction in that curriculum.

## Consequences accepted

- A correction forks the unit; platform regeneration no longer reaches it. Made
  visible, not prevented.
- Validation is per school. Two schools validate the same question separately —
  correct under decision 1, and the cost of not having a platform loop.
- A question whose text is later regenerated gets a new `stable_question_id` and
  so loses its tick. That is the honest outcome: it is a different question.
- `revert_unit_override`'s active-pointer INSERT omits `school_id` and conflicts
  on the wrong key (router.py:2850-2863) — a pre-existing inconsistency this
  design does not touch; filed as #803.

## Testing

- Validation: recorded per school; a second school is unaffected; a changed
  correct answer turns a tick into "needs re-checking"; correcting re-validates.
- Correction, all three ownership cases, each ending with the corrected answer
  **served and graded** — the grading assertion is the point, not the row.
- Case 3 without `confirm_fork` → refused with the reason; with it → adoption,
  fork and import created exactly once, and a second correction in the same
  curriculum needs no further confirmation.
- Permissions: a plain teacher may read and is refused both writes; a
  `curriculum.review` teacher and a `school_admin` may do both; another school's
  reviewer is refused everything (cross-tenant).
- Flags: counts cover only this school's students; no identity or text in the
  response.
- Audit rows written for both actions.
- The Unit Performance row links to this page with the curriculum the row came
  from — the link is the only way an unadopted curriculum is reachable, so a
  broken link means the feature is unreachable exactly where it is needed.
