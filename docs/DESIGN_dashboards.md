# Dashboard redesign — personas, data, and what to settle first

**Started 2026-08-25.** Working document for #640.

Prompted by Venki after five QA rounds: *"Apart from the points mentioned in my
reports, you need to redesign the dashboard page for all the logins."*

Everything below is checked against the code as it stands (`main` @ `fb8c9b7`).
Where a number is currently untrustworthy, this says so — the fastest way to
waste a redesign is to lay out metrics that are wrong underneath.

---

## 0. Why this is worth doing properly

Four of Venki's separate reports were the same complaint wearing different
clothes:

| What he said | What was actually true |
|---|---|
| "My students count shows 0" | The number was right. Nothing told him it counted classrooms he leads. |
| "Units with no activity is not showing any data — is this OK?" | Empty and broken look identical. |
| "Strongest: Engineering — why not Technology?" | Correct (88 avg vs 79.3), but the working is invisible. |
| "Recent activity — looks it is not the case" | The panel promised more than it held. |

Each was answerable individually. Together they say: **the dashboards present
numbers without the context needed to trust them.** That is a design problem, not
four bugs — and it is the thing to fix, not the tile layout.

**Design principle #1: every number explains itself.** What population, what
period, and what to do about it. If a figure can't carry that, it doesn't earn a
tile.

---

## 1. The roles that actually exist

Nine, from `backend/src/core/permissions.py`. Not all need a dashboard.

| Role | Needs a dashboard? | Note |
|---|---|---|
| `student` | **Yes** | The largest audience by far |
| `demo_student` | Reuses student | Trial; no `content:feedback` |
| `teacher` | **Yes** | Currently shares the school_admin page |
| `school_admin` | **Yes** | Teacher **superset** (ADR-005), not a separate track |
| `product_admin` | **Yes** | Content + schools + feedback + audit |
| `super_admin` | Reuses product_admin | Wildcard `*`; adds authoring, streams, archive |
| `plat_admin` | Minimal | `demo:manage` only — demo leads and geo-blocks |
| `developer` | Minimal | Read + rate. Arguably needs no dashboard at all |
| `tester` | Minimal | Read + rate + annotate |

