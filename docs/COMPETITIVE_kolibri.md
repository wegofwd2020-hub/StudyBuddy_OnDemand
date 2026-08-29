# Kolibri, read against StudyBuddy

**Landscape read — 29 August 2026.**
Source: [learningequality.org/kolibri/about-kolibri](https://learningequality.org/kolibri/about-kolibri/)
· Companion piece: [`DESIGN_kolibri_site_teardown.md`](DESIGN_kolibri_site_teardown.md)

Kolibri is an offline-first learning platform from Learning Equality, a non-profit.
It is open source and free. It solves the problem StudyBuddy has deliberately not
taken on — teaching where there is no internet — and mostly does not compete with us.

---

## What it is

Kolibri describes itself as *"an ecosystem of open digital products and tools
centered around an offline-first learning platform."* That sentence is the whole
product strategy; everything else follows from it.

It installs on a server — often a low-cost machine in a school — and serves learners
over a local network with no internet at all. Content arrives once by download, then
spreads by USB stick or peer-to-peer sync between Kolibri instances. It targets
*"low-cost and legacy devices and operating systems"*, with an Android app for
version 6 and newer.

The library covers K–12 across STEM, public health, internet safety, coding, life
skills and teacher professional development, in **173 languages**, drawn from openly
licensed material.

---

## The five pieces

| Component | What it does |
|---|---|
| **Kolibri** | The learning platform. Learners work at their own pace with instant feedback; coaches get a progress dashboard. |
| **Kolibri Studio** | Where curriculum specialists align open resources to standards and assemble custom channels for offline distribution. |
| **Kolibri Library** | The curated corpus — 173 languages of openly licensed K–12 material. |
| **Data Portal** | Cross-school monitoring for programme administrators: visualisations and exports across many deployments. |
| **EdTech Toolkit** | Train-the-trainer material for blended learning. Not software — the implementation half of the product. |

**Studio is the piece worth studying.** It answers the same question StudyBuddy
answers with a scoped LLM query: *how does material become curriculum-aligned at
scale?* Kolibri answers with people plus tooling; StudyBuddy answers with generation.
Same problem, opposite cost curve — theirs is linear in specialists, ours is linear
in tokens.

---

## Architecture

The server is a Django application with pure-Python runtime dependencies, over SQLite
or PostgreSQL. The frontend is Vue. Plugins are ordinary Django apps registered into
`INSTALLED_APPS`.

The notable part is **Morango** — a database replication engine for Django they built
because nothing off the shelf did it. It lets Kolibri instances sync partitioned
datasets (a "learning facility") peer-to-peer. That is the load-bearing component:
offline-first is easy to say and hard to do, and the hard part is exactly what
Morango is.

Notably absent from their own product pages: **any mention of AI or automated content
generation.**

---

## Where the two sit

| Axis | Kolibri | StudyBuddy |
|---|---|---|
| Connectivity | Offline-first; internet optional and rare | Backend-powered; assumes connectivity |
| Content origin | Human-curated open educational resources | Generated per scoped query, per grade and language |
| Freshness | Fixed when the channel was built | Re-runs; "lessons, always current" |
| Curriculum fit | Specialists align resources in Studio | Scoping layer: topic, grade, language, prior coverage, format |
| Commercial model | Free, open source, grant-funded non-profit | School subscription |
| Who deploys it | NGOs, ministries, programme implementers | The school itself, self-serve |
| Hardware floor | Deliberately low — legacy devices, LAN server | A browser and a network |

The overlap is thinner than the category suggests. Kolibri's buyer is a programme
running schools without reliable power, let alone bandwidth. StudyBuddy's buyer is a
school with both, paying for content that stays current. A deployment that needs
Kolibri usually cannot use StudyBuddy at all, and a school that can use StudyBuddy
would find Kolibri's content static.

---

## Four things they have got right

1. **The implementation toolkit is part of the product.** Kolibri ships
   train-the-trainer material alongside software. Our school-admin onboarding stops
   at the setup checklist (`/school/setup`).

2. **"Content specialist" is a named role.** They designed for the person who aligns
   material to standards. We have the capability — the `curriculum_mgmt` grant, the
   Authoring Studio — but have not named the job in the product the way they have.

3. **Cross-school monitoring is a separate product.** The Data Portal is not a bigger
   dashboard; it is a different audience with different questions. Worth remembering
   before Epic 5 (district admin) becomes "the school dashboard with more rows".

4. **They publish outcome research.** Literacy and numeracy gains, pass rates,
   re-enrolment. We have no equivalent evidence base, and a ministry or district will
   eventually ask for one.

---

## Two claims that need discounting

> **"Installed in 220+ countries and territories"**

There are roughly 195 countries. The figure reaches 220 by counting territories, and
*"installed in"* is a download statistic, not an adoption one — open-source software
gets installed everywhere by people evaluating it. Treat it as reach, not usage.

> **"Re-enrolment of out-of-school learners up to 97%"**

*"Up to"* marks this as the best result from some study, not a typical one, and
re-enrolment programmes select hard for motivated participants. The direction is
probably real; the number is a ceiling, not an expectation.

Neither is dishonest — this is ordinary non-profit impact framing. But if any of it
reaches a StudyBuddy comparison deck it must be **cited as their claim**, not repeated
as fact. The precedent is on record: in July a brief's prose shipped two false
StudyBuddy claims live, because "apply this copy" was read as a warrant that the copy
was true. Grep the source before repeating a product claim — including someone
else's.

---

## The strategic question: does offline matter for us?

Kolibri exists because a large part of the world cannot assume connectivity.
StudyBuddy assumes it everywhere — though the mobile app (Epic 3) already carries an
offline sync design, so the question is not whether it has been considered but how far
it goes.

The honest tension: **StudyBuddy's core claim is that content stays *current*, and
current is exactly what offline distribution cannot deliver.** A cached lesson is a
snapshot. Any offline story has to be framed as *degraded operation for a school with
intermittent connectivity* — not as market entry into the contexts Kolibri serves,
where Kolibri is both free and a decade ahead on the hard part.

Where the two could genuinely meet is **Kolibri Studio as an import source**: openly
licensed, standards-aligned material in 173 languages is a corpus, and a
scoped-retrieval system benefits from grounding material. That is a research question,
not a roadmap item, and it needs a licence review before it is anything.

---

## Sources

- [About Kolibri](https://learningequality.org/kolibri/about-kolibri/)
- [Kolibri product ecosystem](https://learningequality.org/kolibri/)
- [Kolibri developer documentation — tech stack](https://kolibri-dev.readthedocs.io/en/develop/stack.html)
- [learningequality/kolibri](https://github.com/learningequality/kolibri)
- [learningequality/studio](https://github.com/learningequality/studio)

Product facts and quoted phrasing come from Learning Equality's own pages. The
comparison, the discounting of the two claims, and the strategic reading are ours.
