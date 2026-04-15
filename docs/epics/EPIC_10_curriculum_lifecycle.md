# Epic 10 — Curriculum Lifecycle & Governance

**Status:** 💭 Your call

---

## What it is

Formalise access, ownership, and end-of-life for curricula so the platform can
host a shared "default library" alongside private school-owned content without
any risk of cross-tenant leakage or accidental destruction.

Three threads:

1. **Access model** — who can read, who can modify, what the "default library"
   actually means as a first-class concept.
2. **Tenancy** — school-built content is strictly private to that school.
3. **Deletion / archive lifecycle** — deletes become soft archives with a 1-year
   TTL, gated on "no active student assignments", fully audited, super-admin
   visible.

Retrieval from archive is an explicit non-goal for this epic — we log the
intent but defer scope.

---

## Current state

Most of the primitives already exist from earlier phases:

- `curricula.owner_type` ∈ `{'platform','school'}` with `school_id` nullable —
  already distinguishes default library vs school-owned.
- `curricula.is_default` boolean — older flag, overlaps with `owner_type`.
- Row-Level Security (migration 0028) — `tenant_isolation` policy on 7 tables
  including `curricula`; `app.current_school_id` session variable enforces
  school scoping.
- `retention_status`, `expires_at`, `grace_until`, `renewed_at` (migration
  0029) — lifecycle columns exist for the lesson retention feature; we can
  reuse them for archive TTL.
- `audit_log` table + `write_audit_log()` helper — already used for admin
  actions (approve/reject/publish/rollback/block).
- `student_teacher_assignments` (migration 0024) — the source of truth for
  "is this student using this curriculum?".

Gaps:

- No formal policy that says "platform-owned rows are always readable by any
  authenticated school user". Currently this works because schools query via
  endpoints that bypass RLS for `is_default=true` rows, but it's implicit.
- No `archived` retention state distinct from the retention-service lifecycle.
- No precondition check on archive: "are there active enrolments / assignments
  pointing at this curriculum's units?"
- No super-admin view to see what has been archived platform-wide.
- No Celery Beat job to hard-delete rows past their 1-year TTL.

---

## Why it matters

- **SaaS safety.** Schools paying for the platform must be confident their
  uploaded curriculum content cannot be read by another school — a single leak
  would be a compliance + reputation failure.
- **Destructive-action guardrails.** Right now nothing prevents a school admin
  from deleting a curriculum with 400 students mid-course. A gate + archive
  window makes accidental destruction reversible.
- **Platform content stewardship.** The super-admin-curated default library is
  the platform's offering; it needs explicit read-only protection from schools
  and an explicit change process for itself.
- **Compliance narrative.** Every jurisdiction-level conversation (SOC-2,
  FERPA, ISO-27001) asks "how do you track deletions of educational records?".
  Formal audit + TTL is the answer.

---

## Rough scope

| Phase | What gets built | Size |
|---|---|---|
| L-1 | **Access policy formalisation.** ADR + migration 0046 that adds an RLS policy `platform_readable` on `curricula`, `curriculum_units`, and `content_subject_versions`: `USING (owner_type = 'platform' OR school_id = current_setting('app.current_school_id')::uuid)`. Explicit refusal of writes on `owner_type='platform'` rows by any non-super-admin, enforced both in endpoint handlers and via a policy `FOR UPDATE/DELETE`. | S |
| L-2 | **"In use" query.** Single authoritative helper `is_curriculum_in_use(curriculum_id)` that joins `student_teacher_assignments` + `school_enrolments` + (optionally) `progress_sessions` within a retention window. Exposed as `GET /admin/curricula/{id}/usage` for UI and as a gate inside archive endpoints. | S |
| L-3 | **Soft archive state.** New `retention_status = 'archived'` value (separate from the retention-service lifecycle). Columns already exist: `retention_status`, `expires_at`. Migration to add a CHECK constraint accepting the new value and an index on `(retention_status, expires_at)`. | S |
| L-4 | **Archive endpoints.** `POST /admin/curricula/{id}/archive` (super-admin for platform, school_admin for own), `POST /admin/curricula/{id}/unarchive` (super-admin-only), `DELETE /admin/curricula/{id}` is repurposed to call archive internally — no hard delete via API. Pre-conditions: `is_curriculum_in_use` returns false; if platform-owned, caller must be super-admin. | M |
| L-5 | **Audit events.** Three new action types: `curriculum.archive`, `curriculum.unarchive`, `curriculum.hard_delete_by_sweeper`. Every call records `actor_id`, `curriculum_id`, `owner_type`, `school_id`, prior `retention_status`, new `retention_status`, `reason` (free text), `correlation_id`. | S |
| L-6 | **TTL sweeper.** Celery Beat job `sweep_archived_curricula` runs daily; deletes rows where `retention_status='archived' AND expires_at < now() - interval '1 year'`. Rows are deleted together with their `curriculum_units` + `content_subject_versions` rows (cascade or explicit). Logs each hard-delete as audit event. | S |
| L-7 | **Super-admin archive view.** New page `/admin/archive/curricula` listing archived rows across the platform with filters (owner_type, school, grade, days-until-TTL). Shows audit trail for each row. Read-only initially — retrieval is a later epic. | M |
| L-8 | **School UI treatment.** Decide what schools see during the archive window for their own archived curricula — greyed out in library with "Archived — expires 2027-04-15" tag? Hidden entirely? See Open Question 3. | S |

