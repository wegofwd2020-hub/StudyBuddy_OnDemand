# StudyBuddy OnDemand — Tagline Options

> Brainstorming doc to pick a canonical one-liner for the rebrand from
> "STEM tutoring platform" → "AI-powered education enhancement tool."
>
> Once a pick is made, the chosen tagline + sub-headline roll out to:
> `README.md`, `CLAUDE.md`, `web/app/layout.tsx` metadata, `web/i18n/{en,fr,es}.json`,
> `backend/src/help/service.py` system prompt, and `backend/src/email/service.py`.
>
> Status: **✅ DECIDED 2026-04-21 → REVISED 2026-05-06** — original pick (C+1) was
> too long for hero presence; shortened during demo prep. Execution tracked in
> [EPIC_13_branding_refresh.md](epics/EPIC_13_branding_refresh.md).
>
> **Canonical tagline (live as of 2026-05-06):** *"Lessons, always current."*
> **Canonical sub-headline:** *"AI-powered lessons, quizzes, and tutorials — your bridge from classroom to a world that won't sit still."*
>
> **Previous tagline (2026-04-21 → 2026-05-05):** *"Your bridge from lessons to a world that's always current."* — preserved here for audit. The bridge metaphor moved into the sub-headline; the load-bearing word "current" is retained in the new H1. See `studybuddy-docs/docs/promos/TaglineOptions.md` for the full candidate library.

---

## Engineering mental model — "scoped retrieval over the world of knowledge"

> "StudyBuddy is a sophisticated search engine where the contents are managed by providing
> reference to topic, grade, language every time a query goes out into the world." — founder, 2026-04-21

This is the **engineering / internal mental model** that sits behind the consumer bridge
metaphor. Both framings are correct; they serve different audiences.

A plain LLM call is an *unscoped* query against the world of knowledge. StudyBuddy's pipeline
is a **scoped query**, parametrised by six dimensions that together form the product's IP:

| Scope dimension | What it enforces |
|---|---|
| Topic / subject / unit | Curriculum alignment — matches what the teacher is teaching |
| Grade | Reading level, conceptual depth, age-appropriateness |
| Language | en / fr / es / vernacular |
| Curriculum context | What the student has already covered — so we don't re-explain prerequisites |
| Format | Lesson / quiz / tutorial / experiment — different prompts, different validators |
| Real-world framing | The bridge — connect the topic to something current the student recognises |

Structural consequence — **this is why "current" is defensible, not cosmetic:**

- A *library* is curated by **selection** — pick content once, shelve it, serve it. Static.
- A *search engine* is curated by **query** — every query re-runs against a live index. Dynamic.
- StudyBuddy is the second. The retrieval re-runs every time the query runs, so the output
  can reflect the current state of the world, not a frozen 2024 library.

**Audience translation matrix:**

| Audience | Does "sophisticated search engine" land? |
|---|---|
| Engineering / internal docs / CLAUDE.md | Yes — the cleanest mental model |
| Pitch deck / VCs / B2B schools | Partial — useful for 30 seconds, then move to pedagogy |
| Parents / students / teachers | No — pulls them to Google associations, away from "lesson" |

**How to use this model:**
- CLAUDE.md + ARCHITECTURE.md should adopt it explicitly as the architectural frame.
- Pitch decks and technical marketing can lead with it.
- Consumer copy (landing, emails, help widget) keeps the **bridge** metaphor — the bridge is
  the *visible effect* of scoped retrieval, which is exactly what parents and students want.

---

## Founder direction — the "information bridge" concept

> "I really want people to think of StudyBuddy as the **information bridge** between
> their lessons and the real world." — founder, 2026-04-21
>
> Raw tagline proposal: *"We bring current world explanation to your learnings."*

This direction is stronger than the original Angles A–E because it gives the product a
**concrete mental model** — a bridge — rather than a feature list or an outcome claim.
Two insights worth preserving verbatim in the final copy:

