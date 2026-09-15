# ADR-007 — Academic Calendar as a First-Class Entity

**Date:** 2026-08-25
**Status:** Proposed
**Branch at decision:** `docs/dashboard-design-640`

---

## Context

### This is not a new concept — it is a specified one that was never built

`ARCHITECTURE.md` § *Academic Year Transitions* already describes an academic
calendar, a grade-promotion mechanism, and an annual operator checklist. It even
gives the config shape:

```python
ACADEMIC_YEAR_START = {
    "northern": "09-01",   # September 1
    "southern": "01-30",   # January 30
}
```

**None of it exists in the code.** `grep ACADEMIC_YEAR_START backend/` returns
nothing; `config.py` carries only `GRADE_PROMOTION_DATE`, which is unset. So this
ADR is not proposing a new idea — it is deciding *how* to implement one that has
been specified since Phase 8, and **changing two parts of that specification**
(see "Supersedes" below).

### The product has start dates but no end dates Verified across the whole schema
on 2026-08-25:

| Exists | |
|---|---|
| `students.enrolled_at` | when a student joined |
| `school_enrolments.added_at` | when they joined that school |
| `grade_curriculum_assignments.assigned_at` | when a grade received its curriculum |
| `classroom_packages.assigned_at` | when a classroom received a package |