On top of the role there are **additive capabilities** (#358):
`curriculum.commission`, `curriculum.review`, `curriculum_mgmt`. A teacher may
hold these, so a teacher dashboard must handle "teacher plus curriculum duties"
without becoming a second role.

**So: four dashboards to design** — student, teacher, school admin, platform
admin. The last three admin roles get the platform dashboard with sections
hidden by permission.

### The split that can no longer be avoided

Teacher and school_admin **share one page today** (`/school/dashboard`, same
component, different scope). Since #628 that is no longer tenable: their numbers
now *mean different things*. A teacher's "pass rate" is **their assigned grades'**;
a school admin's is **the whole school's**. The page does not say which you are
looking at.

That is a live source of exactly the confusion Venki keeps reporting, and it is
the strongest argument for separating them as part of this work rather than after.

---

## 2. Personas

Not invented — derived from what each role can actually do and how often they
plausibly do it.

### 2.1 Student — *"What should I do next?"*

- **Grades 5–12.** Reading level targets 1–2 grades below their own (Content Rule #3).
- **Cadence:** daily-ish, short sessions, often on a shared or borrowed device.
- **Motivation:** finishing things, not analysing themselves. A streak matters
  more than an average.
- **Emotional state:** a dashboard full of red percentages is a reason to close
  the tab. This is the one persona where the dashboard's *tone* is part of its
  function.
- **Job to be done:** resume the thing I was doing; see I'm making progress;
  find what's next.
- **What they do NOT want:** a management report about themselves.

**Design consequence:** one obvious continue-action, progress expressed as
completion rather than judgement, and no metric a 10-year-old can't interpret.

### 2.2 Teacher — *"Who in my class needs me this week?"*

- **Scope:** their assigned grades only (post-#628).
- **Cadence:** weekly, often before a lesson or a parent conversation.
- **Job to be done:** find the students falling behind, and the units the whole
  class is struggling with — the difference between "this child needs help" and
  "I taught this badly".
- **Constraint:** everything they see about a named student is an **educational
  record** under FERPA. The dashboard is a disclosure surface, not just a report.

**Design consequence:** the primary object is *the exception*, not the average.
"3 students need attention" beats "62% average score". Named lists must be
bounded and scoped.

### 2.3 School admin — *"Is this working, and is it set up correctly?"*

- Teacher **superset** — they may also teach, so their dashboard must contain the
  teacher's job as well as their own.
- **Cadence:** weekly to monthly; heavier at term boundaries and at onboarding.
- **Two distinct jobs:**
  1. **Operational** — are teachers and students set up, is curriculum assigned,
     did the backup run, is the subscription healthy?
  2. **Outcome** — is the school getting value: adoption, coverage, results.
- **Onboarding matters disproportionately.** A brand-new school sees zeros
  everywhere and cannot tell "not set up yet" from "broken". There is already a
  6-step setup wizard (`/school/setup`) that the dashboard currently ignores.

**Design consequence:** the dashboard should change shape by lifecycle stage —
setup checklist first, outcomes later — rather than showing an empty analytics
grid to a school on day one.

### 2.4 Platform admin — *"What needs my attention across all schools?"*

- `product_admin` / `super_admin`, plus the narrow `plat_admin`, `developer`,
  `tester`.
- **Cadence:** daily operational scanning.
- **Job to be done:** content awaiting review, pipeline failures, system health,
  unresolved feedback, subscription movement — a queue, not a report.
- Currently spread across **20 sections** under `/admin`; the dashboard is one of
  them rather than the entry point to the rest.

**Design consequence:** this one is an operations console. Counts that link
straight into work queues, and freshness/staleness stated explicitly.

---

## 3. Primary data points per role

Only data that exists today. **Trust column matters** — do not design around a
figure that is currently wrong.

### 3.1 Student

Source: `GET /student/stats` (`get_stats`) + `GET /progress/student`.

| Data point | Source | Trust |
|---|---|---|
| Current streak (days) | Redis `streak:{student_id}` | ✅ |
| Lessons viewed | `lesson_views` | ⚠️ tutorials & experiments record nothing (#569) |
| Quizzes completed | `progress_sessions.completed` | ✅ since #627 |
| Pass rate | completed ∧ passed / completed | ✅ |
| Average score | `AVG(score/total_questions)` | ✅ |
| Audio sessions | `lesson_views.audio_played` | ✅ but always 0 in practice |
| Recent quizzes | `progress_sessions` newest-first | ✅ since #627 |
| Units done / total | `curriculum_units` | ❌ **denominator wrong** (#638) |
| Time spent | `lesson_views.duration_s` | ⚠️ sub-60s floors to "0m" (#570) |

**Not yet surfaced but available and arguably more useful to a student:**
next unit in their curriculum, per-subject progress, and their own quiz history
with the questions they got wrong.

### 3.2 Teacher

Source: `/reports/school/{id}/*`, all grade-scoped since #628.

| Data point | Source | Trust |
|---|---|---|
| Students in my grades | `school_enrolments` ∩ `teacher_grade_assignments` | ✅ |
| At-risk students (named) | `get_at_risk_students` | ✅ scoped since #628 |
| Units where the class struggles | per-unit pass rate | ✅ since #624/#626 |
| First-attempt pass rate | `progress_sessions` | ✅ |
| Active students in period | `lesson_views` | ⚠️ inherits #569 |
| Quiz attempts | `progress_sessions` | ✅ since #627 |
| Curriculum health tiers | `_health_tier` | ⚠️ depends on avg attempts (fixed #626) |
| Unreviewed feedback | `feedback` | ✅ since #600 |
| Trends week-over-week | aggregated | ⚠️ ordering wrong (#592) |
| Units with no activity | derived | ❌ **doesn't measure real coverage** (#590) |
| Alerts | `report_alert_settings` | ⚠️ dismissal doesn't persist (#574) |

### 3.3 School admin

Everything the teacher sees (unscoped), plus:

| Data point | Source | Trust |
|---|---|---|
| Setup completeness (6 steps) | `web/lib/school/setup-checklist.ts` | ✅ **unused by the dashboard** |
| Teachers: count, roles, grade assignments | `teachers`, `teacher_grade_assignments` | ✅ |
| Students: enrolled, active, by grade | `school_enrolments` | ✅ |
| Classrooms and their packages | `classrooms`, `classroom_packages` | ✅ largely unpopulated |
| Curriculum adopted / forked / pending review | `school_adopted_curricula`, `unit_content_overrides` | ✅ |
| Subscription plan, seats used vs limit | `school_subscriptions` | ✅ |
| Storage quota used | `school_storage_quotas` | ✅ |
| Build allowance / credits remaining | build allowance tables | ✅ |
| Last backup + its outcome | `curriculum_backups` | ✅ since #637 |
| Restore requests awaiting them | `backup_restore_requests` | ✅ |
| Pipeline jobs running / failed | `pipeline_jobs` | ✅ |

**Seats used vs limit, storage, and build credits are the three that carry
commercial consequence and none currently appear on the dashboard.**

### 3.4 Platform admin

| Data point | Source | Trust |
|---|---|---|
| Content awaiting review | `content_subject_versions` status | ✅ |
| Pipeline jobs by status | `pipeline_jobs` | ✅ |
| System health probes | `/healthz`, `/readyz` | ✅ |
| Unresolved student feedback | `feedback` | ✅ |
| Schools: total, active, trialling | `schools`, `school_subscriptions` | ✅ |
| Subscription analytics | `/admin/analytics/subscriptions` | ✅ |
| Demo leads / demo accounts | demo tables | ✅ |
| Audit log volume | `audit_log` | ✅ |
| Backups across all schools | `curriculum_backups` | ✅ since #637 |
| CI status | external | ⚠️ |

---

## 4. What else belongs in this conversation

The parts not covered by (b) and (c) that will decide whether the redesign lands.

### 4.1 Don't enshrine broken metrics

Three figures are wrong *right now* and would be baked into a new layout:

- **#638** — units-done denominator sums every stream at a grade (4/56 should be 4/29)
- **#590** — "units with no activity" doesn't measure real coverage
- **#569** — tutorials and experiments record no lesson-view analytics, so "time
  spent" and "lessons viewed" understate every student who uses them

**Fix these before or during the redesign, not after.** A prettier wrong number
is worse than an ugly one, because it invites trust.

### 4.2 Empty and partial states are the common case

Every school starts at zero, and the demo is *still* mostly zeros. A design
validated only against populated data will fail its most important audience:
a school on day one deciding whether this works.

Three states per surface, deliberately: **not set up yet** (with the next
action), **set up but no activity yet**, and **populated**. The setup checklist
already exists and should drive the first.

### 4.3 Design for the scale we don't have yet

The demo has **6 students and 2 schools**. A table that reads beautifully at 6
rows is unusable at 600. Decide now which surfaces are lists (and therefore need
search, sort, pagination, and a bounded default) and which are summaries.

### 4.4 Every tile should imply an action

A number a teacher can't act on is decoration. "3 students inactive 14+ days"
→ links to those three. "Pass rate 38%" → which units dragged it down.

Where no action exists, ask whether the tile should.

### 4.5 The privacy line runs through this design

A teacher's dashboard naming struggling students is an **educational record**
(FERPA). Post-#628 those lists are grade-scoped; the redesign must not widen
them again for visual convenience. Aggregates in small cohorts also
de-anonymise: a "grade average" where the grade has one student is that
student's score.

### 4.6 Accessibility and responsive are requirements, not polish

WCAG 2.1 AA is a project standard: 4.5:1 contrast, labelled controls, keyboard
reachable. A dyslexia-friendly font toggle already exists and the redesign must
keep it working.

Venki asked separately whether the portal works on mobile/tablet (#639). It has
never been deliberately tested at those widths. Students especially will not all
be on laptops. **Pick the supported widths before designing, not after.**

### 4.7 Sequence

Suggested: **student dashboard first** — clearest single job, largest audience,
least political — to establish the pattern, then teacher, then school admin
(splitting the shared page at that point), then platform admin.

### 4.8 How we'd know it worked

Worth agreeing up front, or "better" stays a matter of taste:

- Venki (or a new school admin) can answer *"what does this number mean and what
  do I do about it?"* for every tile, without asking.
- A brand-new school sees a useful first screen, not an empty grid.
- A teacher finds the students needing help in one click.
- No dashboard shows a figure listed as untrustworthy in §3.

---

## 5. Open questions

Consolidated into **§8 — Decisions needed** at the end of this document, where
they sit alongside the ones your answers raised, with space to write.

---

## Appendix — what the dashboards show today

**Student** (`/dashboard`): `useProgressHistory(5)` + `useStudentStats()` —
streak, lessons viewed, quizzes completed, pass rate, average score, audio
sessions, and a recent-quizzes list.

**Teacher / school admin** (`/school/dashboard`, one shared component): overview
report, alerts, school library, teachers, class metrics. Differs only by scope,
and does not state which scope you are seeing.

**Platform admin** (`/admin/dashboard`): one of 20 sections — analytics, archive,
audit, authoring, backups, backup-schedules, build-reports, content-review,
dashboard, demo-accounts, demo-leads, demo-settings, demo-teacher-accounts,
feedback, health, help, pipeline, restore-requests, retention, schools.

## Answers

> Answers below are the product owner's, recorded verbatim on 2026-08-25.
> My analysis of what each one costs follows in §7.

**Student**
1) What am I doing this week
2) What needs to be completed this month
3) What was my subjects and score I completed
4) What is my standing in the classrooms

**Teacher/School admin**
In addition to what is listed in Appendix
a) How usage errors have been reported through the past few days
b) what is the failure fix time frame
c) errors by users

**Platform admin**
In addition to what is listed in Appendix
Whatever we have listed above for teacher/school admin.

---

## 7. What the answers require — analysis

The answers are clear and they change the shape of this work. **Six of the seven
asks need data the product does not currently hold.** That is not an objection —
it is the difference between "redesign the dashboards" and "build two new
capabilities and then redesign the dashboards", and it should be known before
anyone draws a layout.

### 7.1 Student — a plan, not just a record

The four answers describe a **plan with a horizon**, where today's dashboard only
holds a *record of the past*. That is the single biggest shift in this document.

| Ask | Data today | Verdict |
|---|---|---|
| 1. What am I doing this week | Recent activity exists; no notion of a *plan* | Partly — needs a target |
| 2. What needs completing this month | **Nothing.** No due dates anywhere in the schema | **New capability** |
| 3. Subjects and scores I completed | Exists; per-subject breakdown not surfaced | **Cheap** — mostly display |
| 4. My standing in the classroom | **Nothing.** No rank or percentile concept | **New, and needs a policy decision** |

**On 1 and 2 — where does "should" come from?**

Both imply someone has set an expectation. Two ways to source it:

- **Derive it.** Pace = units remaining ÷ weeks left in the term. Costs nothing
  from teachers, works on day one for every student, and answers both questions
  immediately. Approximate, but honest if labelled as a suggested pace.
- **Assign it.** Real teacher-set assignments with due dates: new table, teacher
  UI to set them, student view, probably reminders. A genuine subsystem.

Recommendation: **derive first, assign later.** Deriving gets both answers now
and does not depend on teachers adopting a new workflow — and if teachers never
adopt it, the derived version still works.

**On 4 — "standing in the classroom" needs a decision, not just a build**

Three things to weigh:

1. **The data does not exist and classrooms are nearly empty.** Live: 5
   classrooms, **3 classroom-student memberships** across the whole demo. A
   standing figure would be blank or meaningless for almost everyone today.
2. **It leaks other students.** In a class of four, "you are 3rd" plus knowing
   your classmates is close to knowing their results. That is educational-record
   territory, and the smaller the class the worse it gets.
3. **It cuts against the student persona.** Ranking motivates the top of a class
   and discourages the bottom — and the bottom is exactly who we most need to
   keep opening the app.

A middle option that keeps the intent without the cost: **compare to the class,
not to classmates.** "Your average is 62%, your class is at 55%" or "you have
completed more units than most of your class" — a band, not a position. It
answers "how am I doing?" without publishing a league table.

**This is a product call.** Full ranking is buildable; it should be chosen
knowingly rather than by default.

### 7.2 Teacher / school admin — this is a support surface, not a teaching one

> a) How usage errors have been reported through the past few days
> b) What is the failure fix time frame
> c) Errors by users

