# ADR-001 — Tenancy Model, Subscription Model, and School-as-Primary-Entity

**Date:** 2026-04-05
**Status:** Accepted
**Branch at decision:** `feat/demo-teacher-flow`

---

## Context

During a review of the school-as-primary-entity model, three foundational architectural
decisions were clarified and locked in. These supersede earlier exploratory work in
migrations 0022 (private teacher tier) and the individual student subscription path.

---

## Decision 1 — School/Institution Is the Only Primary Entity

### Rule
Every user in the system belongs to a School/Institution. There are no users that exist
outside a school context.

### How all personas map to this rule

| Persona | How they register | School contact email | Teacher email |
|---|---|---|---|
| Public school / private school | Admin registers institution | `admin@school.edu` | Same — first teacher = school_admin |
| Private tutor | Registers themselves as a school | `tutor@gmail.com` | Same — they are the school_admin teacher |
| Home schooler | Registers family as a school | `parent@gmail.com` | Same — they are the school_admin teacher |

Nothing prevents `schools.contact_email` and the first `teachers.email` from being the
same address. `register_school()` already uses the same email for both. This is correct
and intentional.

### Entity rules

| Entity | Uniqueness | Authority |
|---|---|---|
| School | `contact_email` (add UNIQUE constraint — see Gaps) | Self-registered |
| Teacher | `email` globally UNIQUE | Onboarded by school only (`invite_teacher`) |
| Student | `email` globally UNIQUE | Onboarded by school only (roster upload) |
| Teacher ↔ Grade | `UNIQUE (teacher_id, grade)` | Set by school admin |
| Student ↔ Grade ↔ Teacher | `UNIQUE (student_id, grade)` | Set by school only |

### Consequences — dead code to remove

The following were built under an older multi-tier model and conflict with this decision:

| Migration | Tables | Reason for removal |
|---|---|---|
| `0022` | `private_teachers` | Replaced by school_admin teacher = same email as school |
| `0022` | `teacher_subscriptions` | School subscription covers billing |
| `0022` | `student_teacher_access` | School enrolment covers access |
| Phase 5 | `subscriptions` (individual student) | All students enter through a school |

---

## Decision 2 — Subscription Is School-Level Only

### Rule
The School/Institution is the sole billing entity. A school subscription covers all
teachers and students enrolled in that school.

### Subscription table

`school_subscriptions` (migration `0019`) — one row per school:
- `plan`: `starter | professional | enterprise`
- `status`: `trialing | active | past_due | cancelled`
- `max_students` / `max_teachers`: seat limits
- Stripe customer and subscription IDs

### Entitlement flow

```
Student requests content
  → backend checks school_subscriptions WHERE school_id = student.school_id
  → status IN ('active', 'trialing') AND seat count < max_students → 200
  → status = 'past_due' → 402
  → student.school_id IS NULL (orphan) → 402
```

### Dedicated instance tier (future)

If a school district or government body requires a fully isolated deployment (separate
cloud account, separate DB), this is offered as a separate commercial tier. Technically
it is Option A (separate instance per tenant). The code is identical — only the
deployment topology changes. This is a sales/commercial decision, not an architectural
one for the shared SaaS.

---

## Decision 3 — Multi-Tenancy Model: Shared Instance with PostgreSQL RLS

### Options considered

| Option | Description | Decision |
|---|---|---|
| A | Separate full-stack instance per school | Rejected for shared SaaS — 12× cost and ops burden |
| B | Shared instance, row filtering in app code only | Rejected — isolation relies entirely on bug-free application code |
| C | Shared instance, PostgreSQL Row-Level Security (RLS) | **Accepted** |

### Why Option C

- **Single infra cost** — one cluster serves all schools in a region.
- **DB-enforced isolation** — RLS policies mean isolation is provable to security auditors:
  _"The database engine prevents cross-tenant data access regardless of application behaviour."_