---

## Open questions

1. **Who can initiate archive?**
   - (a) Super-admin only for everything.
   - (b) Super-admin for platform content; school_admin for school-owned content.
   - (c) Super-admin for platform; school_admin for school-owned **only when
     `is_curriculum_in_use` returns false**; super-admin can override the
     in-use gate with an explicit reason.

2. **"In use" = what, exactly?**
   - (a) Any row in `student_teacher_assignments` (historical + active).
   - (b) Only active assignments — students currently enrolled.
   - (c) Active assignments **OR** a progress_session in the last N days.
   Matters because older default-2024 curricula may have historical sessions
   but no active students, and we probably want those archivable.

3. **Display in school UI during the 1-year archive window?**
   - (a) Hidden entirely — the curriculum simply disappears from the school's
     library.
   - (b) Shown with an "Archived" badge, read-only, students mid-course can
     finish.
   - (c) Hidden from library but still served to students who had an active
     assignment before archive (they finish; new assignments are impossible).

4. **Audit scope for platform content.**
   - (a) Audit only the destructive actions (archive / unarchive / sweep).
   - (b) Audit every read of platform content by every school — expensive and
     mostly noise, but some compliance frameworks ask for it. Might be a
     per-jurisdiction setting rather than always-on.

5. **What about content that was mid-build when archived?**
   Pipeline jobs running against an archived curriculum — cancel, let finish,
   or refuse to start? Probably "cancel on archive, refuse to start on
   archived rows" but worth confirming.

6. **TTL clock — when does the year start?**
   - (a) `expires_at = archived_at + interval '1 year'` (simple).
   - (b) `expires_at = archived_at + interval '1 year'` but pauses while there
     is a pending restore request. We haven't designed the restore flow yet,
     so punt on this.

7. **Can the TTL be shortened by super-admin?**
   Regulatory request ("delete this within 30 days") vs. the default one-year
   window. Does `PATCH /admin/curricula/{id}` accept an `expires_at` override?

8. **Hard-delete safety — what's the blast radius of the sweeper?**
   A bug in `is_curriculum_in_use` that returns false when it shouldn't could
   see the sweeper destroy live content a year later. Probably need:
   - Dry-run mode with alert on unexpected counts.
   - Pre-delete backup of row + units + version metadata to a JSONL in object
     storage.
   - Rate limiting (max N deletions per run) so a regression can't nuke the
     whole library in one night.

---

## Dependencies

- **Migration 0045 shipped** — streams registry already uses the soft-lookup
  pattern; no conflict with retention work.
- **RLS (migration 0028) in place** — formalising the `platform_readable`
  policy is an additive change.
- **Audit log infrastructure** — already in use; no new tables needed for L-5.
- **No block on hosting** — this is pure backend + migration + admin UI work;
  ships before Epic 3 (mobile) and alongside Epic 8 (onboarding).

---

## Non-goals for this epic

- **Archive retrieval / restore flow.** Explicitly deferred — we log the intent
  but design the retrieval scope in a later epic once we see how the archive
  is actually used in practice.