These are reasonable things for a paying school to want — *is this working, and
do you fix it when it isn't?* — but they belong to reliability and support
rather than teaching, and **almost none of the data exists**.

| Ask | What exists today |
|---|---|
| Errors reported recently | `feedback` has categories `content` / `ux` / `general`. Live: **10 feedback rows, 0 in ux or general** |
| Failure fix time frame | **Nothing.** Time-to-fix lives in GitHub issues, not in the product |
| Errors by users | **Nothing.** No per-user error capture. Sentry is optional and internal-only |

Also true: correlation IDs are attached to every request and errors are
structured-logged, so the raw material exists operationally — it has simply never
been aggregated or exposed to a school.

**Two ambiguities worth settling before anything is built:**

1. **"Errors by users" — product failures, or user mistakes?** Failures the
   product caused (a 500, a dead button) and mistakes a person made (wrong
   password, invalid upload) are different builds with different value. Tracking
   the second *per named teacher* also raises its own privacy question.
2. **"Failure fix time frame" — historical or forward-looking?** "Issues like
   this are usually fixed within N days" is publishable from our own history.
   "This specific problem will be fixed by Thursday" is a commitment per
   incident, and a different promise.

**A cheap honest first version** — and probably the right one — is a **status
panel** rather than analytics: *"No known issues"*, or *"We are investigating a
problem with quiz loading, reported 14:20"*, plus a list of **the school's own
reported problems and their state**. That uses feedback we already collect,
requires no new tracking, and answers the real question underneath (a) and (b),
which is *"do these people notice and act when their product breaks?"*

