# StudyBuddy — Canonical Overview (for promo work)

> **Purpose of this doc.** A single source-of-truth you can paste into the
> top of any Claude.ai conversation when drafting promo material —
> teacher emails, school admin one-pagers, LinkedIn posts, investor
> blurbs, demo invitations, landing page copy. Tight enough to fit in
> one prompt; specific enough that Claude doesn't have to guess.
>
> **How to use.** Open a Claude.ai Project (or a new conversation),
> paste this whole doc as the first message, then say what you want:
> "Draft a 150-word LinkedIn post for school administrators." Iterate
> from there. Update this doc — not your individual chats — when the
> product, audience, or moat shifts.
>
> **Last refreshed:** 2026-05-19 (post-demo-walkthrough launch).

---

## The one-line pitch

> **Lessons, always current.**

*Sub-headline:* AI-powered lessons, quizzes, and tutorials — your bridge from classroom to a world that won't sit still.

---

## What it is (in three sentences)

StudyBuddy is an AI-powered education platform that produces grade-aligned, curriculum-scoped lessons, quizzes, tutorials, and experiments **on demand** — re-generated against the live world every time, not pulled from a static library.

Teachers adopt curricula into their school's library, optionally override or approve any unit's content, and assign it to classrooms. Students get lessons that connect what they're learning today to what's happening in the world right now — in their language, at their reading level.

The product is an **information bridge** between two things every student already has: the lesson their teacher is teaching, and the world around them.

---

## The defensible moat — "current" is the load-bearing word

A typical content library is curated by **selection**: pick content once, shelve it, serve it. Static. Outdated within months.

StudyBuddy is curated by **query**. Every time a lesson is rendered, the pipeline re-runs a *scoped* query against the live world of knowledge — parametrised by six dimensions:

| Scope dimension | What it enforces |
|---|---|
| Topic / subject / unit | Curriculum alignment — matches what the teacher is teaching |
| Grade | Reading level, conceptual depth, age-appropriateness |
| Language | en / fr / es / vernacular |
| Curriculum context | What the student has already covered — no re-explaining prerequisites |
| Format | Lesson / quiz / tutorial / experiment — different prompts, different validators |
| Real-world framing | Connect the topic to something current the student recognises |

Structural consequence: the output can reflect the state of the world today, not a frozen 2024 library. **A static EdTech product cannot claim "current". A live AI product can.** That is the moat.

