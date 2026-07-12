# Five questions from the 07-11 report, answered

Each answer is traced to the exact place in the code that decides it, so the
behaviour on screen can be matched to how the system actually works.

> **`file:line`** = source location. Two of these — **Q4** and **Q5** — surfaced
> real reporting quirks worth knowing about.

---

## Q1 — How does the subject / grade get mapped?

**The school admin sets the grade; the grade plus the school picks a curriculum;
the curriculum's units supply the subjects.**

A three-link chain:

| Link | What happens |
|---|---|
| **Grade** | Set by the school on the student screen — the school is the authority. A school student who tries to change their own grade is refused. |
| **Curriculum** | Resolved in 3 steps: the school's own curriculum for that grade → else the platform package on the student's classroom → else the default STEM package. |
| **Subjects** | Read off the curriculum's units. Display names like "Physics" come from published content, falling back to the internal code ("G11-PHYS") until then. |

The middle step is the important one: the **classroom package is how streams**
(Commerce, Science) get selected for a grade — otherwise a student lands on the
default STEM package for their grade.

- `school/enrolment_service.py:342, 365` — assignment writes the grade; school is the authority
- `auth/router.py:1050` — student self-change of grade returns 403
- `content/service.py:313–384` — the 3-step curriculum resolver
- `curriculum/router.py:528` — subject display name (`COALESCE(csv.subject_name, cu.subject)`)

---

## Q2 — Where does a logged-in student see their assigned subjects?

**Two places, both fed by the same curriculum data: Subjects (`/subjects`) and
Curriculum Map (`/curriculum`).**

The student sees subject cards; opening one reveals its units, each with a
**Lesson** and a **Quiz** button — or a **Coming soon** pill for units whose
content isn't published yet. The Curriculum Map is the same structure with
progress overlaid on each unit.

- `web/app/(student)/subjects/page.tsx`
- `StudentNav.tsx:21`
- `GET /curriculum/tree`

---

## Q3 — How do students get associated with teachers?

**Three mechanisms. The one behind the "My students" toggle is the classroom.**

1. **Classroom — the one behind "My students."** A classroom has one teacher;
   students are enrolled in it. The "My students" toggle is worked out **in the
   browser**: students in classrooms *you lead* (`classroom.teacher_id === you`).
   `school/service.py:386, 661` · `students/page.tsx:85`

2. **Direct grade assignment — the formal record.** The assignment screen writes
   one student → grade → teacher row (one teacher per grade) and syncs the
   student's grade. This is the school-owned source of truth for ownership.
   `enrolment_service.py:342`

3. **Enrolment default.** A roster upload can carry a teacher at enrolment time,
   which seeds mechanism 2. `enrolment_service.py:225`

> **Why you saw "My students (0) / All school (4)":** you were signed in as a
> **school admin** who doesn't personally lead a classroom, so zero students are
> "yours" — while all four are enrolled in the school. Assign yourself as a
> classroom's teacher (or view **All school**) to see them.

One nuance worth knowing: the reporting backend is **school-wide** — it scopes by
`school_id` only and never by teacher (`reports/service.py:52`). So "All school"
is the backend; "My students" is a client-side classroom filter layered on top.
The two association models are not synchronized.

---

## Q4 — Is the pass rate based on quiz marks, or something else?

**Quiz marks. A pass = quiz score ≥ 60%, recorded once when the quiz is
submitted. But two screens count the *rate* differently.**

| Screen | Basis |
|---|---|
| **Overview — "1st-attempt pass rate"** (`reports/service.py:135–157`) | **First tries only.** Passed first-attempts ÷ completed first-attempts. A retry never counts. |
| **At-Risk — "pass rate"** (`reports/service.py:1072–1079`) | **All attempts, lifetime.** Passed sessions ÷ all completed sessions. A fail-then-pass counts as a pass. |

> **Worth knowing:** because the two use different denominators, the same
> student's pass rate will **legitimately differ** between the Overview and the
> At-Risk screen. That's a labelling gap, not a calculation error — worth
> clarifying in the UI.

- `progress/service.py:30, 299` — the 60% threshold (`QUIZ_PASS_THRESHOLD`, `passed`)

---

## Q5 — What is the basis of the data under "Risk / Inactive"?

**Thresholds: inactive > 14 days, or pass rate < 50%. "Last active" = the
student's most recent completed quiz.**

> **Why every student showed "Inactive / —":** a student who has **never
> completed a quiz** has no session on record, so "last active" is empty — and
> the query counts an empty last-active as inactive, with pass rate shown as "—".
> Since lessons and quizzes were failing to open (the curriculum bug), **no quiz
> was ever taken**, so every student collapsed into that empty state. The screen
> was reporting **absence of data, not real disengagement.**

> ✅ **Resolved:** the content fix in **PR #506** makes lessons and quizzes open,
> so sessions get recorded. Once students actually complete quizzes, this screen
> becomes a real signal instead of an artefact.

- `reports/service.py:1050–1058` — thresholds (14 days, 50%)
- `reports/service.py:1071` — last active = `MAX(ended_at)`
- `reports/service.py:1100, 1113` — empty last-active treated as inactive
- `reports/service.py:1130` — empty pass rate rendered as "—"

---

## The bigger picture

The same root cause behind Q5 — content failing to open — is what emptied the
**Overview, Engagement, and Student Progress** screens too. Each one fails
*differently* on missing data (zeros here, "Never active" there, "Inactive / —"
on the risk screen), which made it look like four separate bugs when it was one
broken content path. **One fix (PR #506) addresses all of them.**

Q4's two-denominator mismatch and the UI labelling notes are separate, smaller
follow-ups.