- **FERPA / COPPA compliance story** — student educational records are physically scoped
  at the DB session level. No school's data is readable in another school's session.
- **Scales to thousands of tenants** without re-architecture.

### How RLS works here

1. Every tenant-scoped table has an RLS policy:
   ```sql
   ALTER TABLE teachers ENABLE ROW LEVEL SECURITY;
   CREATE POLICY tenant_isolation ON teachers
     USING (school_id = current_setting('app.current_school_id')::uuid);
   ```
2. On every authenticated request, the DB connection sets the tenant context:
   ```python
   await conn.execute("SET LOCAL app.current_school_id = $1", school_id)
   ```
3. PostgreSQL enforces the policy — a query that forgets a `WHERE school_id = ...`
   clause still returns only the current tenant's rows.

### Tables requiring RLS policies

| Table | Tenant key |
|---|---|
| `schools` | `school_id` (own row only) |
| `teachers` | `school_id` |
| `school_enrolments` | `school_id` |
| `student_teacher_assignments` | `school_id` |
| `teacher_grade_assignments` | `school_id` |
| `school_subscriptions` | `school_id` |
| `curricula` | `owner_id` where `owner_type = 'school'` |
| `curriculum_units` | via `curriculum_id` join |
| `content_subject_versions` | via `curriculum_id` join |

Platform-default content (`owner_type = 'platform'`) is read-only and shared across all
tenants — no RLS restriction needed.

### Content store isolation

```
{CONTENT_STORE_PATH}/curricula/
  default-{year}-g{grade}/   ← platform default, read-only, shared
    {unit_id}/...

  {school_uuid}/             ← school-owned, private
    {unit_id}/...
```

Content paths are already school-scoped by `curriculum_id`. No structural change needed —
only the entitlement enforcement layer needs updating.

### Redis key namespacing

All Redis keys for school-scoped data must be prefixed:
```
school:{school_id}:ent:{student_id}       ← entitlement cache
school:{school_id}:cur:{student_id}       ← curriculum resolver
school:{school_id}:roster:{school_id}     ← teacher roster cache
```

Platform-default content keys remain unprefixed (shared cache, read-only).

---

## Open Gaps to Fix (from compliance review, 2026-04-05)

These are pre-RLS fixes that should land before the RLS migration:

| # | Gap | Fix |
|---|---|---|
| G1 | `schools.contact_email` has no UNIQUE constraint — two registrations with same email give confusing DB error | Add `UNIQUE` constraint in new migration |
| G2 | `teachers.school_id` nullable with no DB-level guard for non-demo teachers | Add `CHECK (school_id IS NOT NULL OR auth_provider = 'demo')` |
| G3 | `get_roster()` LEFT JOIN on `student_teacher_assignments` missing grade filter — student in 2 grades appears twice | Add `AND sta.grade = se.grade` to the JOIN |
| G4 | `UNIQUE (student_id, grade)` allows a student to hold multiple active grade assignments simultaneously | Decide: add `UNIQUE (student_id)` if a student is always in exactly one grade at a time |
| G5 | Remove `private_teachers`, `teacher_subscriptions`, `student_teacher_access` tables (migration `0022` rollback or new downward migration) | New migration `0025_remove_private_teacher_tier.py` |
| G6 | Remove individual student subscription path (`subscriptions` table, `src/subscription/router.py` student endpoints) | New migration + router cleanup |

---

## Implementation Order

```
1. Fix G1–G4 (schema corrections, no behaviour change)       → migration 0025
2. Remove private teacher tier (G5)                          → migration 0026
3. Remove individual student subscriptions (G6)              → migration 0027 + code
4. Add PostgreSQL RLS policies                               → migration 0028
5. Add SET LOCAL app.current_school_id in request middleware  → backend/src/core/
6. Audit and prefix Redis keys                               → backend/src/core/cache.py
7. Update entitlement checker to use school_subscriptions    → backend/src/core/
```
