# ADR-008 — Institutional Delivery Calibration: Syllabus Fidelity, Local Tuning, Year Over Year

**Date:** 2026-08-31
**Status:** Proposed
**Branch at decision:** `main`

---

## Context

### The product goal

An institution does not choose its syllabus. A board, ministry or examination
authority sets it, and the school is accountable for covering it. What a school
*does* control is **delivery** — emphasis, examples, sequencing, how a topic is
practised and assessed — and delivery is where schools differ from one another and
where a school gets better or worse over time.

Today that improvement is tacit. It lives in the heads of teachers who have taught
the material before, and it leaves when they do.

**The goal this ADR serves: a school can measurably improve how it delivers a fixed
syllabus, year over year, without ever drifting out of compliance with it — and can
show its governing body that it has not.**

That is the institutional articulation of what CLAUDE.md already calls the scoping
layer. It is not a new capability so much as a purpose for capabilities we have
mostly built and never pointed at anything.

> **A word to avoid.** Do not describe this externally as *"fine-tuning"*. To a
> technical reader — including a district's IT evaluator — that means fine-tuning a
> model, which is not what happens here. We re-scope generation against observed
> outcomes; no model weights change. Say *calibrate*, or *tune delivery*. The
> distinction matters because the wrong word is a false technical claim that
> survives into decks.

### The architecture already draws this line

The split between "the syllabus, which is fixed" and "the delivery, which is ours"
is already enforced in the schema, from two directions:

| Mechanism | Effect |
|---|---|
| Epic 10 L-1 (migration 0046) | RESTRICTIVE RLS refuses INSERT/UPDATE/DELETE on `curricula` rows with `owner_type='platform'` from any non-bypass session. **A school cannot edit the platform curriculum.** |
| Epic 12 (migrations 0050–0051) | Fork-on-import (`curricula.source_curriculum_id`), per-school overrides in `unit_content_overrides`, active pointer in `unit_content_active_versions`, governance workflow `draft → pending_review → approved` |

`unit_content_overrides.content_type` already permits `lesson`, `tutorial`,
`quiz_set_1`, `quiz_set_2`, `quiz_set_3`, `experiment`, all per-school RLS-scoped.

So the rails for local calibration exist and are already governed. What is missing
is not the ability to vary delivery — it is **any evidence about whether a
variation was an improvement.**

### The immediate trigger

From QA (31 Aug 2026): *"instead of having predefined sets can't we keep some 50
questions in the table and randomise?"* Randomisation is a reasonable tactic, and
this ADR adopts it — but as a consequence of the goal above, not as the point.

### What exists today

Measured on the demo, Grade 10 (`default-2026-g10`):

| | |
|---|---|
| Quiz sets per unit | 3 |
| Questions per set | 8 (uniform across all 57 files inspected) |
| **Total questions per unit** | **24** |
| Rotation | Round-robin per student per unit (Redis `quiz_set:{student_id}:{unit_id}`) |

Round-robin over three sets means **attempt 4 is set 1 again, question for
question**. The anti-cheat work in #684 was patching around a bank small enough to
memorise.

### The flaw that blocks all of it

`question_id` is **positional and set-relative** (`q1…qN` within a set). `q1` of set
2 is a different question from `q1` of set 1, in every unit. This is pitfall #35,
where it already forces the graded set to be pinned per session
(`progress_sessions.quiz_set`, migration 0061).

The consequence for this ADR is larger than grading. `progress_answers` already
records per answer:

```
question_id, student_answer, correct_answer, correct, ms_taken, recorded_at
```

— including **time-on-question**, a good difficulty proxy — and there are already
494 such rows on the demo across 151 sessions.

**None of it can be aggregated.** Grouping by `question_id` groups questions that
merely share a position. We are collecting the evidence a school would calibrate
against, and it is unreadable. Every other decision here is blocked on that one
identifier.

### The other missing grain

`feedback` is keyed by `unit_id` and `content_type`. A student can say *"this lesson
was not helpful"*. Neither a student nor a teacher can say **"question 4 is
ambiguous"** or **"question 4 is wrong"** — the single highest-value human signal
about an item, and the one a teacher is best placed to give.

### Generation does not read outcomes

`pipeline/prompts.py` scopes generation by the six dimensions CLAUDE.md identifies
as the product IP. None of them is *what happened last time this was taught*.
Generation is open-loop, so a second year's content is no better than the first
year's except by chance.

### Relationship to ADR-007

[ADR-007](ADR_007_academic_calendar.md) made the **unit-level** version of this
argument and named its confounder: a unit with a poor pass rate may be too hard, or
may simply have been taught the week before exams. Without calendar position,
content difficulty cannot be separated from cohort circumstance.

