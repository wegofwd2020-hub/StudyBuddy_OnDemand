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

## 5. Open questions — these need answers before design starts

1. **One page per role, or one page with scoped variants?** Recommendation:
   separate teacher and school admin, since their numbers now mean different
   things.
2. **Does the student dashboard need a "next action", and what decides it?**
   Next unit in sequence, weakest subject, or teacher-assigned?
3. **Do `developer` / `tester` / `plat_admin` get a dashboard at all,** or land
   directly on the one screen they use?
4. **Which of the untrustworthy metrics (§4.1) get fixed first** — they change
   what can be shown.
5. **Supported screen widths.**
6. **Is commercial data (seats, storage, credits) on the school admin dashboard
   or kept in billing?** It carries the most consequence and is currently
   invisible.

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

1. **Student standing: rank, or comparison to class average?** (§7.1)
2. **"Errors by users": product failures or user mistakes?** (§7.2)
3. **"Fix time frame": historical typical, or per-incident commitment?** (§7.2)
4. **Is derived pace acceptable for "this week / this month",** or do you want
   real teacher-set due dates?
