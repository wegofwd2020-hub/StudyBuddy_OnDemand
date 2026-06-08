# ADR-005 — School User Roles (school_admin as superset), Single-Key Uniqueness, and Soft-Delete Accounts

**Date:** 2026-06-08
**Status:** Proposed
**Branch at decision:** `docs/adr-005-school-roles-uniqueness`

---

## Context

A functional spec for **Type 1 (Self-Managed) school user account management** was
drafted (super-admin onboards school + school-admin(s); school self-manages
teachers, students, passwords, and grade/class assignment). Two design questions
surfaced that this ADR locks in. Both refine — they do not overturn —
[ADR-001](ADR_001_tenancy_and_subscription_model.md).

**Q1 — Role model.** The spec lists three roles (school admin / teacher /
student) but also states "an account is a teacher *or* a student, never both"
and "a teacher may be promoted to school-admin." In small schools the *same
person* is both a working teacher (assigned to grades/classes) and the
administrator. Today the codebase stores a **single** `teachers.role` value
(`teacher | school_admin`); migration 0059 (#358/#359) added `teacher_capabilities`
as an **additive** grant store for giving *non-admin* teachers partial
curriculum powers, and explicitly documents "school_admin is an implicit
superset (no row needed)." The open question: keep `school_admin` as a role
value, or split the admin bit into a separate additive flag?

**Q2 — Uniqueness.** ADR-001's entity-rules table and open issue #240 propose a
`UNIQUE` constraint on `schools.name`. The product owner's call: **email-id
uniqueness alone is sufficient**; two schools may legitimately share a display
name (e.g. "St. Mary's").

**Q3 — Deletion semantics.** What does "Delete" mean when a school removes a
user? A hard delete would destroy student educational records (FERPA-relevant)
and prevent recognising a returning person. The product owner's call: **soft
delete** — deactivate + archive, with returning users re-onboarded as new
accounts.

---

## Decision

### Decision 1 — `school_admin` is a superset *role* on the teacher account, not a separate exclusive role

- An account's **type** is fixed at creation: **teacher XOR student** (spec Rule 6).
  This is unchanged.
- **`school_admin` is a role *value* on a teacher account with superset
  semantics:** a `school_admin` is *fully a teacher too* — they can be assigned
  to grades/classes and teach (spec Rules 7–9) **in addition to** holding the
  admin capabilities (spec Rule 10: view all curriculum, onboard teachers/students,
  add/remove school-admin on a teacher, change student grade/class; and Rule 11:
  create/modify curriculum + content).
- The small-school case ("one person is teacher *and* admin") is therefore
  **already satisfied** by `role = 'school_admin'`. No `is_school_admin` boolean
  and no mutually-exclusive third role are introduced.
- Promotion/demotion (spec Rule 10c) is a flip of `teachers.role` between
  `teacher` and `school_admin`, performed by an existing school_admin.
- `teacher_capabilities` (migration 0059) **remains** and keeps its stated
  purpose: granting *non-admin* teachers partial curriculum powers
  (`curriculum.commission`, `curriculum.review`, `curriculum_mgmt`).
  `school_admin` stays the implicit superset of all capabilities — **no rows
  required** for an admin.

**Authority precedence:** `school_admin` (role) ⊃ any `teacher_capabilities`
grant ⊃ plain `teacher`. Curriculum create/modify (Rule 11) requires
`school_admin`; capability grants cover the narrower commission/review gates only.

### Decision 2 — Email-id is the sole uniqueness key; school name is NOT unique

- **`schools.contact_email`** — `UNIQUE` (already enforced, migration 0025).
- **`schools.name`** — **no uniqueness constraint.** Duplicate display names are
  permitted and expected.
- **`teachers.email` / `students.email`** — globally `UNIQUE` (per ADR-001),
  unchanged. A school-admin account is bound to exactly one school via
  `teachers.school_id` (spec constraint b).

This **supersedes** the `schools.name` uniqueness item in ADR-001's entity-rules
table and **closes issue #240** as "won't do."

### Decision 3 — Account deletion is a soft delete (deactivate + archive), never a hard delete

- **"Delete" deactivates.** Deleting any school user (teacher, student, or
  school_admin) sets a `deactivated_at` timestamp; the account can no longer log
  in and is excluded from active rosters and grade/class assignment queries. The
  row is **never** physically removed by this action.
- **Archive on deactivation.** The deactivated record is moved to an archive
  store — a new **`user_account_archive`** table — carrying the deactivation
  timestamp, so a returning person can be recognised and re-onboarded later.
- **Returning user = new account.** Re-onboarding a previously deactivated person
  grants **no implicit access.** They are treated as a new account: a
  `school_admin` must re-grant their role and grade/class privileges from scratch.
  Prior assignments are **not** automatically restored.
- **Minimum-1 school-admin invariant.** Deactivating the last remaining
  `school_admin` of a school is **refused** (a school must always retain ≥1 active
  admin); ≥2 is recommended so this never blocks routine offboarding.
- **FERPA alignment.** Soft delete + archive preserves educational-record
  retention (progress, scores, lesson-view history) instead of destroying it on
  deactivation. Any eventual hard purge follows the separate retention/GDPR
  schedule (ADR-001 / data-privacy rules), **not** this action.

---

## Consequences

### Positive
- Matches operational reality: a single migration-free model (Decisions 1–2)
  serves both a 10-teacher school and a one-person tutor/home-school (the ADR-001
  personas).
- No schema change for roles — `school_admin`-as-superset already works; lower risk.
- Onboarding never fails on a benign name collision; only the email — the real
  identity key — must be unique.
- Soft delete preserves FERPA-relevant educational records and lets a returning
  person be recognised, while the "new account" rule keeps re-grant explicit (no
  stale privileges silently resurrected).

### Negative
- "Role" remains overloaded: `school_admin` encodes both "is an admin" and "is a
  teacher." Anyone reasoning about permissions must know admin ⊃ teacher. Mitigated
  by documenting the precedence chain above.
- Duplicate school names can confuse super-admin search/disambiguation in the
  console — must surface `contact_email` (the unique key) alongside name in any
  school picker.
- Decision 3 **does** require new schema + behavior (archive table, `deactivated_at`,
  roster-exclusion filtering, last-admin guard) — the one part of this ADR that is
  not migration-free.

### Neutral
- The JWT continues to carry a single `role` claim plus a `capabilities[]` array
  (the 0059 design); no token-shape change.
- Email-ids remain globally unique even across deactivation — re-onboarding the
  same address reuses it; the archive row is keyed by the original account id.

## Alternatives considered

- **Separate `is_school_admin` boolean (additive flag) alongside `role='teacher'`** —
  rejected. It duplicates what the `school_admin` superset role already expresses
  and would force every permission check to test two fields. The additive pattern
  is already correctly scoped to `teacher_capabilities` for *non-admin* partial grants.
- **A distinct, mutually-exclusive `school_admin` role that cannot teach** —
  rejected. Breaks the small-school / tutor / home-school personas (ADR-001) where
  the admin must also be assigned to grades and teach.
- **`UNIQUE (schools.name)` per issue #240** — rejected. Email-id uniqueness is
  sufficient; name collisions are legitimate. Closes #240.
- **Hard delete of school users** — rejected (Decision 3). Destroys FERPA-relevant
  educational records and loses the ability to recognise a returning person.
- **Soft delete that restores prior access on return** — rejected. Silently
  resurrecting old role/grade grants is a security risk; re-grant must be explicit.

## Migration / rollout

- **Decisions 1 & 2 — no new migration required.**
  - Roles: `teachers.role ∈ {teacher, school_admin}` and `teacher_capabilities`
    (0059) already in place; this ADR documents their intended semantics.
  - Uniqueness: `schools.contact_email` UNIQUE already exists (0025); we
    deliberately **do not** add `UNIQUE (schools.name)`.
- **Decision 3 — new migration + behavior required (follow-up):**
  - `deactivated_at TIMESTAMPTZ NULL` on `teachers` and `students`.
  - New `user_account_archive` table (RLS-scoped per `school_id`), holding the
    archived account snapshot + deactivation timestamp.
  - Roster / assignment / login queries filter out `deactivated_at IS NOT NULL`.
  - Deactivation endpoint(s) enforce the **last-active-`school_admin` guard**
    (refuse to deactivate the final admin).
  - Re-onboarding a previously-archived email creates a fresh account with **no**
    inherited role/grade grants.
  - *Tracked separately for implementation; not part of this docs-only PR.*
- **Issue hygiene:** close **#240** referencing this ADR. Cross-check #359 docs
  to ensure the "school_admin = implicit superset" wording matches Decision 1.
- **UI:** ensure any super-admin/school school-picker shows `contact_email` next
  to `name` (names are non-unique).
- **Spec linkage:** this ADR is the decision record behind the
  [School User Account Management — Functional Spec](SCHOOL_USER_MANAGEMENT.md)
  (Type 1); Decision 3 detail lives in its §6.1.