| Insight | Why it sticks |
|---|---|
| **"Bridge"** as the product metaphor | Not tutor, not helper, not library — a *conduit*. Positions StudyBuddy as the connective tissue between two things the student already has (the lesson) and already cares about (the world). Defensible; visual; reusable in product copy, diagrams, and pitch decks. |
| **"Current world"** (not "real world") | Static content libraries can claim "real world." Only a live AI agent can claim **current** — today's news, fresh science, this week's events applied to classic lessons. This is the actual moat. |

The raw phrasing has three issues that block direct use:
1. **"your learnings"** — corporate jargon; students say "lessons."
2. **"current world explanation"** — awkward noun phrase.
3. **"We bring …"** — passive corporate voice; no rhythm.

Angle F (below) preserves the bridge + current-world concept with cleaner wording.

---

## Positioning — what the new tagline must convey

| Must convey | Must NOT imply |
|---|---|
| Works across any academic subject (not just STEM) | STEM-only, science-only, maths-only |
| AI agent generates content (not just a static library) | Human tutor, live tutoring sessions |
| Enhances existing curriculum / lessons (additive to school) | Replaces the teacher or the classroom |
| Real-world context, relevance, application | Abstract, academic-only, textbook-only |
| Grades 5–12 / K-12 scope | Adult learners, university |
| The "Buddy" metaphor — companion, helper, alongside the student | Authority figure, examiner, assessor |

---

## Shortlist — top recommendations

These are the strongest candidates. Each is a **H1 tagline + sub-headline** pair so it can slot
into landing hero, email welcome line, and help-assistant self-description in one go.

**B+1 and B+7 (Angle F, below) are the current front-runners** based on the founder's "information
bridge" direction. S1–S4 are retained for comparison but rank lower.

| # | Tagline (H1) | Sub-headline | Best for |
|---|---|---|---|
| **C+1** ⭐ | **Your bridge from lessons to a world that's always current.** | An AI study buddy that connects your lessons to the world — and keeps learning alongside you. | Landing hero — explicit bridge, future-proof against the agent roadmap |
| **C+1b** | **Your bridge from lessons to a world that's always current.** | Every lesson matched to your grade, your subject, your language — and always connected to the world now. | Landing hero — sub hints at the scoped-retrieval model without jargon (14 words, longer) |
| **C+2** | **Keeping your lessons current with the world.** | Your AI study buddy for every subject, Grades 5–12. | Metadata / SEO / help-widget self-description — tight, active voice |
| **C+3** | **Your bridge between lessons and a world that keeps changing.** | An AI study buddy that grows with you as your learning grows. | Fallback if "always current" reads redundant |
| B+1 | Your bridge from lessons to today's world. | — | **Superseded by C+1** — "today's" implies a snapshot; fails the agent-roadmap test. |
| S1 | Learn more from every lesson. | AI-enhanced academic content for Grades 5–12, connected to the real world. | Kept for comparison — outcome-first, lacks the bridge metaphor |
| S2 | Where academic lessons meet the real world. | Your AI study buddy for any subject, Grades 5–12. | Kept for comparison — mechanism-first but "real" instead of "current" |
| S3 | Your AI study buddy — for every lesson, every subject. | Instant lessons, quizzes, and real-world context, ready when you are. | Kept for comparison — lean on brand name, no bridge concept |
| S4 | Academic lessons, enhanced. | An AI agent that adds real-world context to every subject, Grades 5–12. | Kept for comparison — shortest, but "enhanced" is abstract |

---

## Long list — all options, grouped by angle

### Angle A — Buddy / companion metaphor (leverages brand name)

| # | Tagline | Note |
|---|---|---|
| A1 | Your AI study buddy — for every lesson, every subject. | See S3. |
| A2 | The study buddy that turns textbook lessons into the real world. | Long; strong concept. |
| A3 | Learning is better with a buddy. | Warm; but weak on mechanism. |
| A4 | A study buddy for every subject you'll ever have. | Inclusive; generic verb. |
| A5 | Never study alone. | Emotional; lacks "AI" / "academic" signal. |

### Angle B — Real-world connection (mechanism-first)