The fuller version — client-side error capture aggregated per school, with a
published SLA — is a real project, worth doing only if schools ask commercially.

### 7.3 Platform admin

"Whatever we have listed above for teacher/school admin" — with the difference
that for platform admin this data is **operational and already partly
available**: Sentry, structured logs, health probes, pipeline job status, and the
audit log. The gap is aggregation and presentation, not capture.

So the same panel is much cheaper here, and is the natural place to build it
**first** — prove the shape internally where the data already exists, then decide
what a school should see.

### 7.4 What this means for sequencing

The earlier suggestion was "student dashboard first". The answers reinforce that,
with a caveat:

1. **Student, display-only slice** — subjects and scores completed (#3), per-subject
   progress, "this week" from derived pace. No new subsystems. Ships fast.
2. **Fix the untrustworthy metrics** (§4.1) — #638 blocks any honest "units
   completed" figure, which items 1–3 all depend on.
3. **Decide standing** (§7.1) before building anything for item 4.
4. **Platform-admin status panel** — where the error data already exists.
5. **School-facing status panel** — once the shape is proven.
6. **Due dates / assignments** — only if derived pace proves insufficient.

### 7.5 Questions this raises

Folded into **§8** below.

### 7.6 There are start dates, but no end dates — anywhere

Raised by the product owner: *"Does the grade not have an end date? If a student
is onboarded in Grade 8 and assigned subjects, do we not have start/end dates?"*

Checked across the whole schema. **Start dates yes, end dates no.**

| Exists | |
|---|---|
| `students.enrolled_at` | when the student joined |
| `school_enrolments.added_at` | when they joined that school |
| `grade_curriculum_assignments.assigned_at` | when a grade got its curriculum |
| `classroom_packages.assigned_at` | when a classroom got a package |

| Does not exist | |
|---|---|
| Academic year / term / semester | **no table or column anywhere** — a schema-wide search for `academic\|term\|semester` returns nothing |
| `curricula.year` | an integer **label** (2026), not a range |
| `curricula.expires_at` / `grace_until` | a **content-retention clock** (1 year from creation, #90) — not a school calendar — and **0 of 19 curricula have a value** |
| `GRADE_PROMOTION_DATE` | **unset**, so `promote_student_grades` is a permanent no-op — **students never advance a grade** |

**The only "term" in the product is a hardcoded date.** `_period_start()` treats
1 September as the start of the academic year. That is correct for
MilfordWaterford (CA) and wrong for **ABC School (IN**, April–March**)** — whose
admin is the person filing these reports. Filed as **#642**.

#### Why this matters more than it first looks

One small addition — **an academic year on the school, start and end** — unblocks
four separate things:

1. **"What should I complete this month"** (student ask #2) gets something to
   count down to.
2. **"This term"** in reports stops being a hardcoded northern-hemisphere guess.
3. **Grade promotion** becomes schedulable at all; today it cannot run.
4. **Retention and renewal** could align to a school year instead of a rolling
   12 months from creation.

That is a stronger argument for building it than the dashboard alone would make,
and it is why A2 has been revised.

### 7.7 Why the calendar matters — and what that means for its design

Two reasons given by the product owner, recorded verbatim:

> a) It will allow us to track the performance of different entities (viz. study
> progress, the infrastructure response to the classes)
>
> b) We are assigning study material to students — a calendar will allow us to
> measure the strength/load of the study material and tune it up or down over a
> long period of time.

Both hold, and together they **change what the calendar has to be**. Two date
columns on `schools` is enough to answer "when does this month end". It is not
enough for either of these.

#### (b) is the sharpest idea in this document

Here is why it matters more than it first reads: **today, difficulty and timing
are confounded and cannot be separated.**

A unit with a poor pass rate might be genuinely too hard — or it might have been
taught the week before exams, or straight after a holiday, or last in a term when
everyone had stopped. We currently cannot tell those apart, which means
`curriculum_health`'s "struggling" tier is not safe to act on as a content
signal. The calendar is precisely what de-confounds it.

**Most of the raw material already exists:**

| Signal | Where |
|---|---|
| Intended order of units | `curriculum_units.sort_order`, `.sequence` |
| Actual difficulty | `progress_sessions.attempt_number`, `passed`, `score`, timings |
| When a grade got its curriculum | `grade_curriculum_assignments.assigned_at` |
| When a classroom got a package | `classroom_packages.assigned_at` |
| **When in the school year any of it happened** | **missing — this is the gap** |

So (b) is closer to buildable than it appears. What is missing is only the axis.

This also feeds the product's actual IP: the scoping layer. A measured
difficulty signal per unit, normalised by where it fell in the year, is what
lets the next generation of that content be tuned deliberately rather than by
impression.

#### Two cautions on (b), worth settling before measuring

1. **Small cohorts are noise.** The whole demo holds **43 completed sessions**. A
   unit judged "too hard" on three students' results is not a finding. Any
   tuning loop needs a minimum cohort size before it is allowed to act, and
   should say so rather than silently averaging four data points.
2. **Optimising for pass rate optimises for easiness.** If every unit students
   struggle with gets tuned down, the curriculum converges on trivial. "Correctly
   loaded" needs defining against something — intended difficulty, expected time,
   or a teacher's judgement — *before* the measurement starts, or the loop will
   quietly select for the wrong thing.

#### (a) has a second half worth naming

"Infrastructure response to the classes" — load follows the academic rhythm.
Term starts, exam weeks and holidays are the real drivers of traffic, not a flat
average. A calendar makes capacity planning **predictive** instead of reactive,
and academic-year transitions are already flagged as a concern in
`SCALABILITY.md`.

#### What (a) and (b) require that a start/end date does not

| Requirement | Why |
|---|---|
| **Terms / periods within the year** | "Week 8" is meaningless if the year is one undivided block |
| **Holidays and breaks** | Otherwise pace maths and load baselines are both wrong — a two-week break reads as two weeks of no effort |
| **Stable week numbering** | Cohort-to-cohort and year-to-year comparison need a common frame |
| **Historical calendars retained** | You cannot compare 2026 with 2027 if the 2026 calendar was overwritten |
| **Per school** | Two demo schools already differ (IN: Apr–Mar, CA: Sep–Jun) |

That is a first-class entity, not a field in the onboarding form. **Written up as
[`ADR_007_academic_calendar.md`](ADR_007_academic_calendar.md)**, which grew well
beyond the calendar itself once the promotion and grading questions surfaced:
grade enrolments with outcomes, per-school grading scales, and the freeze/
correction rules. Retention, promotion, reporting periods and content tuning all
come to depend on it.

#### A third reason, and a fourth

Worth adding to the two above:

3. **Year-over-year comparison of the same curriculum.** This is the compounding
   asset: the curriculum gets measurably better each year, and "this year's
   Grade 8 versus last year's" becomes answerable.
4. **"On track" becomes possible at all** — which is the student ask (§7.1) and
   the reason this came up.

---

## 8. Decisions needed — write your answers here

Grouped by whether they block work. Options are lettered so a one-letter answer
is enough; add reasoning only where you want it recorded.

Leave anything you're not ready to decide — a blank answer is information too.

---

### Group A — blocks the first build

**A1. Student "standing in the classroom": what shape?** *(§7.1)*

Live today: 5 classrooms, **3 classroom memberships**. Rank also implicitly
exposes classmates in a small class.

- **(a)** True rank — "3rd of 12"
- **(b)** Comparison to the class average — "you 62%, class 55%" *(my suggestion)*
- **(c)** Percentile band — "ahead of most of your class"
- **(d)** Drop it for now, revisit when classrooms are populated

**Answer:**
Go with (b)
---

**A2. Where does "this week / this month" come from?** *(§7.1, revised — see §7.6)*

**Correction to my earlier answer.** I suggested deriving a pace from "units
remaining ÷ weeks left in the term". There is **no term to count down to** — the
product has start dates but no end dates anywhere (§7.6). So option (a) is not
free after all; it needs an academic year first.

- **(a)** Add an academic year to the school (start + end), then derive pace from
  it — **now specified in [ADR-007](ADR_007_academic_calendar.md)**, which also
  covers promotion, grading scales and the freeze rules
- **(b)** Build real teacher-set assignments with due dates *(bigger; still needs
  a calendar to sit in)*
- **(c)** Academic year now, assignments later
- **(d)** Neither — drop "this month" and show only "this week" as recent activity

**Answer:**
go with (a)
---

**A3. Which untrustworthy metrics get fixed first?** *(§4.1)*

These change what can honestly be shown. #638 in particular blocks any "units
completed" figure, which three of your four student asks depend on.

- **(a)** #638 units-done denominator — blocks student items 1–3
- **(b)** #590 units-with-no-activity — blocks a teacher tile
- **(c)** #569 tutorial/experiment analytics — understates time spent everywhere
- **(d)** All three before any dashboard work

**Answer:**
go with (d)
---

### Group B — needed before the teacher / admin work

**B1. "Errors by users" — which meaning?** *(§7.2)*

- **(a)** Product failures — 500s, dead buttons, things we broke
- **(b)** User mistakes — wrong password, invalid upload
- **(c)** Both, separated on screen

Note: (b) means tracking a named teacher's error rate, which has its own privacy
question.

**Answer:**
go with (c)
---

**B2. "Failure fix time frame" — which promise?** *(§7.2)*

- **(a)** Historical typical — "issues like this are usually fixed in N days" *(publishable from our own history)*
- **(b)** Per-incident commitment — "this will be fixed by Thursday" *(a real SLA)*
- **(c)** Neither — just show current status and what we're working on

**Answer:**
go with (a)
---

**B3. Start the status panel where?** *(§7.3)*

- **(a)** Platform admin first — the data already exists there *(my suggestion)*
- **(b)** School-facing first — it's who asked
- **(c)** Both together

**Answer:**
go with (c)
---

**B4. One page per role, or one page with scoped variants?** *(§1)*

Teacher and school_admin share a component today, and since #628 their numbers
mean different things with nothing on screen saying which.

- **(a)** Split them into separate pages *(my suggestion)*
- **(b)** Keep one page, but state the scope prominently
- **(c)** Keep as-is

**Answer:**
go with (a)
---

### Group C — can be decided later, but cheaply now

**C1. Do `developer` / `tester` / `plat_admin` get a dashboard at all?**

- **(a)** No — land them directly on the one screen they use
- **(b)** Yes — a minimal one

**Answer:**
go with (a)
---

**C2. Supported screen widths.** *(§4.6)*

Venki asked whether the portal works on mobile/tablet (#639). It has never been
deliberately tested at those widths.

- **(a)** Desktop only for now — say so publicly
- **(b)** Desktop + tablet
- **(c)** Full responsive down to phone *(students especially won't all be on laptops)*

**Answer:**
go with (b)
---

**C3. Commercial data — seats used, storage, build credits.** *(§3.3)*

Carries the most consequence of anything on the school admin's screen, and is
currently invisible.

- **(a)** On the school admin dashboard
- **(b)** Keep in billing, link from the dashboard
- **(c)** Dashboard only when close to a limit

**Answer:**
go with (a)
---

### Anything else

Space for asks that don't fit the questions above — including anything you want
the dashboards to do that isn't in §2 or §3.

**Notes:**


---

## 9. What the answers commit us to

All ten answered 2026-08-25. Summarised, then the consequences worth knowing
before work starts.

| | Decision |
|---|---|
| A1 | Standing = **comparison to the class average**, not a rank |
| A2 | **Academic year first**, then derive pace from it (ADR-007) |
| A3 | **All three untrustworthy metrics fixed before any dashboard work** |
| B1 | Errors means **both** product failures and user mistakes, shown separately |
| B2 | Fix time frame = **historical typical**, not a per-incident commitment |
| B3 | Status panel built for **platform admin and schools together** |
| B4 | Teacher and school admin become **separate pages** |
| C1 | `developer` / `tester` / `plat_admin` get **no dashboard** |
| C2 | Supported widths: **desktop + tablet**. Phone explicitly out |
| C3 | Commercial data **on the school admin dashboard** |

### Three things these answers change

**A1 needs "class" defined, or it is blank for almost everyone.** Comparison to
the class average is only computable if *class* means the student's **grade
cohort at their school**. It cannot mean *classroom*: the demo holds 5 classrooms
and **3 classroom memberships** in total, so a classroom-based average would be
empty for nearly every student.

It also needs a **minimum cohort size**, for the same reason content tuning does
(ADR-007 Decision 7): a "class average" where the grade has one other student
*is* that student's score. Below the threshold the comparison should be withheld,
not approximated.

**A3 (d) is the most expensive answer given, and deliberately so.** Fixing all
three before any dashboard work front-loads real effort — and #569 is the
largest, because tutorials and experiments record no analytics at all, so it is
new instrumentation rather than a query fix. The discipline is right: none of
them can be laid out honestly until they are true. Worth going in knowing the
dashboard does not start immediately.

**B1 (c) + B3 (c) together are the biggest single chunk in this document.**
Errors in both senses, shown to schools *and* platform admin, with historical fix
times. Almost none of that data is captured today: no per-user error record
exists, and `feedback` holds 0 rows in its `ux` / `general` categories. It is a
new capability, not a dashboard panel — and "user mistakes attributed to a named
teacher" carries its own privacy question that should be settled before capture
begins, not after.

### Sequence this implies

1. **#638** — units-done denominator. Blocks three of the four student asks, and
   is wrong on Venki's reports today.
2. **#590**, **#569** — the other two metrics (A3d).
3. **ADR-007 steps 1–4** — academic year + backfill + settings, which also
   delivers #642 on its own.
4. **Student dashboard** — the display-only slice, now with honest numbers and a
   calendar to derive pace from.
5. **Split teacher / school admin** (B4), with commercial data added (C3).
6. **Status panel** (B1c/B2a/B3c) — the new capability, scoped separately.

Phone support is out of scope by C2; that should be stated publicly rather than
left for a student to discover.


---

## 10. Venki's wireframe proposal (26 Aug) — evaluation

He sent two annotated wireframes: one dashboard for admin/teacher, one for
students. This is a real step forward — an actual layout with stated
constraints, not a request — and most of it should be taken.

### What it proposes

**Admin / teacher.** A shorter header, a "welcome back" banner with an alert
count and *View full report*, a period selector (7d / 30d / term), seven tiles
(Enrolled Students · Active · Lessons Viewed · Pass rate 1st attempt · Quiz
attempts · Unreviewed Feedback · Audio play rate), then two wide cards (Units
with struggles · Units with no activity). Left rail grouped **TEACH**
(Classrooms, Student Progress, Alerts) / **REPORTS** / **SETTINGS**.

**Student.** The same shape — period selector, four tiles, the same two wide
cards, plus a *Recent Quizzes* panel down the right.

**His three notes:** admin sees the school and a teacher sees their grades;
Reports should expand/collapse like Settings; and *"avoid scroll in the
dashboard page"*.

### Take directly

- **The period selector, and saying what it does or does not filter.** His
  caption — *"only these cards change with the selector"* — is more honest than
  anything on the page today.
- **Grouped left rail** (TEACH / REPORTS / SETTINGS). Clearer than the flat list.
- **Reports expanding like Settings.** Small, obviously right.
- **Shorter header.** Also obviously right.
- **"Avoid scroll"** as a design constraint, with the caveat below.
- **Student Progress belongs under TEACH**, answering his question: it is the
  teacher's core job ("who needs me this week"), where REPORTS is periodic and
  exportable.

### Three things in it that the data does not support

| On the wireframe | Live reality |
|---|---|
| **Audio play rate** tile, on both dashboards | **0 audio plays across 86 lesson views, ever.** A permanently-0% tile on the most valuable screen real estate. |
| **Alerts count** in the header ("105 alerts") | **233 unacknowledged, none ever acknowledged** — because dismissal does not persist (#574). A badge that only ever grows is noise, and a fix for #574 has to land before the badge means anything. |
| **Units with no activity** card, on both | #590 — this measure does not reflect real unit coverage. Prominent placement of a figure we know is wrong. |

None of these are reasons to reject the layout; they are reasons the tiles behind
it need fixing first, which is exactly what answer **A3(d)** already committed
to.

### Where it conflicts with decisions already taken

**1. One dashboard for admin and teacher (his) vs separate pages (answer B4a).**

His version is "same layout, different data", which is what exists today and is
what produced the confusion in §0 — the page never states which scope you are
seeing. Since #628 a teacher's "pass rate" means *their grades'* and an admin's
means *the school's*.

These are reconcilable: keep one layout, but **state the scope on the page** —
"Your grades: 8, 10" against "Whole school". That is cheaper than two pages and
fixes the actual defect, which was never the layout but the silence about what
the numbers cover.

**2. His student dashboard is a teacher's dashboard with fewer tiles.**

Pass rate, quiz attempts, units with struggles, units with no activity, audio
play rate — these are management metrics. The product owner's own answers for
the student were different:

> 1) What am I doing this week · 2) What needs to be completed this month ·
> 3) What were my subjects and score I completed · 4) What is my standing in
> the classrooms

