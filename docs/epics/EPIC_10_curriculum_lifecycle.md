# Epic 10 — Curriculum Lifecycle & Governance

**Status:** ✅ Go — all 8 questions + 2 follow-ups resolved 2026-04-15

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
| L-1 #178 | **Access policy formalisation (Option 3 shipped 2026-04-15).** Migration 0046 adds per-command RESTRICTIVE policies on `curricula` refusing INSERT/UPDATE/DELETE on `owner_type='platform'` rows from non-bypass sessions. Schools can still SELECT platform rows via the existing permissive `tenant_isolation` policy. Child-table RLS (`curriculum_units`, `content_subject_versions`) deferred to **L-1.1 #TBD** — requires test pool setup-callback fix + `studybuddy_test` DB recreation as postgres. Manual psql smoke test verifies school session reads but cannot write platform curricula. | S |
| L-2 #179 | **"In use" query.** Single authoritative helper `is_curriculum_in_use(curriculum_id)` that joins `student_teacher_assignments` + `school_enrolments` + (optionally) `progress_sessions` within a retention window. Exposed as `GET /admin/curricula/{id}/usage` for UI and as a gate inside archive endpoints. | S |
| L-3 #180 | **Soft archive state.** New `retention_status = 'archived'` value (separate from the retention-service lifecycle). Columns already exist: `retention_status`, `expires_at`. Migration to add a CHECK constraint accepting the new value and an index on `(retention_status, expires_at)`. | S |
| L-4 #181 | **Archive endpoints.** `POST /admin/curricula/{id}/archive` and `POST /admin/curricula/{id}/unarchive`, `DELETE /admin/curricula/{id}` repurposed to call archive internally — no hard delete via API. Authorisation matrix: school_admin can archive their own content; super-admin archives platform content and can override school content with a required `reason` field (audited, surfaced in school UI). Pre-conditions: `is_curriculum_in_use=false`; curriculum has at least one published version OR zero versions; not already archived. Action cascades to all versions regardless of state (published / failed / rolled_back / draft). | M |
| L-5 #182 | **Audit events.** Four new action types: `curriculum.archive`, `curriculum.archive_by_platform_admin` (when super-admin archives school-owned), `curriculum.unarchive`, `curriculum.hard_delete_by_sweeper`. Every call records `actor_id`, `curriculum_id`, `owner_type`, `school_id`, prior `retention_status`, new `retention_status`, `reason` (required for platform-admin-overrides school content; optional otherwise), `correlation_id`. | S |
| L-6 #183 | **TTL sweeper.** Celery Beat job `sweep_archived_curricula` runs daily; deletes rows where `retention_status='archived' AND expires_at < now() - interval '1 year'`. Rows are deleted together with their `curriculum_units` + `content_subject_versions` rows (cascade or explicit). Logs each hard-delete as audit event. | S |
| L-7 #184 | **Super-admin archive view.** New page `/admin/archive/curricula` listing archived rows across the platform with filters (owner_type, school, grade, days-until-TTL). Shows audit trail for each row. Read-only initially — retrieval is a later epic. | M |
| L-8 #185 | **School UI treatment (Q3 resolution).** Archived curricula hidden from school library but still served to students with active assignments pre-dating archive. "Archived by platform admin — reason: X" banner shown to school_admin when super-admin archived their content. | S |
| L-9 #186 | **Per-jurisdiction audit mode (Q4 resolution).** `schools.compliance_read_audit_enabled BOOLEAN DEFAULT false`. When true, every read of platform-owned curriculum content by that school is logged to `audit_log` with action `platform_content.read`. Off by default; enabled per-school by super-admin for SOC-2 / FERPA / ISO customers. | S |
| L-10 #187 | **TTL override (Q7 resolution).** `PATCH /admin/curricula/{id}/expiry` — super-admin-only, updates `expires_at` to any future date, required `reason` field, audited as `curriculum.expiry_override`. Used for regulatory ("30-day delete") or exceptional ("hold for litigation") cases. | S |

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
The School can initialize the "archive" process for the content they own
The "super-admin" can archive only the content that is in "general" library