| # | Tagline | Note |
|---|---|---|
| B1 | Where academic lessons meet the real world. | See S2. |
| B2 | Every lesson, connected to the world outside the classroom. | Slightly long but precise. |
| B3 | Classroom content, real-world context — powered by AI. | Three-part; good for B2B school pitch. |
| B4 | Bringing real-world context to every academic lesson. | Plain, clear. |
| B5 | From the textbook to the real world. | Short; poetic; ambiguous without context. |

### Angle C — AI agent / enhancement (mechanism + product category)

| # | Tagline | Note |
|---|---|---|
| C1 | An AI agent that enhances every academic lesson. | Literal but self-explanatory. |
| C2 | Academic lessons, enhanced. | See S4. |
| C3 | AI-enhanced learning for any subject, any grade. | Good alt to current "AI-powered study material". |
| C4 | One AI agent. Every subject. Every grade. | Punchy; three-beat rhythm. |
| C5 | The AI agent behind every great lesson. | Implies ubiquity; slightly ambitious. |

### Angle D — Outcome-focused (what the student gets)

| # | Tagline | Note |
|---|---|---|
| D1 | Learn more from every lesson. | See S1. |
| D2 | Turn lessons into understanding. | Warm; verb-led. |
| D3 | Lessons that stick. For every student. | Two-sentence; strong for parents. |
| D4 | Deeper understanding — on demand. | Plays on the product name "OnDemand". |
| D5 | Helping students get more from every class. | Plain; works in translation. |

### Angle E — Inclusive / all-subjects (direct anti-STEM signal)

| # | Tagline | Note |
|---|---|---|
| E1 | Any subject. Any grade. One AI agent. | Mirrors C4. |
| E2 | From maths to history, we've got every subject covered. | Explicit but colloquial. |
| E3 | AI-powered learning for every subject, Grades 5–12. | Safe; literal; not memorable. |
| E4 | Every subject, every student, every day. | Three-beat; good for internal morale. |

### Angle F — Information bridge / "current world" (founder direction) ⭐

Preserves the founder's core insight: StudyBuddy is the **bridge** between classroom lessons
and the **current world** — where "current" means *continuously up-to-date as the student's
learning progresses and the AI agent extends it*, not a dated snapshot. These rank highest in
the shortlist because they give the product a concrete, defensible, future-proof mental model.

| # | Tagline | Note |
|---|---|---|
| **C+1** ⭐ | Your bridge from lessons to a world that's always current. | Explicit bridge; "always current" disambiguates from electrical sense and signals the agent roadmap. Current top pick. |
| **C+2** | Keeping your lessons current with the world. | "Current" as adjective-phrase reads as "up-to-date"; active verb "keeping" hints at the agent. Tightest (7 words). |
| **C+3** | Your bridge between lessons and a world that keeps changing. | Avoids the word "current" but encodes its meaning. Fallback if "always current" feels redundant. |
| B+1 | Your bridge from lessons to today's world. | Superseded by C+1 — "today's" implies a dated snapshot; breaks when the agent ships. |
| B+7 | From the textbook to today's world. | Superseded — same "today's" issue as B+1. |
| B+3 | Textbook lessons. Today's world. One study buddy. | Superseded — retain the three-beat structure idea for ad copy but re-phrase with "always current." |
| B+4 | Every lesson, explained by today's world. | Risk: "explained by" implies the world teaches, which is charming but odd. |
| B+5 | The bridge between your lessons and the world today. | Literal bridge; longest; "the world today" has the same snapshot issue. |
| B+8 | Connecting your lessons to the world that matters now. | Emotive; "the world that matters now" is slightly over-written. |

**"Current world" vs. "today's world" — why we went back to "current":**

Initial draft proposed swapping "current" → "today's" for readability. Founder overruled on
strategic grounds (2026-04-21), and the reasoning is load-bearing — preserve it:

