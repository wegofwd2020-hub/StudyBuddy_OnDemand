# Epic 4 — Parent Portal

**Status:** 💭 Your call

---

## What it is

A read-only view for parents/guardians to see their child's progress —
completion rate, quiz scores, streaks, and at-risk flags — without giving
them access to teacher or admin features.

---

## Current state

No parent-facing surface exists. Parents have no visibility into their child's
progress unless the teacher manually shares a CSV report. The student portal
is login-gated with school credentials that parents don't have.

The existing data model already captures everything a parent would want to see:
progress records, quiz scores, streaks, and at-risk flags are all stored.
The access control layer (JWT roles) would need a new `parent` role.

---

## Why it matters

- **Engagement:** Parents who can see progress are more likely to encourage study habits.
- **At-risk early warning:** A parent notified that their child hasn't logged in for 10 days can intervene before the teacher flags it.
- **Sales angle:** Schools are more likely to adopt a platform they can show to parents as a transparency tool.
- **FERPA:** Parents of students under 18 have a legal right to inspect educational records. A parent portal makes this self-serve rather than requiring teacher CSV exports.

---

## Design decisions to make

### Access model
**Option A — School-provisioned parent accounts:** School Admin creates parent accounts and links them to specific students. Parents log in with school credentials. Same local auth track as teachers/students.

**Option B — Student-invited:** Student approves a parent email from within their portal. Parent receives a magic-link to a read-only view — no account required.

**Option C — Teacher-shared link:** Teacher generates a time-limited read-only link for a specific student's progress. No parent account needed.

Option A gives the most control and audit trail. Option C is the fastest to build.

### Scope at v1
A minimal parent view would show: completion rate, quiz average, streak, last active date, and whether the student is at-risk. Everything a teacher sees in the Overview report — for one student only.

---

## Rough scope (Option A — provisioned accounts)

| Phase | What gets built |
|---|---|
| I-1 | `parent` role in auth system; School Admin provisions parent accounts; parent↔student linking table |
| I-2 | `GET /parent/students/{student_id}/progress` endpoint (scoped to linked students only) |
| I-3 | Parent portal web UI: simple progress card, streak, at-risk indicator |
| I-4 | Email notification: weekly summary email to parents of at-risk students |

---

## Open questions

1. **Access model:** Option A (provisioned), B (student-invited), or C (shared link)? Or start with C and evolve?
2. **COPPA:** Parents of under-13 students already must give consent. Does the parent portal change the consent flow?
3. **Notification channel:** Email only, or should parents also receive push notifications (requires mobile app)?
4. **Scope:** Progress only, or should parents be able to see quiz question details? (FERPA says they can request it; whether the portal exposes it is a product choice.)
5. **Multi-child:** A parent may have two children at the same school. Should the portal support multiple linked students from day one?
6. **School opt-in:** Should the parent portal be a per-school feature that the School Admin enables, or available to all schools by default?

---

## Your decisions / notes

> Add your thoughts here. Even rough bullet points are enough to start.

-
-
-