| Does not exist | |
|---|---|
| Academic year / term / semester | **no table or column anywhere** — a schema-wide search for `academic\|term\|semester` returns nothing |
| `curricula.year` | an integer **label** (2026), not a range |
| `curricula.expires_at` / `grace_until` | a **content-retention clock** (1 year from creation, #90), not a school calendar — and **0 of 19 curricula have a value** |
| `GRADE_PROMOTION_DATE` | **unset**, so `promote_student_grades` is a permanent no-op — students never advance a grade |

### Supersedes two parts of the existing specification

**1. Region is the wrong granularity.** The specified model has two buckets,
`northern` and `southern`. Academic calendars do not follow hemispheres:

| Country | Hemisphere | Academic year | `northern` bucket says |
|---|---|---|---|
| Canada | northern | Sep–Jun | Sep — correct |
| **India** | **northern** | **Apr–Mar** | **Sep — wrong** |
| Japan | northern | Apr–Mar | Sep — wrong |

**Implementing the specification as written would not have fixed #642**, because
ABC School is in India and would still have been given 1 September. Country is
better than hemisphere, and still wrong for any school that differs from its
national norm — private versus state, or different examination boards within one
country. Only per-school is actually correct.

**2. Promotion was specified as unconditional.** The spec says the task
"increments `student.grade` by 1". That is what the code does, and it is why
#643 is a specification gap rather than only an implementation bug. Decision 6
changes it.

### The only "term" in the product is a hardcoded constant `reports/service.py::_period_start`
treats **1 September** as the start of the academic year. That is correct for
MilfordWaterford (CA, Sep–Jun) and wrong for ABC School (**IN, Apr–Mar**) — whose
admin is the person filing our QA reports. Filed as **#642**; the "This term"
filter appears on the school dashboard, the Overview report, and is the *default*
on Trends.

### What is driving this now

Four independent needs converged on the same missing concept:

1. **Student "what should I complete this month"** (#640) — there is nothing to
   count down to.
2. **Reporting periods** — "This term" is a northern-hemisphere guess (#642).
3. **Grade promotion** — cannot be scheduled at all today, *and* the
   implementation waiting behind it advances every student on the platform with
   no pass check and no school scoping (#643).
4. **Measuring the load of study material** — see below.

The fourth is the strongest and the least obvious.

### Difficulty and timing are currently confounded

A unit with a poor pass rate might be genuinely too hard — or it might have been
taught the week before exams, straight after a holiday, or last in a term when
attention had gone. **We cannot distinguish these**, which means
`curriculum_health`'s "struggling" tier is not safe to act on as a *content*
signal, only as a *this-cohort-needs-help* signal.

Most of the raw material for the content signal already exists:

| Signal | Where |
|---|---|
| Intended order of units | `curriculum_units.sort_order`, `.sequence` |
| Actual difficulty | `progress_sessions.attempt_number`, `passed`, `score`, timings |
| When material was assigned | `assigned_at` on grade and classroom assignment |
| **Where in the school year it happened** | **missing — this ADR** |

This feeds the scoping layer, which CLAUDE.md identifies as the product IP: a
difficulty signal per unit, normalised by its position in the year, is what lets
the next generation of that content be tuned deliberately rather than by
impression.

---

## Decision

### Decision 1 — The academic calendar is a per-school, first-class entity

Three new tables, all RLS-scoped per school in the manner of migration 0028:

- **`academic_years`** — `school_id`, `label` (e.g. "2026–27"), `starts_on`,
  `ends_on`, `status` (`planned` / `active` / `closed`).
- **`academic_terms`** — `academic_year_id`, `school_id` (denormalised for RLS),
  `name`, `sequence`, `starts_on`, `ends_on`.
- **`academic_breaks`** — `academic_year_id`, `school_id`, `name`, `starts_on`,
  `ends_on`. Holidays and closures.

**Terms are mandatory. There is no "no-terms" school.** A term with a start and
an end date is a familiar concept to any school and is expected to be adopted
without friction, so the product takes a stand rather than generalising around
an edge case.

The private tutor is not an exception to this — it resolves through Decision 1b.
A tutor's term is **relative**: relative to the grade the student is taking, and
to the timeframe set for that student. So a tutor also enrols a student *into a
grade, with a start and an end date*. Same structure, different origin — the
school's calendar supplies the dates for a school, and the tutor supplies them
per student.

### Decision 1b — A student is enrolled in a *grade*, for a period, with an outcome

New table **`student_grade_enrolments`** — `student_id`, `school_id`, `grade`,
`starts_on`, `ends_on`, `outcome` (`in_progress` / `cleared` / `not_cleared` /
`withdrawn`), `academic_year_id` (nullable — a tutor may have no school
calendar).

This is the structural consequence of the tutor case, and it is worth more than
that case alone:

- **`students.grade` stops being the truth.** Today it is a single mutable
  integer that `promote_student_grades` overwrites, leaving no history at all.
  It becomes a cached view of the active enrolment.
- **Repeating a year becomes expressible** — a second enrolment at the same
  grade. Today the schema simply cannot say it.
- **The transcript comes for free.** A student's academic history is the ordered
  list of their grade enrolments and outcomes, which is precisely what the
  product owner identified as the point: *"the above works for the student in
  their final academic transcripts, in addition to the credibility of the school
  delivering education in compliance with common practice."*
- **Promotion becomes auditable and reversible** — close one enrolment, open the
  next — instead of an in-place `UPDATE` across every student on the platform.

### Decision 2 — Breaks are excluded from every elapsed-time calculation

Pace, "weeks remaining", load baselines and time-on-task all measure **teaching
time**, not wall-clock. A two-week holiday must not read as two weeks of no
effort by a student, nor as a drop in infrastructure load requiring explanation.

### Decision 3 — Week numbering is derived, stable, and break-aware

"Week 8 of Term 2" is computed from the calendar, excluding breaks. This is the
common frame that makes cohort-to-cohort and year-over-year comparison possible.
It is derived, never stored on progress rows — storing it would freeze a value
that a calendar correction should update.

### Decision 4 — Calendars are historical records, not editable settings

A closed `academic_year` is immutable. Correcting a past year creates a new
revision rather than overwriting, because year-over-year comparison depends on
knowing what the calendar *was* at the time the data was produced.

### Decision 5 — Reporting periods resolve from the calendar

`_period_start("term")` stops hardcoding 1 September and reads the school's
current term. Where a school has no calendar configured, the API returns the
period explicitly labelled as a rolling window rather than silently calling it a
"term" (#642).

### Decision 6 — Grade promotion is per-school, calendar-driven, and policy-gated

Three changes, and the third is the one that matters most.

**6a. Per-school, on that school's year end.** `promote_student_grades` triggers
on `academic_years.ends_on` rather than the global `GRADE_PROMOTION_DATE`. One
global `MM-DD` cannot serve an April–March school and a September–June school
simultaneously — which is precisely why it has remained unset and the task has
never run.

**6b. Promotion is gated on a school-level policy, not on the date alone.** The
current implementation is:

```sql
UPDATE students SET grade = LEAST(grade + 1, 12)
WHERE account_status = 'active' AND grade < 12
```

**No pass check, and no school scoping** — every active student on the platform
advances regardless of results (#643). That contradicts how many systems work.
As stated by the product owner: *"If a student does not clear all subjects in a
grade, they do not get to move to the next grade."*

Both policies are legitimate and schools genuinely differ:

- **Gated** — a student who has not cleared the grade repeats it.
- **Automatic** — students advance with their cohort regardless.

So the decision is **not** to hardcode a pass check any more than to hardcode
automatic promotion. `schools` carries a **promotion policy**, and the task
honours it.

**6c. "Cleared the grade" is defined: every subject assigned to that grade must
be passed.** Decided by the product owner, and the reasoning is recorded because
it raises the stature of the record: promotion is not a convenience flag, it is
an entry in a student's academic transcript, and getting it wrong is a
credibility problem for the school as much as a data problem.

Promotion is therefore **gated by default**: a student who has not cleared the
grade repeats it, and the outcome is written to their grade enrolment (1b)
rather than inferred.

The school-level policy field is retained so that a market requiring automatic
cohort progression can be served later without a migration — but **gated is the
implemented behaviour**, and nothing ships with automatic unless a customer needs
it.

**One level of definition remains open** (see §Open, below): what makes a
*subject* passed.

Note the interaction with retention. `ARCHITECTURE.md` already grants a
**30-day grace period** after promotion so students mid-unit can finish last
year's content. That is sized for a student who was promoted, not for one who is
**repeating the year** — they need the previous curriculum for the *whole* next
year. Neither the grace period nor the retention clock (#90) currently accounts
for that.

### Decision 6d — The grading scale is per-school data, not a constant

"Cleared the grade" cannot be computed until "passed" means something
school-specific. The two systems this product already serves disagree:

| System | Fail | Bands |
|---|---|---|
| **India** | below **40** | 40–60 Second Class · 60–90 First Class · 90+ Distinction |
| **USA** | below **60** | 60–69 D · 70–79 C · 80–89 B · 90+ A |

`QUIZ_PASS_THRESHOLD = 0.60` is hardcoded — the US line — and ABC School is in
India. Six of one student's attempts scored exactly 50%: a **Second Class pass**
in his own system, recorded by us as failures (#644). Note that **60 appears in
both scales and means different things** — the US pass mark and the Indian First
Class line — which is precisely why it must be data.

**Both are the same structure**: an ordered set of bands over a percentage, each
with a label and a pass flag. One table, **`grading_scales`** (+ `grading_bands`),
per school, serves both.

**The score is a fact; the classification is an interpretation.** A school that
corrects its scale must not silently rewrite history, so scales are versioned
exactly as calendars are (Decision 4), and a closed academic year keeps the scale
it was actually marked under. `progress_sessions` already stores `score` and
`total_questions`, so the fact is safe; `passed` becomes a derived cache rather
than the source of truth.

**Subject result** is then: aggregate the student's unit scores for that subject
into a percentage, and interpret it with the school's scale. **Grade cleared** is
every subject landing in a passing band — the product owner's rule, now
computable.

This is the *pass mark*, not a gradebook: no new assessment types, no
teacher-entered marks, no weights. Only the existing percentage, read with the
school's own scale.

#### Scales resolve by inheritance: school → grade → subject

A school may set the pass mark **per grade and per subject**, which real schools
do — practical subjects, languages and board-examination years commonly differ.

It is modelled as an **override hierarchy**, not as a configuration per
combination. A school with 8 grades × 5 subjects would otherwise face 40
settings to fill in and keep consistent:

| Level | Required | Resolution |
|---|---|---|
| School default | **Yes** — seeded from country, editable | Applies unless overridden |
| Grade | Optional | Overrides the school default for that grade |
| Grade + subject | Optional | Most specific; wins over both |

One row shape covers all three, with nullable `grade` and `subject`; the most
specific match wins. A school sets one scale and overrides only the exceptions.

Overrides are versioned exactly as the base scale is, so a closed year keeps the
marks it was actually judged under.

**Implementation trap.** The override key includes a subject, and
`curriculum_units.subject` is **not a stable label** — stream curricula store
abbreviated codes (`G11-PHYS`) while the human-readable name lives in
`content_subject_versions.subject_name` (pitfall #32). An override keyed on the
display name would silently fail to match for exactly the stream grades where
subject-specific pass marks are most likely to be wanted. The key must be the
resolved subject code, consistently, with a test covering a stream curriculum.

**Deliberately not supported:** per-classroom or per-student pass marks. A pass
mark that varies by individual is not a grading scale, it is an override
(Decision 6e), and conflating the two would make the transcript
uninterpretable.

**Consequence for the transcript.** If Mathematics passes at 33 and English at
40, a bare "Second Class" is ambiguous. Where marks vary by subject, the
transcript must carry the applicable pass mark alongside the result — otherwise
the credibility argument that motivated gating is undermined by the flexibility
that serves it.

### Decision 6e — Grading scales are administered by `school_admin`; teachers read

Setting a pass mark is an administrative act with transcript consequences, not a
teaching one. New permission `grading:manage`, held by `school_admin` and above.

`teacher` gets **read** access, and that is deliberate rather than an omission: a
teacher must be able to see the mark their students are being judged against —
otherwise they cannot explain a result to a student or a parent, which is the
situation the mark exists to support. The effective scale (after the
school → grade → subject resolution in 6d) should be visible wherever a result
is shown, not buried in settings.

Consistent with ADR-005, where `school_admin` is a teacher **superset**: an
administrator who also teaches keeps both.

### Decision 6f — Scales and the grade/subject mapping are bound to the academic year and frozen once it starts

Both the grading scales **and** the grade → subject mapping belong to a specific
`academic_year`, and neither may change once that year has started
(`academic_years.starts_on`). Before it, they are freely editable; that is what
the `planned` status is for.

**Why the freeze matters more than it appears.** It is what makes "cleared the
grade" well-defined at all. Without it:

- Changing a pass mark in March silently re-judges every result already recorded
  that year — a student who cleared a subject in November could fail it
  retrospectively without sitting anything.
- Adding a subject to a grade in March retroactively fails every student who had
  already cleared the grade's subjects, because "all subjects passed" is
  evaluated against a list that grew after they finished.

Neither is recoverable after the fact, because the transcript would already be
wrong. Freezing is the cheaper guarantee by a wide margin.

It also gives the "year over year" comparison in Decision 4 something solid:
a closed year is judged by the scale and subject list it actually ran under.

**Consequence:** a school must complete its grading setup during `planned`, so
this belongs on the setup checklist alongside the calendar, not in a settings
page a school discovers in month three.

### Decision 6g — A frozen year can be corrected, but never silently

Decision 6f freezes scales and the grade → subject mapping once a year starts.
Corrections remain **possible**, because a typo would otherwise stand for a full
academic year and the workarounds are worse — editing the database, or quietly
adjusting individual students. They are never silent.

**Every correction is audited.** A `curriculum.grading_corrected` audit event
records who, when, before → after, and a **mandatory reason**. The affected
academic year carries a visible marker; a corrected year does not look like an
untouched one.

**Approval is required when the correction would re-judge existing results.**

| Situation | Path |
|---|---|
| No results recorded yet that year | `school_admin` corrects. Audited. Nothing to re-judge. |
| Results already recorded | **Platform approval required**, audited, year flagged |

The distinction is impact, not ceremony. Where nothing has been marked, a
correction is indistinguishable from finishing the setup. Where results exist,
the school would be re-judging its own students — which is precisely what the
freeze exists to prevent, so the approver is deliberately outside the school.

**The impact is shown before approval, not after.** A correction is previewed as
a **dry run** stating how many students change outcome and in which direction.
"3 students move from fail to pass" and "12 students move from pass to fail" are
very different acts, and the approver must see which one they are approving. The
product already has this pattern in restore requests (BR-4), and it should be
reused rather than reinvented.

**Re-judgement is explicit.** Because a score is a fact and a classification an
interpretation (6d), a corrected scale *can* be reapplied to existing results —
but whether it is must be stated in the correction, not inferred. A student whose
outcome changes has their grade enrolment (1b) updated with the correction
recorded against it, so the transcript shows a corrected result rather than
silently presenting a different one.

### Decision 6h — A teacher may override a subject result, on the record

**Approved.** Every real system has a human remedy for the student who lands a
mark short — a re-sit, a supplementary exam, or a teacher's judgement. Without
one in the product, a school facing that case edits the student's grade directly,
and the transcript then records a promotion that never happened. The override
makes the remedy official instead of improvised.

**Scope: one student, one subject, one academic year.** An override that applied
to a cohort would be a scale change (6d) wearing a disguise, and must go through
that path instead.

**Requirements:**

- A **mandatory reason**, in the teacher's own words.
- An audit event, and a record against the student's grade enrolment (1b), so
  the outcome reads *cleared by override* rather than simply *cleared*.
- Visible to `school_admin`, who may revoke it while the year is open. Once the
  year closes it is frozen into the transcript with everything else (6f).

**The actual mark is always carried alongside the override.** This is what stops
the override becoming a rubber stamp: a numeric floor ("only within 5 marks of
passing") would be arbitrary and easy to argue with, whereas showing the real
score next to the override makes an unreasonable one self-evident to anyone
reading the transcript. It also keeps the record honest in the direction that
matters — an override can add a pass, but it can never hide a score.

**Not a substitute for a re-sit.** Attempts are already recorded per unit, so a
student retaking work raises their subject aggregate legitimately. The override
is for the case where re-sitting is not the right answer, not the default path
to a pass.

### Decision 7 — Content-load measurement is normalised by calendar position, and gated on cohort size

Any signal used to tune curriculum difficulty must:

- be normalised by **where in the term** the unit was taught, and
- be **suppressed below a minimum cohort size**, stated on screen rather than
  silently averaged.

The whole demo currently holds **43 completed sessions**. A unit judged "too hard"
on three students' results is not a finding.

### Decision 8 — "Correctly loaded" is defined before it is measured

Tuning on pass rate alone optimises for *easiness*: anything students fail gets
softened until the curriculum is trivial. The target must be expressed against
something independent — intended difficulty, expected time-on-task, or teacher
judgement — and that definition is a prerequisite for the tuning loop, not a
later refinement.

---

## Open — one item remains



**A recorded teacher override.** Decision 6d makes a subject result computable,
which removes the brittle "every single unit must pass" problem: a weak unit no
longer fails a subject outright, because the subject is judged on its aggregate.

What is still unresolved is the edge case. Even under a percentage scale a
student lands one mark short, and every real system has a human remedy —
re-sits, supplementary exams, or a teacher's judgement. "Compliance with common
practice", the stated reason for gating promotion at all, arguably requires one.

Re-sits already work mechanically: attempts are recorded per unit, so a later
passing attempt raises the subject aggregate without any new machinery.

Recommendation: allow a **teacher override recorded against the grade
enrolment** (1b). Without it a school facing a one-mark case will simply edit the
student's grade directly, and the transcript will then record a promotion that
never happened. With it, the transcript stays honest about *how* the grade was
cleared.

---

## Consequences

### Positive

- Four blocked things become possible: student "on track", honest reporting
  periods, schedulable grade promotion, and content-load measurement.
- Difficulty and timing stop being confounded, so curriculum health becomes
  usable as a content signal rather than only a cohort signal.
- Year-over-year comparison of the same curriculum becomes answerable — the
  compounding asset in a product whose IP is the scoping layer.
- Capacity planning becomes predictive: load follows the academic rhythm, and
  `SCALABILITY.md` already flags academic-year transitions as a concern.
- Retention and renewal could later align to a school year instead of a rolling
  twelve months from creation.
- Makes a **repeating student** expressible at all — today the schema has no way
  to say "stayed in Grade 8", because promotion is an unconditional bulk update.

### Negative

- **Onboarding gains a required step.** A school must describe its year before
  several features work. Mitigated by seeding a sensible default from
  `schools.country` and letting them correct it.
- Every existing school needs a backfilled calendar, and any backfill is a guess.
- Three new tables, their RLS policies, and a settings UI to maintain.
- Reporting queries gain a join they did not have.
- A gated promotion policy cannot ship until "cleared the grade" is defined
  (6c), so the calendar alone does not finish #643.

### Neutral

- Schools that genuinely have no term structure are still representable (one
  term spanning the year).
- Nothing here requires the student-facing "this month" feature to ship; it
  unblocks it without committing to it.
- The calendar is descriptive, not prescriptive: it records when teaching
  happens, and does not itself schedule or assign anything.

---

## Alternatives considered

- **Two date columns on `schools`** — rejected. Sufficient for "when does this
  month end", and for nothing else in the Context. No terms means "week 8" is
  meaningless; no breaks means pace and load baselines are both wrong; no history
  means year-over-year comparison is impossible.
- **Derive the term from `schools.country`** (option 1 on #642) — rejected as the
  primary model. Fixes the reported symptom, but adds a second hardcoded table to
  maintain and is still wrong for any school whose calendar differs from its
  national norm. Retained only as the *seed* for a new school's default.
- **Region-level calendars (`northern` / `southern`), as specified in
  `ARCHITECTURE.md`** — rejected. Academic calendars do not follow hemispheres:
  India and Japan are both northern and both run April–March. Implementing it as
  written would have left #642 unfixed.
- **A single platform-wide calendar** — rejected. The two demo schools already
  differ (IN Apr–Mar, CA Sep–Jun); this is the exact assumption that produced
  #642.
- **Reuse `curricula.year` / `expires_at`** — rejected. `year` is a label, and
  `expires_at` is a content-retention clock with a different lifecycle and owner.
  Overloading it would couple content licensing to the school timetable.
- **Hardcode gated promotion (repeat unless all subjects cleared)** — rejected.
  It matches the product owner's own schooling and many systems, but not all;
  automatic cohort progression is equally real. Hardcoding either produces a
  product that silently does the wrong thing for half its market, which is the
  same mistake as hardcoding 1 September (#642).
- **Teacher-set assignment due dates instead** — rejected as a *substitute*. It
  addresses only the student "this month" ask, leaves reporting, promotion and
  content measurement unserved, and still needs a calendar to sit inside. Remains
  a plausible later addition on top of this.

---

## Migration / rollout

Sequenced so nothing depends on a calendar that does not yet exist.

1. **Migration `00NN`** — the three tables plus RLS policies. No behaviour change.
2. **Backfill** — one `academic_year` per existing school, seeded from
   `schools.country`, `status='active'`, single term spanning the year, no
   breaks. Flagged in the school's settings as *"we guessed this — please
   confirm"* rather than presented as fact.
3. **Settings UI** — school admin edits the current year, terms and breaks. Added
   to the existing 6-step setup checklist (`web/lib/school/setup-checklist.ts`).
4. **#642** — `_period_start` reads the calendar; the rolling-window fallback is
   labelled honestly where no calendar is configured.
5. **Grade promotion (#643)** — `promote_student_grades` switches to per-school
   `ends_on`, scoped explicitly rather than relying on an implicit RLS bypass;
   `GRADE_PROMOTION_DATE` is deprecated. Ships with the **automatic** policy
   only. The gated policy follows once 6c is decided. Until then
   `GRADE_PROMOTION_DATE` stays unset — it is currently the only thing preventing
   a platform-wide unconditional promotion.
6. **Derived week numbering** helper, break-aware, with tests covering a year
   containing breaks.
7. **`ARCHITECTURE.md` § Academic Year Transitions** is updated in
   `studybuddy-docs` to match: region → school, unconditional → policy-gated,
   and the annual operator checklist becomes per-school rather than global.
8. **Downstream consumers** — student "on track" (#640) and content-load
   measurement, each specified separately. Neither is in scope here; this ADR
   only makes them possible.

Steps 1–4 are independently shippable and deliver #642 on their own.

**Status flips to Accepted when step 1 lands.**