**None of those four appear on his wireframe**, and none of his student tiles
answer them. This is the sharpest conflict in the document and needs deciding by
the product owner, not by me: the persona work (§2.1) says a student wants "what
do I do next", not a report card about themselves, and tone is part of that
screen's function.

**3. Reports for students, including Export CSV.**

He proposes Trends, Unit performance, Quiz attempts and Export CSV for students.
Trends and Unit performance are teacher framings; and it is worth asking what a
Grade 5 student does with a CSV. Plausible for Grades 11–12, or for a parent —
neither of which is a persona we have defined.

**4. "Avoid scroll" against desktop + tablet (answer C2b).**

Seven tiles, two wide cards and a side panel without scrolling is achievable at
desktop width and very hard at tablet. Either the no-scroll rule applies to
desktop only, or the tile count comes down. Worth resolving before layout work,
because it decides how many tiles survive.

### What is missing from both wireframes

- **Empty and partial states** (§4.2). A new school sees this grid full of
  zeroes with no way to tell "not set up" from "broken". The setup checklist
  already exists and neither wireframe uses it.
- **Commercial data** — seats used, storage, build credits — which answer
  **C3(a)** placed on the school admin dashboard. Not present.

### Recommendation

Adopt the layout, the rail grouping, the period selector and its honesty
caption, the shorter header, and Student Progress under TEACH. Fix #590, #574
and the audio tile before the tiles that depend on them are drawn. Treat the
student dashboard as **unresolved** until the conflict between his wireframe and
the four student questions is settled.