That confounder applies identically per question. **This ADR depends on ADR-007's
calendar normalisation for its signal to be trustworthy**, and it inherits ADR-007's
academic year as the natural period of the calibration cycle. The two are the same
mechanism at two grains: ADR-007 measures the unit, ADR-008 measures the item.

---

## Decision

### Decision 1 — The unit of improvement is a school's delivery of a fixed syllabus

The platform curriculum represents the syllabus: the coverage a governing body
requires. It is immutable to schools, and stays so.

A school's fork represents its **delivery** of that syllabus. Calibration acts on
the fork — emphasis, examples, question mix, sequencing — and never on the
platform curriculum.

This is a restatement of what migrations 0046 and 0050–0051 already enforce. It is
recorded as a decision because everything below must respect it, and because it is
the sentence the product is sold on.

### Decision 2 — There are two loops, and they are gated separately

| | **Local loop** | **Platform loop** |
|---|---|---|
| Scope | One school's own cohorts | Aggregated across schools |
| Improves | That school's fork and overrides | The OOB platform curriculum |
| Data basis | The school's own students; the school is the controller | **Crosses tenant boundaries** |
| Status here | **Approved** | **Deferred — needs its own decision** |

The local loop is the product goal and is legally clean: a school analysing its own
students' results to teach them better is the ordinary business of a school.

The platform loop — using what many schools observe to improve the curriculum
everyone receives — is where value compounds across customers, and is also where
the tenancy line runs. It requires aggregation, anonymisation, and an explicit
contractual basis with schools, none of which exist today.

**These are separated deliberately.** Fusing them would let a cross-tenant data
decision arrive disguised as a quiz feature. The platform loop is out of scope for
this ADR and must not be implemented as a side effect of it.

### Decision 3 — Syllabus coverage is an enforced invariant, not an assumption

If a school may vary delivery, something must verify it still covers what the
syllabus requires. The platform curriculum is the coverage contract; a fork may
differ in *how* and must not differ in *whether*.

Coverage is checked at the existing Epic 12 review gate (`pending_review →
approved`), and a school-facing view must be able to answer, for a governing body:
*which required elements does our delivery cover, and where does it differ?*

This is what makes the pitch defensible rather than merely attractive. Without it,
"local calibration" is indistinguishable from drift.

### Decision 4 — Every question has a stable, content-addressed identity

