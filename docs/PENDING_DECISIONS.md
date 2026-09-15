# Pending product decisions

**Rewritten 2026-08-24.** The previous edition covered #589, #572 and #576 —
all three were decided and shipped the same day, and all three issues are now
closed. This edition covers what is left, including two questions that only
exist *because* of those decisions.

Every claim below was verified against `main` at `8dff714` and the live demo
database on 2026-08-24. Where an issue's original text is now out of date, this
says so rather than repeating it.

| # | The question | Cost if you say yes | Blocked on |
|---|---|---|---|
| 1 | Is COPPA parental consent in scope? (#609) | Medium–large | Nothing |
| 2 | How do we stop the quiz set rotating mid-attempt? (#567) | Small–medium | Nothing |
| 3 | Which curriculum does a dual-enrolled student see? | Medium | Needs the answer to "how does a student switch context?" |
| 4 | Should a teacher see school-wide aggregates at all? | Small | Nothing |
| 5 | Should "Recent Activity" include lessons read? (#579) | Small | Nothing |
| 6 | Is a *classroom* eventually the entitlement unit? (#576 deferred half) | Large | Classrooms are unpopulated |

---

## ✅ ANSWERED — 2026-08-24

| # | Decision | What it means |
|---|---|---|
| 1 | **Out of scope** | Remove the consent page + client call; amend the CLAUDE.md claim and the About-page COPPA badge so the product stops asserting a control it does not have. |
| 2 | **Session chooses the set** | `POST /progress/session` picks and pins the quiz set; `GET …/quiz` serves what the session pinned. Removes the side-effecting GET. |
| 3 | **Primary-only now, switcher later** | Document `students.school_id` as the primary school; additional enrolments are for reporting. Revisit when a tutor actually needs to deliver content. |
| 4 | **Leave as shipped** | Teachers see their own cohort; `school_admin` sees the school. No school-wide figure below school_admin. |
| 5 | **Rename now** | "Recent Activity" → "Recent Quizzes". Fold lesson views in later. |
| 6 | **Trigger, not a date** | Revisit classroom-as-entitlement-unit when the first school creates classrooms and assigns students to them. |

The sections below are the reasoning these answers were taken from, kept as the
record of what was known at the time.

Two smaller ones are at the end: a restore-request notification gap and a
timezone-dependent test (#630).

---

## 1 — Is COPPA parental consent in scope? (#609)

**Status:** #609 is open. Its *other* half — enrol-by-code — shipped in #617, so
only this remains.

### What is true today

- `web/app/(public)/consent/page.tsx` **exists** and collects `parent_name` /
  `parent_email`.
- It posts to `POST /auth/consent`, which **does not exist** (404).
- The page is **orphaned** — nothing in the app links to `/consent`. The only
  reference anywhere is the API client call itself. So no parent is hitting a
  broken form today.
- `POST /api/v1/auth/consent` is the **last remaining entry** in the
  `KNOWN_BROKEN` allowlist in `web/tests/unit/api-contract-paths.test.ts`.
  That check has a "no stale entries" assertion, so the allowlist empties itself
  the moment the endpoint appears.
- CLAUDE.md still states the obligation as fact:

  > **COPPA:** students under 13 require parental consent before account
  > activation. Block content access until `account_status = 'active'`.

  The About page also shows a COPPA trust badge (Epic 16, S-1…S-5).

### The decision

**Do we implement COPPA consent, or stop claiming it?**

| Option | Cost | Consequence |
|---|---|---|
| **A. Build it** | Medium–large: endpoint, a verifiable-consent mechanism, routing a parent to the form, and gating `account_status` until consent lands | The documented obligation becomes true. Note "verifiable parental consent" under COPPA is a legal standard, not just an email capture — the current form would not satisfy it as written. |
| **B. Out of scope for now** | Small: delete the page and the client call, amend the CLAUDE.md claim and the About-page badge | Honest. The product stops asserting a control it does not have. Reversible if the market changes. |
| **C. Leave it** | Zero | The form and the claim both stay, neither works. This is today's state and it is the one option that is actively misleading. |

### Recommendation

**B, unless under-13 US students are a near-term market.** The current form
would not meet COPPA's verifiable-consent bar anyway, so A is bigger than it
looks — and the honest version of "we don't do this yet" is better than a badge
and a dead form.

If you pick **B**, note it also touches marketing copy, so it is a decision
about what we *claim*, not only about code. If you pick **A**, the first
question is which verification method — that is the expensive part, not the
endpoint.

---

## 2 — How do we stop the quiz set rotating mid-attempt? (#567)

**Status:** open since 2026-08-10. This is the "quiz-set model question" I have
been carrying as an open item.

### What Venki reported

> "If you don't answer any questions and leave it for a few mins, it
> automatically takes and shows Set 2… once I start taking the quiz after
> answering 1 or 2 questions, if I don't carry out any activities it takes to
> the next set."

### Mechanism

`GET /content/{unit_id}/quiz` **mutates state as a side effect of a read**:
`get_next_quiz_set()` advances the per-unit rotation pointer on *every* call.
On the client, `useQuiz` inherits a 60s `staleTime` and React Query's
`refetchOnWindowFocus: true`. Idle 60s, switch tab, come back → refetch →
pointer advances → different questions.

### Why it is worse than an annoyance — and what changed yesterday

The **graded** set is pinned per session (`quizset:{session_id}`, pitfall #35).
That pin is correct, but it pins *grading*, not *display*. `question_id` is
`q1…qN` in every set with different answers, so nothing errors — the student is
silently marked against questions they were never shown.

**Updated by #627 (shipped 2026-08-24):** `create_session` now reuses an
unanswered session, so the session — and therefore the pinned set — is stable
across reloads. That narrows the bug:

- **Refocus BEFORE the first answer:** the pointer advances, the display
  changes, and the set is pinned at first answer from the same pointer. Display
  and grading now agree. **This half is effectively fixed.**
- **Refocus AFTER the first answer:** the set is already pinned, but a refetch
  still changes the questions on screen. **Still broken, and this is exactly the
  case Venki described.**

### The decision

| Option | Cost | Consequence |
|---|---|---|
| **A. Session chooses the set** — `POST /progress/session` picks and pins it; `GET …/quiz` serves the set the session pinned | Medium | Removes the side-effecting GET entirely. Display and grading cannot diverge by construction. Touches the rotation contract, so "a second attempt gets a different set" needs re-testing. |
| **B. Quiz endpoint accepts the session's pinned set** and serves that | Small–medium | Fixes the divergence without redesigning rotation. The GET stops mutating on the session path, though the pointer still advances for callers with no session. |
| **C. Client `staleTime: Infinity`** on `useQuiz` | Trivial | Masks the symptom. The side-effecting GET remains, so any remount, retry, or dev double-render still rotates. Not sufficient alone. |

### Recommendation

**A**, with C as an immediate mitigation if you want the demo quiet before the
proper fix. A is the only one that makes the invariant structural — "the set you
see is the set you are graded on" stops depending on nobody calling a GET twice.

Worth settling before or with **#532** (quiz UX rework): skip-and-return makes
mid-quiz refetches far more likely.

---

## 3 — Which curriculum does a dual-enrolled student see? *(new, from #572)*

**Status:** created by yesterday's decision. Not yet filed as an issue — awaiting
this answer.

### What works now

A student can hold enrolments at several schools (#631). The reported case — a
school plus an external tutor running different classes — now provisions
correctly, appears on both rosters, and each school's reports are scoped so
neither sees work done before the student joined it.

### What does not

**Content still resolves to exactly one school.** Precisely:

- The **local** student JWT carries `school_id` (the Auth0-exchange one does
  not), set at login from `students.school_id` — a single column naming their
  *first* school.
- `resolve_curriculum_id()` accepts that `school_id` and uses it for the RLS
  session variable and the cache key, but its first resolution step joins
  `students.school_id` regardless of what is passed.

So a student enrolled at a school **and** a tutor sees the school's content.
**The tutor half of your example does not work end to end yet** — the tutor can
enrol them and report on them, but cannot deliver them different material.

### The decision

**How does a dual-enrolled student choose which school's content they are
working in?**

| Option | Cost | Consequence |
|---|---|---|
| **A. Explicit switcher** — the student picks a school; the choice enters the session/JWT and drives resolution | Medium: UI, a claim that can change without re-login, cache keys already per-school | Clearest mental model, and the only one that lets a tutor deliver distinct material. Every student sees a switcher, including the ~all who only have one school — needs to hide itself in that case. |
| **B. Merge the content** — show units from every enrolment in one tree | Medium–large | No switching for the student. But two curricula for the same grade collide, progress attribution gets murky, and the FERPA boundary we just drew (a school sees work from its own enrolment onward) gets harder to hold. |
| **C. Primary school only** — document `students.school_id` as "primary", accept that additional enrolments are for *reporting*, not delivery | Zero | Honest and shippable today. A tutor can track a student but not teach them. Makes the current behaviour deliberate rather than accidental. |

### Recommendation

**C now, A when a tutor actually needs to deliver content.** C costs nothing and
makes today's behaviour intentional; A is the real answer but wants a concrete
tutor use-case to design against, rather than being guessed at.

If you pick **A**, the sub-question is whether switching re-issues the JWT or
adds a header/param — the caches (`cur:{student}`, `ent:{student}`) are already
school-scoped, so either works.

---

## 4 — Should a teacher see school-wide aggregates at all? *(new, from #576)*

**Status:** created by yesterday's decision. Not filed.

### What changed

#628 scoped six aggregate report endpoints to a teacher's assigned grades:
`overview`, `unit/{id}`, `curriculum-health`, `feedback`, `trends`, `at-risk`.

That closed a real leak — `at-risk` was **naming** struggling students from
grades a teacher was never assigned to.

### The question it raises

Scoping `overview` changed what the number *means*. A Grade-8 teacher's "pass
rate" is now **their cohort's**, not the school's. That is almost certainly the
right reading for a teacher — but it means **nobody below `school_admin` can see
a school-wide figure any more**.

| Option | Cost | Consequence |
|---|---|---|
| **A. Leave it** | Zero | Teachers see their own cohort. `school_admin` still sees the school. Simple and defensible. |
| **B. Add a separate school-wide endpoint** for teachers | Small | Teachers can see how their cohort compares to the school. Non-identifying aggregates only — no student names, no per-unit drill-down that reconstructs them. |
| **C. Show both** on the overview — "your grades" and "school" side by side | Small–medium | Most informative; the most UI work; and each extra figure needs checking that it cannot be de-anonymised in a small school (a grade with one student makes an "aggregate" personal). |

### Recommendation

**A for now.** It is the safe reading and it is already shipped. Revisit if
teachers ask for comparison — and if they do, prefer **B**, because a separate
endpoint makes "this figure is non-identifying" an explicit property of that
endpoint rather than a subtlety inside a report that also serves names.

---

## 5 — Should "Recent Activity" include lessons read? (#579's second half)

**Status:** #579 is closed; this half was deliberately left out of #627 and is
not separately filed.

### What is true today

The student dashboard's **Recent Activity** renders `history.sessions` — the
`GET /progress/student` feed, which contains **quiz sessions only**.

#627 removed the phantom rows (opening a quiz page no longer counts), so the
section is now accurate about what it shows. But a student who spent the evening
**reading lessons** still sees nothing under a heading that promises recent
activity. Lesson views live in `lesson_views` and are already queried elsewhere.

### The decision

| Option | Cost | Consequence |
|---|---|---|
| **A. Fold lesson views into the feed** | Small–medium: union the two sources, add a type discriminator, update the renderer | The section means what it says. Also makes the feed useful for a student who is reading ahead rather than testing. |
| **B. Rename the section** to "Recent Quizzes" | Trivial | Honest immediately, and arguably the better *first* move — the heading stops overclaiming while A is scheduled. |
| **C. Leave it** | Zero | A student who has done real work sees an empty state telling them to get started. |

### Recommendation

**B now, A soon.** B removes the false promise in one line; A delivers what the
student actually wants. C is the only wrong answer — Venki already reported this
section as not matching what he expected.

---

## 6 — Is a *classroom* eventually the entitlement unit? (#576's deferred half)

**Status:** #576 is closed on the grade decision. This is the "later" you chose.

The model in the database says a teacher is entitled to a **whole grade**. A real
secondary teacher teaches **one subject to particular classes** — a Grade-10
maths teacher has no business reading Grade-10 English results for students they
never teach. `classrooms` and `classroom_students` (migration 0038) already
express that finer relationship; the reports layer ignores them.

**Nothing is required now.** The trigger to revisit is *classrooms actually being
populated* — enforcing an empty model would lock teachers out of their own
reports, which is why grade was the right call today.

Worth deciding **when** it gets revisited rather than leaving it to drift: a
reasonable trigger is "the first school that creates classrooms and assigns
students to them".

---

## Smaller items

### 6a — Restore requests have no SLA and no notification (#589 follow-up)

A school admin who states a preferred time gets **no signal** that a human has
or hasn't picked it up. The request sits at `submitted` indefinitely, which is
correct per the design (#595 relabelled the field to "Preferred time" precisely
because nothing executes automatically) — but "correct" and "reassuring" are
different things.

Live demo: **both** restore requests are still `submitted`, one from 17 Aug.

Options: notify the school when a super-admin acknowledges; or show an expected
response window on the form. Small either way. Not filed.

### 6b — #630: a test that means different things on different machines

`web/tests/unit/restore-schedule.test.ts` → "accepts a value exactly at the
horizon boundary" is **timezone-dependent**: its helper strips the `Z`, so the
value parses as local time while the boundary is computed in UTC. It passes in
CI (UTC), passes for the wrong reason east of UTC, and fails west of it.

It is the one test asserting the client mirror agrees with the server bound at
the boundary — the case most likely to drift — so it is not merely noise. Filed
as #630 with a suggested fix; no decision needed, just scheduling. Worth
grepping `toISOString().slice` for the same assumption elsewhere.

---

## Related, and explicitly *not* blocking

- **#578** (email uniqueness is per-table; a teacher can shadow a student) — was
  going to block multi-school if we had scoped email per school. We did not, so
  **#578 is no longer on the critical path**. Still a real bug, still open.
- **#581** (no delete/deactivate; ADR-005 Decision 3 never implemented) —
  unaffected by yesterday's work and still open. `user_account_archive` and
  `deactivated_at` have zero occurrences in the codebase. This is what makes a
  mistyped address unrecoverable without an operator.
- **#620** (API wedged silently for 13 hours; root cause unknown) — autoheal
  bounds recovery to ~90s. If autoheal starts restarting the API repeatedly,
  that is the signal the wedge is recurring, and its logs become the diagnostic.