- **Multi-region archive storage.** Archive rows live in the same DB as active
  rows; cold-storage migration to S3 Glacier is a later optimisation if
  per-row retention cost becomes noticeable.
- **Cross-school content sharing.** If a school wants to publish their
  curriculum to the default library, that's a separate "platform promotion"
  workflow — out of scope here.

---

## Your decisions / notes

Fill in the **Your answer** field under each question. "My lean" is a default
recommendation — circle it, override it, or write your own reasoning. When all
eight are answered, this section becomes the spec we ticket against.

---

### Q1. Who can initiate an archive?

- (a) Super-admin only for everything.
- (b) Super-admin for platform content; school_admin for school-owned content.
- (c) Super-admin for platform; school_admin for school-owned **only when not
  in use**; super-admin can override the in-use gate with an explicit reason.

**My lean:** (c) — gives schools day-to-day control without risk, keeps
super-admin as the break-glass.

**Your answer:**

**Your reasoning (optional):**

---

### Q2. What counts as "in use" for the archive precondition?

- (a) Any row in `student_teacher_assignments` (historical + active).
- (b) Only active assignments — students currently enrolled.
- (c) Active assignments **OR** a progress_session in the last N days
  (suggest N=30).

**My lean:** (b) — historical assignments from past academic years shouldn't
block archival of superseded curricula.

**Your answer:**

**If (c), what N:**

---

### Q3. What do students / school admins see during the 1-year archive window?

- (a) Hidden entirely — the curriculum simply disappears from the library.
- (b) Shown with an "Archived" badge, read-only, students mid-course can
  finish.
- (c) Hidden from library, but still served to students who had an active
  assignment before archive (they finish; new assignments are impossible).

**My lean:** (c) — protects in-flight students from mid-course disruption
without letting the curriculum stay discoverable.

**Your answer:**

---

### Q4. Audit scope for platform content reads.

- (a) Audit only destructive actions (archive / unarchive / sweep).
- (b) Audit every read of platform content by every school — heavy log volume,
  but some frameworks require it.
- (c) (a) by default, (b) opt-in per jurisdiction / compliance mode.

**My lean:** (a) initially; add (c) if a paying customer asks for SOC-2 or
similar certification.

**Your answer:**

---

### Q5. What happens to a running pipeline build when its curriculum is archived?

- (a) Cancel the job immediately; mark the job as `cancelled`.
- (b) Let it finish, then the output is already archived-state content.
- (c) Refuse to archive while a build is running — return 409.

**My lean:** (a) for running jobs, and (c) as an additional guard on
`archive` — we shouldn't let archival race with a late-finishing build.

**Your answer:**

---

### Q6. When does the 1-year TTL clock start?

- (a) `expires_at = archived_at + interval '1 year'`.
- (b) Same as (a), but the clock pauses while there is a pending restore
  request (requires restore flow, out of scope for this epic).

**My lean:** (a) — keep it simple; revisit when retrieval is designed.

**Your answer:**

---

### Q7. Can super-admin shorten (or extend) the TTL?

Regulatory deletion requests ("delete within 30 days") vs. edge-case reasons
to extend beyond a year.

- (a) No — TTL is fixed at one year.
- (b) Yes, super-admin can `PATCH` `expires_at` to any future date; audited.
- (c) Shorten only (for compliance); never extend.

**My lean:** (b) — it's a rare action and always audited; flexibility is
cheap.

**Your answer:**

---

### Q8. Sweeper safety — what guardrails on the hard-delete job?

Pick all that apply:

- [ ] Dry-run mode (logs what would be deleted without acting).
- [ ] Pre-delete JSONL backup to object storage (row + units + version meta).
- [ ] Rate limit — max N deletions per run (e.g. 50).
- [ ] Alert if a single run would delete > M rows (e.g. 20), requires manual
      unblock.
- [ ] Separate Celery queue + dedicated worker so a queue backlog can't delay
      other beat jobs.

**My lean:** all five — sweeper is the one code path that can destroy live
content at scale, and the cost of guardrails is tiny compared to the blast
radius of a regression.

**Your answer (check boxes you want):**

---

### Additional notes

> Anything not covered by the eight questions above — a custom sub-scope you
> want to add, a phase you want to drop, integrations with other epics, etc.

-
-
-
