# Pending product decisions — #589, #572, #576

**Prepared 2026-08-24.** Every claim below was verified against the current
`main` (`ff42de2`) and the live demo database on the same day, because parts of
the original issues are now stale — #616 and #622 shipped fixes that changed
what is actually broken.

Each section is structured the same way: **what is true today** → **what is
already fixed** → **the decision you actually have to make** → **options with
their real costs** → **recommendation**.

---

## #589 — Restore requests: the 2030 row that will never run

**Status:** issue CLOSED. The residue is untracked.

### What is true today (verified)

The validator is live and working. `backend/src/backup/schemas.py:23` sets
`RESTORE_SCHEDULE_MAX_HORIZON_DAYS = 30`, and `validate_scheduled_at` rejects
both past dates and anything beyond the horizon. The frontend field is relabelled
from "Schedule for" to **"Preferred time"**
(`web/app/(school)/school/restore-requests/new/page.tsx:317`).

**There is still no scheduler.** `grep scheduled_at` across
`src/backup/tasks.py` and `src/core/celery_app.py` returns **zero** hits. Nothing
reads the column back. The restore lifecycle only advances when a human clicks
acknowledge/execute (super admin) or confirm (school). That is now *by design* —
the field is a preference, not a promise — which is what the relabel encodes.

Live demo, right now — **two** restore requests, **both still `submitted`**:

| created | `scheduled_at` | verdict |
|---|---|---|
| 2026-08-17 | 2030-11-17 | **beyond horizon** — predates the validator |
| 2026-08-20 | 2026-09-16 | within horizon |