> **"Today's"** anchors to a specific date (a snapshot). **"Current"** anchors to "whenever
> the student is using it" (an evergreen property). The tagline has to cover three product
> phases, not just today's library:
>
> | Phase | What "current" has to cover |
> |---|---|
> | Now | Pre-generated content per curriculum |
> | Soon | Teachers generating more content as a course progresses |
> | Roadmap | AI Agent where students query and learn more as they go |
>
> "Today's world" breaks the moment Phase 2/3 ships. "Current world" is the agent's promise.

The awkwardness of the founder's raw phrasing (*"current world explanation to your learnings"*)
was **syntax**, not the word "current" itself. In constructions like *"a world that's always
current"* or *"keeping your lessons current with the world,"* the word reads cleanly and
disambiguates from the electrical-current connotation.

Translation: FR *"toujours actuel"* / *"qui reste d'actualité"*, ES *"siempre actual"* /
*"que se mantiene al día"* — all translate cleanly.

**Why drop "we bring":** The founder's original "*We bring* current world explanation to your
learnings" uses corporate passive voice. Declarative taglines without a "we" read as
statements of fact — stronger, and they work as both marketing copy and help-assistant
self-descriptions without pronoun gymnastics.

---

## Rejected directions — and why

| Direction | Why not |
|---|---|
| "AI tutor for K-12" | Uses "tutor" which implies 1:1 live tutoring. Regulatory + expectations mismatch. |
| "Personalised learning for Gen Z" | Demographic-locked; dates badly. |
| "The Khan Academy of AI" | Positions vs. a competitor; weakens own brand. |
| "Homework, solved" | Implies answer-giving — works against pedagogy + can spook schools/parents. |
| "Your 24/7 tutor" | Same "tutor" problem, plus implies live service SLAs. |
| "Master every subject" | Over-promises; also not what the product actually does. |
| "Replace your textbook" | Antagonises schools. Product augments, does not replace. |

---

## Decision criteria — how to pick

Rank candidates against these (1 = weak, 5 = strong):

| Criterion | Weight | Why it matters |
|---|---|---|
| Translates cleanly to FR + ES | High | Three-locale launch; idioms that don't travel cost a rewrite per locale |
| Fits in 60 chars for meta description / og:title | High | Search + social preview truncation |
| Survives reading out loud | Medium | Audio help-widget response, video ad voiceover |
| Explicit about "academic / curriculum" scope | Medium | Parents + school admins need to know it's aligned with school work |
| Signals AI without being AI-slop | Medium | Differentiator, but "AI" in every sentence reads cheap |
| Leaves room for product to grow | Low | Avoid picking a tagline that blocks parent-portal or district-admin expansion |

---

## Open questions for the founder

1. **"Buddy" metaphor — lean in or play down?** The brand name invites it, but leaning in too hard (A3, A5) costs the AI-agent positioning. S3 tries to split the difference.
2. **Do we keep "Grades 5–12" in the tagline, or move it to the sub?** S1/S3/S4 move it to the sub; S2 keeps it. Moving it to the sub opens the tagline for future grade expansion without a rewrite.
3. **"Real world" vs. "real life" vs. "the world outside the classroom"?** All three are in play in the long list. "Real world" is shortest and most translatable; "real life" is warmer; "world outside the classroom" is most precise but bulky.
4. **How much does the help assistant's self-description need to match the landing tagline?** If the help LLM says *"I'm the AI study buddy for your lessons,"* that can differ from the marketing tagline as long as it reflects the same positioning. Worth a separate short prompt line.

---

## Next step

Pick one shortlist entry (B+1, B+7, B+3, or an S-variant) or nominate a synthesis, then file
`T-BR-5` to lock the copy and roll it through the 6 surfaces listed at the top.

Current recommendation: **C+1** — *"Your bridge from lessons to a world that's always current."*
with sub *"An AI study buddy that connects your lessons to the world — and keeps learning
alongside you."*

This preserves the founder's bridge metaphor and the founder's chosen word "current," while
fixing the syntactic awkwardness of the original raw phrasing. The "always" disambiguates
"current" from its electrical-current reading, and the sub-headline's *"keeps learning alongside
you"* quietly signals the forthcoming AI Agent roadmap without making a hard promise.