(Engineering mental model: "scoped retrieval over the world of knowledge." Useful in technical decks; **don't use with parents/teachers** — pulls them to Google associations.)

---

## Who it's for, in the order of who decides to use it

1. **Teachers (Grade 8 – Grade 12).** They want lessons that work with the curriculum they're already teaching. StudyBuddy lets them adopt a platform curriculum, optionally edit any unit, and assign to a class with a few clicks. They keep editorial control; AI does the heavy lifting.

2. **School administrators.** They want predictable, auditable content that aligns with their adopted curriculum. StudyBuddy's adoption + approval workflow (draft → pending review → approved → published) gives a traceable trail per unit per content type.

3. **Students.** They want lessons that make sense — in their language, at their grade level, connecting to something they actually care about. They never see the AI directly; they see clean lessons, quizzes, tutorials, and short experiments.

4. **District buyers / investors.** They want a defensible product. The "current" framing + scoped-retrieval architecture is the answer to "why won't OpenAI eat your lunch?"

---

## What's live right now (as of 2026-05-19)

- **Live demo:** `https://demo.usestudybuddy.com` — anyone can self-serve sign up at the homepage. Email + name. Verification link. 24-hour student account + 48-hour teacher account land in your inbox. Walkthrough validated end-to-end.
- **Curriculum coverage shipped on the demo:** Grade 8 STEM, Grade 10 STEM, Grade 11 STEM / Commerce / Science (fully populated), Grade 12 Commerce / Science. English (en) only at launch; french / spanish in the pipeline.
- **Per unit:** lesson + tutorial + 3 quiz sets + experiment, AI-generated and curated.
- **Visuals + walkthrough videos:** 44 tutorial MP4s + AI-generated SVGs embedded inline.
- **Auth tracks:** Auth0 SSO for schools, local-auth (email + password) for demo signups.
- **Pipeline:** Anthropic Claude + Voyage AI for content gen + retrieval; ~$215 one-time spend produced the current Grade 8 / 10 / 11 / 12 content set.

---

## The demo experience (the funnel)

1. Visitor lands on `https://demo.usestudybuddy.com`.
2. Watches two pre-recorded feature videos (BioStory + ChemStory) and four short tutorial-visual loops (Hydrocarbon series).
3. Clicks **Request a test run**. Submits name + email.
4. Receives verification email; clicks the link.
5. Receives credentials email — *both* a teacher login and a paired student login.
6. Signs in as the teacher → walks the populated Curriculum Catalog, Our Library, classroom view.
7. Signs out, signs in as the student → opens a Biology lesson, takes a quiz.
8. Total time from request to clickable demo: **about 90 seconds**.

The demo is shared — every visitor lands in the same seeded school (MilfordWaterford Local School) with their own personal classroom + student account. Stripe is intentionally blanked on the demo; payment flows are out of scope for the demo walkthrough.

---

## Differentiators (use these against the obvious comparisons)

- **vs. ChatGPT / generic LLMs.** Generic LLMs return whatever the prompt asks for. StudyBuddy returns *curriculum-aligned, grade-appropriate, language-localised* content because retrieval is scoped at the platform level — the teacher can't accidentally serve a Grade 11 lesson to a Grade 8 class.
- **vs. Khan Academy / static libraries.** Khan's content is excellent but frozen. StudyBuddy regenerates against the live world, so the example used to explain *Kinematics* this semester is different from the one used last semester — and both are tied to something the student recognises today.
- **vs. traditional textbooks.** Textbooks update every 5+ years. StudyBuddy updates on every render.
- **vs. AI-generated content with no curriculum context.** Lots of products generate lessons. Few enforce curriculum + grade + language + prerequisite-awareness in one query.

---

## Voice + tone (paste this into Claude.ai when you want it to write copy)

- **Confident, not salesy.** No "revolutionize," "unlock," "supercharge," "game-changer." Show, don't promise.
- **Teacher-first.** When in doubt, write for a thoughtful Grade 11 Biology teacher who has seen four EdTech products fail her in the last year. Respect her time. Don't claim AI replaces her — claim it gives her better source material.
- **Specific over abstract.** "Anya is studying Sets and Functions in Grade 11 Mathematics" beats "students engage with personalised content."
- **Concrete numbers when they exist.** "29 units across 4 subjects, every one reviewable in 60 seconds" beats "comprehensive coverage."
- **No hedging on "current."** Don't say "fresh-ish" or "up-to-date." Say *current*. It's the moat word.
- **British / American English.** Default American spelling unless writing for a specific market.

---

## What NOT to claim (yet)

- Don't claim Stripe-backed subscription tiers. The demo doesn't exercise payment.
- Don't claim mobile app. Web only at launch; an Expo/RN app is in backlog.
- Don't claim multi-language live. English only at launch; fr/es are in the pipeline.
- Don't claim district-scale deployments. The product is in early access; no district contracts shipped.
- Don't claim the "10 demo requests per requester" or "geo-locked by region" limits — those are in the EPIC spec but not enforced in the live signup flow yet.
- Don't claim curriculum override / approval workflows are exercised by teachers in production. They work in the demo but real adoption is pre-launch.

---

## Useful URLs + facts to cite

- **Live demo:** `https://demo.usestudybuddy.com`
- **Main / community site (founder):** `https://mambakkam.net`
- **Founder:** Sivakumar Mambakkam, Enterprise Architect
- **Tech stack (only if asked):** FastAPI + asyncpg + Postgres + Redis + Celery on the backend; Next.js + Tailwind on the frontend; Anthropic Claude + Voyage AI for content + retrieval; Hetzner Cloud + Cloudflare for hosting.
- **Pricing posture:** not yet announced. Stripe is wired in test mode; subscription endpoints exist but aren't promoted.

---

## A note about audience translation

Different audiences need different framings of the same product. When asking Claude.ai for promo material, **always specify the audience**:

| Audience | Lead with | Bury / drop |
|---|---|---|
| Teacher | "Lessons that work with the curriculum you're already teaching" | Architecture, AI moat, investor metrics |
| School admin | "Auditable adoption + approval workflows per unit" | Student-experience anecdotes |
| Parent | "Lessons in your child's language, at their grade level, connected to the world they recognise" | Editorial workflow, scoped retrieval |
| Student (or student-facing) | "Quizzes and lessons that don't feel like a textbook from 2018" | Anything sounding like marketing copy |
| Investor / VC | "Scoped retrieval is the moat; static libraries can't claim *current*" | Long curriculum lists |
| Press / journalists | "An AI bridge between the lesson and the world that won't sit still" | Tech-stack details |

---

*This doc is updated as the product evolves. If you find yourself
correcting Claude.ai with the same fact twice, that fact belongs
here. The next promo-prompt iteration should be one step shorter,
not one fact longer.*