-- Any content that is not assigned to a student can only be selected for "archiving"

**Your reasoning (optional):**
The ownership of the the "content" and the "curriculum structure"  is the prime property of the school
---

### Q2. What counts as "in use" for the archive precondition?

- (a) Any row in `student_teacher_assignments` (historical + active).
- (b) Only active assignments — students currently enrolled.
- (c) Active assignments **OR** a progress_session in the last N days
  (suggest N=30).

**My lean:** (b) — historical assignments from past academic years shouldn't
block archival of superseded curricula.

**Your answer:**
Let us use (b) .
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
Let us use (c)
---

### Q4. Audit scope for platform content reads.

- (a) Audit only destructive actions (archive / unarchive / sweep).
- (b) Audit every read of platform content by every school — heavy log volume,
  but some frameworks require it.
- (c) (a) by default, (b) opt-in per jurisdiction / compliance mode.

**My lean:** (a) initially; add (c) if a paying customer asks for SOC-2 or
similar certification.

**Your answer:**
Let us use (c)
---

### Q5. What happens to a running pipeline build when its curriculum is archived?

- (a) Cancel the job immediately; mark the job as `cancelled`.
- (b) Let it finish, then the output is already archived-state content.
- (c) Refuse to archive while a build is running — return 409.

**My lean:** (a) for running jobs, and (c) as an additional guard on
`archive` — we shouldn't let archival race with a late-finishing build.

**Your answer:**
Archive is possible only when content is "Published". If the content build is in pipeline, the job is in "pending" state and hence there is not impact.
---

### Q6. When does the 1-year TTL clock start?

- (a) `expires_at = archived_at + interval '1 year'`.
- (b) Same as (a), but the clock pauses while there is a pending restore
  request (requires restore flow, out of scope for this epic).

**My lean:** (a) — keep it simple; revisit when retrieval is designed.

**Your answer:**
let us stick to (a)
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
(b)
---

### Q8. Sweeper safety — what guardrails on the hard-delete job?

Pick all that apply:

- [X] Dry-run mode (logs what would be deleted without acting).
- [X] Pre-delete JSONL backup to object storage (row + units + version meta).
- [X] Rate limit — max N deletions per run (e.g. 50).
- [X] Alert if a single run would delete > M rows (e.g. 20), requires manual
      unblock.
- [X] Separate Celery queue + dedicated worker so a queue backlog can't delay
      other beat jobs.

**My lean:** all five — sweeper is the one code path that can destroy live
content at scale, and the cost of guardrails is tiny compared to the blast
radius of a regression.

**Your answer (check boxes you want):**
All five
---

### Follow-up A (from Q1) — super-admin override on school-owned content

**Resolution:** Super-admin **can** archive school-owned content with a
written reason; audit log captures it; schools see "Archived by platform
admin — reason: X" in their UI. Rare action, always logged, no dual-approval
overhead.

Covers support cases (locked-out school admins) and compliance (court orders,
DMCA, copyright takedowns) without building a heavier process we'd rarely use.

### Follow-up B (from Q5) — archive granularity

**Resolution:** Archive acts at the **curriculum level**, not the version
level. Version-level lifecycle (published / pending / failed / rolled_back)
stays as-is; archiving a curriculum cascades to all its versions regardless
of state.

A curriculum is archivable when:
- `owner_type='school'`, **and**
- No active assignments (Q2 definition), **and**
- Either at least one version has been published, **or** no versions exist at
  all (empty shell — e.g. definition submitted but pipeline never triggered).

Platform-owned curricula: super-admin archives them following the same
assignment check. Failed / rolled-back / draft versions are swept along when
the parent curriculum is archived; no per-version archive flow.

---

### Additional notes

> Anything not covered by the eight questions above — a custom sub-scope you
> want to add, a phase you want to drop, integrations with other epics, etc.

-
-
-