A question id is derived from the question's own stem — `curriculum_id | unit_id |
lang | stem`, hashed — so it is identical wherever it is computed and needs nothing
stored to mint. It does not change when sets are reshuffled or a pool is extended.
Positional `q1…qN` ids are retired as identity; they may remain as a display ordinal.

> **Corrected 2026-08-31, during Phase 1.** This decision originally read "minted
> **once, at generation**" and "does not change when … a question is **revised into
> a new version**". Both were wrong, and implementing them would have been worse
> than leaving the defect in place.
>
> *Minted* ids cannot reach the ~12,500 questions already on disk without
> regenerating them — paying the generation cost twice for content that is fine.
> Content-addressing lets existing content be backfilled in place, which is what
> makes Phase 1 cheap enough to do before Phase 3.
>
> *Revision-stability* is the more consequential error. A reworded question is
> psychometrically a **different item**: the difficulty and discrimination measured
> for the old wording do not describe the new one. Carrying statistics across an
> edit would quietly corrupt the very analysis Decision 8 rests on, and the
> corruption would be invisible — a plausible number computed over two different
> questions. Standard practice re-calibrates a modified item; a changed hash is
> that re-calibration expressed in the identifier.
>
> Continuity across a revision belongs to the Phase 3 registry, which can record
> "v2 supersedes v1" explicitly. An identifier that claims two different texts are
> one thing cannot express that without lying about one of them.

`progress_answers.question_id` and every downstream analytic key on this id.

**This is the load-bearing mechanism.** Decisions 5–9 are not implementable without
it, and it is the cheapest of them.

### Decision 5 — Question bodies stay in the content store; lifecycle and statistics live in the database

Bodies remain generated content in the content store (a per-unit pool file): they
are identical for every student, CDN-cacheable, and store-resident by the existing
layering rule.

A new **question registry** table holds, per stable id: unit, curriculum, language,
version, lifecycle state (`active` / `flagged` / `retired` / `superseded`), owning
scope (platform or school fork), and accumulated statistics. That is metadata about
content, not content.

The registry is what makes a question an object with a history rather than a line
in a file — and it is what lets a school retire an item locally without touching
the platform original.

### Decision 6 — Feedback gains a question grain

`feedback` gains an optional question reference, and the student and teacher
surfaces gain a per-question route ("this question was confusing" / "this question
is wrong").

A teacher flag is a **stronger signal than any statistic**: it is the only one that
distinguishes *hard* from *incorrect*. It may move a question to `flagged`
directly, within that school's scope.

### Decision 7 — Quizzes are drawn server-side from a pool, stratified, and pinned to the session

The served quiz becomes a **draw** from the unit's pool of active questions,
stratified by the existing `difficulty` field so two students' scores remain
comparable.

The session persists **the drawn question ids**, replacing the pinned set number
from migration 0061. This is simpler than what it replaces: pitfall #35 exists
because a set *number* is an indirection resolved twice — at serve time and at
answer time — and can resolve differently. A recorded list of ids cannot.

The draw is server-side, never delegated to the client, for the same reason grading
is not.

### Decision 8 — The quality signal is item analysis on cohorts, and discrimination is the one that matters

Two standard statistics per question:

- **Difficulty (p-value)** — proportion answering correctly.
- **Discrimination (point-biserial)** — do students who score well overall get this
  question right more often than those who do not?

Discrimination is the load-bearing one. A question that strong students miss more
often than weak students is **broken, not hard** — miskeyed, ambiguous, or testing
something other than it claims. Pass rates never reveal that; this statistic does.

It also guards Decision 1 against its own failure mode: **a school cannot improve
discrimination by making its questions easier.** Difficulty alone could be gamed
that way; discrimination cannot.

**Computed over cohorts, never retained as a per-student profile.** Data
minimisation and the prohibition on behavioural fingerprinting of minors are
project rules, and these are FERPA records. The loop consumes aggregates. This
bounds the design rather than weakening it — item analysis is a property of the
*question*, not of any student.

A question needs a meaningful number of responses before its statistics mean
anything; the threshold should be set from our own data rather than borrowed. This
sets the cadence: **per academic year**, per ADR-007, not live.

### Decision 9 — Observed performance becomes a seventh scoping dimension

CLAUDE.md documents the scoping layer as six dimensions and identifies it as the
product IP. This adds a seventh:

| Scope dimension | What it enforces |
|---|---|
| *(existing six)* | … |
| **Observed performance** | What measurably worked when this school last taught this |

That is the substance of the ADR. CLAUDE.md argues StudyBuddy is a search engine
rather than a library — curated by query, not by selection — and that this is why
"always current" is defensible. A generation loop that reads its own outcomes
extends the claim from *recency* to *quality*: the scoping layer stops being merely
parameterised and becomes **self-correcting, per institution**.

### Decision 10 — Identity and feedback grain ship before any pool generation

Generating larger pools before Decision 4 lands produces a bank that still cannot
be learned from, and forces a second regeneration to add ids — paying the
generation cost twice. Sequencing is fixed in Migration / rollout below.

---

## Consequences

### Positive

- A school gets an evidence-backed answer to *"is our delivery of this syllabus
  improving?"*, which is a governing-body question, not a feature request.
- The per-question data already being collected becomes readable — 494 rows on the
  demo today, growing on its own.
- Repetition drops sharply. Drawing 8 from a pool of 50 gives an expected overlap of
  about **1.3 questions** between two attempts, against **8 of 8** on attempt 4
  today.
- Broken questions become findable by statistic rather than by complaint, and a
  teacher gains a direct route to flag one.
- Pitfall #35's pinning hazard is replaced by something structurally safer: an
  explicit list of ids instead of a set number resolved twice.
- Coverage reporting (Decision 3) is independently saleable to any institution
  answerable to a board or ministry.

### Negative

- Quiz generation cost rises roughly with pool size (24 → 50 questions per unit is
  about **2×** the quiz tokens), plus a one-time regeneration.
- **Teaching to a self-set metric is a real risk.** A school optimising its own pass
  rates could drift toward easier assessment and call it improvement. Decisions 3
  and 8 are the guards, and they must ship with the loop, not after it.
- Pass rates become slightly noisier: students answer different subsets. Stratified
  draw contains this but does not remove it, and comparisons spanning the change are
  not like-for-like.
- Another table and another lifecycle to administer, with a review surface implied
  for `flagged` questions.
- The loop is slow by construction. Its first useful output is a year away — a
  property of the statistics, not of the implementation.
- Calibration is per-school, so two schools' forks of the same syllabus diverge over
  time. That is the intent, but it makes cross-school comparison harder, which is a
  cost to bear when Epic 5 (district admin) arrives.

### Neutral

- Caching is unaffected and arguably simplified — one pool file per unit rather than
  three set files, identical for every student, still CDN-cacheable. The draw is
  cheap and server-side.
- Offline behaviour is unchanged: grading is already server-side, so a quiz already
  requires connectivity.
- The `difficulty` field already present on every generated question makes
  stratification available at no extra generation cost.
- The institutional framing is a third register alongside CLAUDE.md's consumer
  ("information bridge") and engineering ("scoped retrieval") framings. It does not
  replace either; it is the school-admin articulation of the same mechanism, and the
  audience translation matrix should gain a row for it.

---

## Alternatives considered

- **Keep three static sets** — rejected. Round-robin guarantees exact repetition on
  attempt 4, and positional ids make the collected per-question data permanently
  unreadable. This is the status quo the QA question reacted to.
- **One global loop that improves the platform curriculum directly** — rejected as
  the primary design. It crosses tenant boundaries without a contractual basis, and
  schools cannot edit platform curricula anyway (migration 0046). It is not
  abandoned; it is Decision 2's deferred platform loop, requiring its own privacy
  decision.
- **Randomise on the client** — rejected. The server must know what it served in
  order to grade it, and anything the client chooses can be re-chosen.
- **Move question bodies into Postgres** — rejected. Breaks the content-store
  layering, loses CDN caching of a payload identical for every student, and solves
  nothing the registry does not. The lifecycle belongs in the database; the prose
  does not.
- **Uniform random draw** — rejected. One student draws eight easy questions and
  another eight hard, making scores incomparable and corrupting the very signal this
  ADR sharpens. Stratify by `difficulty`.
- **Per-student adaptive testing (IRT / CAT)** — rejected for now. The natural
  extension of item analysis, but it requires a persistent per-learner ability
  estimate — exactly the profiling that data minimisation and the rules on minors
  forbid. It also needs far more data than we will have for years. Revisit only by
  deliberate privacy decision, never by drift.
- **Human-authored question banks** — rejected as the primary path. That is the
  linear-in-specialists cost curve described in
  [`COMPETITIVE_kolibri.md`](COMPETITIVE_kolibri.md), which is the model StudyBuddy
  exists to avoid. Teacher input enters as flags and corrections on generated items,
  which is high-leverage, rather than as authorship.

---

## Migration / rollout

Sequenced so the cheap, data-accruing steps come first and the expensive,
hard-to-reverse generation spend comes last.

**Phase 1 — Question identity (blocking, cheap).**
Mint stable ids at generation; carry them through the served quiz, the answer key,
and `progress_answers`. Migration plus a pipeline change. Existing rows keep
positional ids and are **not back-fillable** — their question identity is not
recoverable. Pre-migration answer data is unusable for item analysis and must be
excluded explicitly rather than silently mixed with post-migration data.

**Phase 2 — Feedback grain (cheap, starts the clock).**
Question reference on `feedback`; student and teacher surfaces. Ships independently
of Phases 3–5 and begins accumulating the human signal immediately — the part that
cannot be rushed later.

**Phase 3 — Registry and pool draw.**
Question registry table with lifecycle and owning scope. Serving switches to a
stratified server-side draw; the session records drawn ids; migration 0061's
`quiz_set` is superseded.

Note a constraint change: `unit_content_overrides.content_type` currently enumerates
`quiz_set_1/2/3`, so the pool model needs a new permitted value (e.g. `quiz_pool`)
— a CHECK alteration, not just new rows.

> **Split into 3a and 3b, 2026-09-02.** See "Phase 3, reshaped" below. The
> registry and the draw can ship over the questions that ALREADY exist, with no
> generation spend; enlarging the pool is a separate, costed step. The original
> note here said Grade 8 on the demo was entirely `dev-placeholder` and therefore
> not a candidate — that was true when written and is **no longer true**: Grade 8
> was given real content on 2026-09-01.

**Phase 4 — Coverage fidelity (Decision 3).**
Coverage contract derived from the platform curriculum; check at the Epic 12 review
gate; school-facing coverage view. Independent of Phase 5 and separately saleable.

**Phase 5 — Item analysis and the local loop.**
Difficulty and discrimination per question, normalised by calendar position per
ADR-007. Flagged-question review surface. Aggregate feeds generation as the seventh
scoping dimension, scoped to the school's own fork.

**Not in scope:** the platform loop (Decision 2). It requires its own ADR covering
aggregation, anonymisation, and the contractual basis, and must not be built as a
side effect of Phase 5.

---

## Phase 3, reshaped (2026-09-02)

Two things changed after Phase 2 shipped: the tester answered the questions this
ADR had left open, and the existing corpus was measured rather than assumed.

### What the corpus actually contains

Measured across the content store, counting only real (non-placeholder) content:

| | Platform (`default-*`) | Authoring Studio (`authored-*`) |
|---|---|---|
| Units with quiz content | 222 | 276 |
| Questions | 5,298 | 6,616 |
| Duplicate stems **inside one quiz** | **0** | **5,439 (82.2%)** |

Per platform unit, counting DISTINCT questions (the number a pool can actually
draw from): **median 24, min 17, max 72**, across 212 units and 5,269 questions.
Every one of the 212 has at least 17 — twice a quiz — so no unit is too thin to
draw from.

Difficulty is populated on every question. Raw counts look badly skewed
(easy 66% / medium 24% / hard 11%), but that skew is an artefact of duplication:
the repeated questions are overwhelmingly easy. **After deduplication, platform
content is medium 45% / easy 36% / hard 19%.** Both numbers are given because the
first is what a naive importer would have built a pool from.

Every question is `multiple_choice` — there is not a single multi-select question
in the corpus.

Two consequences, and the second is the reason this section exists at all:

- **Students are not affected by the duplication.** It is confined to
  `authored-*` directories, and there are currently **no `authored-*` rows in
  `curricula`** — that content is orphaned on disk, unreachable by any serving
  path. It is a generation-quality signal about the Authoring Studio, not a live
  defect, and it does not block this phase.
- **It does constrain what a pool can be drawn from.** Any pool built over
  Authoring Studio output would inherit an 82% duplication rate. Pool
  construction must therefore dedupe on stable question identity (Decision 4),
  not merely concatenate the sets.

### The tester's answers, and what they change

- **Pool size: 150-200, not 50.** His reasoning is cost: "generating the question
  bank also will cost you and this can built over a period of time." That is a
  build-up target, not a precondition.
- **Repeats: tolerable at that size.** "ideally no but keeping the question bank
  size and no of questions per quiz probability of getting repeated question is
  less."
- **An interim he proposed himself:** pool the questions that already exist and
  draw randomly, "in case if it is going to take time to build the question
  bank."

That interim is worth taking, and it is stronger than it looks. Today a student
sees one of **3 fixed sets of 8**. Drawing 8 from a deduplicated pool of ~24
gives on the order of 10^5 distinct quizzes per unit instead of 3 — which is the
whole of what "reduces the predictability" asks for, at **zero generation cost**.

So Phase 3 splits:

**Phase 3a — registry and draw over existing questions.** Registry table,
backfill from the content store keyed by stable question id, server-side
stratified draw, session records drawn ids. No generation. Reversible: the
existing sets stay on disk untouched, so the draw can be switched off.

**Phase 3b — enlarge the pool.** Generation to the 150-200 target, per unit,
starting where the signal says it is needed rather than uniformly. Costed
separately and explicitly, because it is the expensive half.

### Two new asks, both deferred with reasons

**Multi-select questions.** Not declined — sequenced. It is not a content change
alone: `correct_option` is a single value end to end, so the answer key, the
server-side grader (pitfall #35), the session tally, the player, and the schema
all change together. It also invalidates comparability with every existing
question for item analysis, since partial credit is a different measurement.
Worth its own slice after 3a, not folded into it.

**Easy / Medium / Hard banks with progression gating.** The `difficulty` field
already exists and Decision 7 already stratifies the draw by it, so the data model
needs nothing new. What is missing is content depth: at 19% hard on a median of
24, a typical unit holds **four or five hard questions**. A gate that requires
finishing an Easy bank before unlocking Medium would, today, unlock a "Hard bank"
of four — which reads as broken rather than progressive, and a student who
retried would see the same four.

This becomes viable **after 3b**, and 3b's generation targets should therefore be
stated **per difficulty band** rather than as a single total per unit. Worth
noting the current mix is not the one this feature wants: it is medium-heavy,
whereas a progression ladder needs a broad easy base.

### Sequencing

3a is safe and cheap and should ship first. 3b is the costed generation step, and
its per-band targets are what make the difficulty banks possible. Multi-select
follows 3a as its own slice. Nothing here changes Decisions 1-10; it schedules
them against measured content rather than assumed content.

---

Phases 1 and 2 are worth doing even if the rest is deferred indefinitely: they cost
little, they make data already being collected meaningful, and every month they are
delayed is another month of unreadable answer data.

**Status flips to Accepted when Phase 1 lands**, not before.