The 2030 row was created at **13:33:56 UTC**; the fix (#595) merged at
**16:50:07 UTC the same day** — a gap of **3 hours 16 minutes**, not the "3 days"
I first told you. The narrowness is the point: a row can be created minutes
before a rule lands and then display a promise the system no longer makes.

### The decision

**What do we do with rows created under the old rules?** The 2030 row is
displayed as awaiting admin action. Nothing will action it at that date. Anyone
reading that table today is still misled — exactly the defect #589 was about,
for data that predates its fix.

| Option | Cost | Consequence |
|---|---|---|
| **1. Leave it** | Zero | Fine on a demo with two rows. Wrong the moment a real school has history. The misleading display persists indefinitely. |
| **2. Clamp on read** | Small — display-layer only | Beyond-horizon dates render with "an administrator will action this" instead of a date. Non-destructive, reversible, and covers any future rows created under rules that later change. |
| **3. One-off cleanup** | Small — a data migration | `NULL` out `scheduled_at` beyond the horizon. Cleanest display, but destroys the school's stated preference, and a `NULL` cannot be distinguished from "never specified". |

### Recommendation

**Option 2.** It fixes the misleading display without discarding what the school
actually asked for, and it is the only option that also protects against the next
rule change. Option 3 throws away user intent to solve a rendering problem.

### Worth raising separately

Even the *valid* 2026-09-16 row sits at `submitted` and will not act on its own.
That is correct per the new design, but there is **no SLA and no notification** —
a school admin who states a preferred time gets no signal that a human has or
hasn't picked it up. Not part of this decision; worth its own issue if schools
will rely on it.

---

## #572 — Should one person be a student at two schools?

**Status:** OPEN. Half of it already shipped.

### What is already fixed (#616, live)

The message is no longer a dead end. `_duplicate_email_detail`
(`backend/src/school/router.py:813`) now distinguishes two cases:

- the clash is **on this school's roster** → name it; the admin can fix it
- the clash is **elsewhere** → say the address is already registered across
  StudyBuddy and give a contact route — **without naming the other school**,
  which would leak another tenant's data

So "Message + recourse", the small half of this issue, is done.

### What is true today (verified)

`students.email` carries a **global** `UNIQUE NOT NULL` constraint
(`alembic/versions/0001_phase1_initial_schema.py:113`), unchanged through
migration 0037. This is deliberate — ADR-005 Decision 2.

The concrete case: `chnsuri@gmail.com` was an active student of
**MilfordWaterford**, so adding her to **ABC School** failed. Cross-school
isolation was working correctly; the roster was right.

ADR-005 **Decision 3 was never implemented** — `grep user_account_archive
deactivated_at` across `src/` and `alembic/` returns **zero** hits. There is no
soft-delete, no archive, and no school-admin path to remove a student
(that is **#581**).

### The decision

**Can one person hold accounts at two schools?** Today the schema silently
answers "no". That answer was never made deliberately at the product level —
it is a constraint from the Phase 1 schema that ADR-005 later ratified.

| Option | Cost | Consequence |
|---|---|---|
| **A. Keep global uniqueness ("no")** | Zero code | Honest and already true. A student changing schools requires an operator. Fails for real cases: a student enrolled at two institutions, or a tutoring centre plus a school. |
| **B. Scope uniqueness per school ("yes")** | **Large.** Migration, plus an audit of **every** lookup assuming one row per address | Unblocks legitimate multi-school students. `login_local_user` becomes ambiguous — which account does an email log into? That is exactly **#578**, where the same assumption already causes a teacher to shadow a student. |
| **C. Keep "no", but make it recoverable** | Medium — implements ADR-005 Decision 3 | Global uniqueness stays; deactivation archives the row and **frees the address**. Solves the common case (abandoned/mistyped/left-the-school) without the ambiguity of B. Also closes **#581**. |

### Recommendation

**C.** The reported case was not really "a person at two schools" — it was an
address stranded at a school she had left, with no way to release it. C fixes
that and closes #581, while leaving the genuine multi-school question open until
there is real demand.

Choosing **B** means committing to answer "which account does this email log
into?" first — #578 must be resolved before, not after.

### Related

- **#578** — email uniqueness is per-*table*, so a teacher row can shadow a
  student row and make them unreachable. Blocks option B.
- **#581** — no delete/deactivate at all. Closed by option C.

---

## #576 — Teacher scoping: is *grade* the right unit?

**Status:** OPEN. Partly shipped today (#622).

### What is already fixed (#622, live)

Two endpoints now enforce the grade-assignment model that already existed:

- `GET /reports/school/{id}/roster` — including the unfiltered case
- `GET /reports/school/{id}/student/{student_id}`

`_permitted_grades()` returns `None` for `school_admin` (unrestricted, per
ADR-005: school_admin is a teacher **superset**) and the assigned grade list for
a plain teacher. The originally reported exposure — a Grade-8 teacher reading a
Grade-10 student's full report card — is closed.

### What is still exposed (verified today)

Only `roster` and `student_report` call `_permitted_grades`. **Six endpoints
remain unscoped**, all in `backend/src/reports/router.py`:

| endpoint | line | what leaks |
|---|---|---|
| `overview` | 216 | school-wide counts; G10 unit codes in a G8 teacher's summary |
| `unit/{unit_id}` | 233 | per-unit performance for any grade |
| `curriculum-health` | 285 | every unit's health tier |
| `feedback` | 301 | student feedback across grades |
| `trends` | 337 | school-wide trend lines |
| `at-risk` | 397 | **named at-risk students** from other grades |

`at-risk` is the sharpest of these: it names individual students flagged as
struggling.

These are aggregate-shaped, which is why #622 stopped short — the fix for them
depends on the decision below.

### The decision

**Is a *grade* the right entitlement unit?**

The model in the database (`teacher_grade_assignments`, migration 0023) says a
teacher is entitled to a **whole grade**. But a real secondary teacher teaches
**one subject to particular classes** — a Grade 10 maths teacher has no business
reading Grade 10 English results for students they never teach.

We also already have **classrooms** (`classrooms`, `classroom_students`,
migration 0038) and **streams** (migration 0044/0045), which express a finer
relationship the reports layer ignores entirely.

| Option | Cost | Consequence |
|---|---|---|
| **1. Grade is the unit — finish the sweep** | Small. Apply `_permitted_grades` to the six endpoints | Consistent with what is built and enforced elsewhere (roster upload). Closes #576. A Grade-10 maths teacher still sees Grade-10 English data. |
| **2. Classroom is the unit** | Large. New scoping model; every report re-queried through `classroom_students`; teachers with no classroom see nothing | Matches how schools actually work and is the strongest FERPA position. Needs classrooms to be populated — today they are largely not, so this could show teachers an empty product. |
| **3. Grade now, classroom later** | Small now, medium later | Closes the live exposure immediately; revisits the unit when classrooms are actually in use. Risks becoming permanent. |

### Recommendation

**3.** The six endpoints leak today, and option 2 cannot ship safely until
classrooms are populated — enforcing an empty model would lock teachers out of
their own reports. Take the grade-level sweep now, and treat "classroom as the
entitlement unit" as a separate, deliberate piece of work rather than a stalled
prerequisite.

If you pick **1**, say so explicitly and I will close #576 on completion. The
difference between 1 and 3 is only whether we record the intent to revisit.

### Worth noting

Aggregate endpoints raise a real question that grade-scoping does not answer:
should a teacher see *school-wide* aggregates at all? A school-wide pass rate
is arguably a management figure, not a teacher's. Scoping `overview` to the
teacher's grades changes what the number *means* — that is a product choice, not
just a security fix, and it is the reason I did not silently pick one.

---

## Summary

| # | The question | Recommendation | Blocked on |
|---|---|---|---|
| 589 | What to do with pre-validator rows showing dates that will never run | **Clamp on read** | Your call only |
| 572 | Can one person be a student at two schools? | **Keep "no", make it recoverable** (ADR-005 Decision 3) | #578 blocks the "yes" path |
| 576 | Is a grade the right entitlement unit? | **Grade now, classroom later** | Classrooms are not yet populated |
