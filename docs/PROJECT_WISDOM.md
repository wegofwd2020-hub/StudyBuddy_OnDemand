# EXTRACT WISDOM: StudyBuddy OnDemand

> A K-12 AI education platform whose architecture quietly makes "always current" a structural property, not a marketing claim.

> **Captured:** 2026-05-04 · **Skill:** ExtractWisdom (Full depth) · **Source:** Whole-project synthesis after a session covering Epic 17 fork debate, Epic 18 catalog, three live use cases on `/jt`, D-ID integration, and the engine-vs-wrappers thesis. Re-run anytime by saying *"extract wisdom from the StudyBuddy_OnDemand project"*.

---

## The Information Bridge Is a Search Engine, Not a Library

A library is curated by selection — someone picks books, the books go stale, and "current" becomes a marketing lie. A search engine is curated by query — the query runs every time, the index updates underneath, and "current" is just true. StudyBuddy is the second kind. That structural choice is doing all the work.

- The product is parametrised over six dimensions: topic, grade, language, prior knowledge, format, real-world framing. Six knobs, infinite content.
- "The LLM is the commodity. The scoping layer is the product IP." That line drives every architecture decision in the codebase.
- When a teacher uploads a curriculum, the product doesn't store new content. It stores new scope. The content is generated against that scope on demand.
- Every code path that touches `pipeline/prompts.py` or `pipeline/build_grade.py` is a knob in the scoping layer, not a content step. Touch it like you're tuning a search engine.
- This makes "always current" a structural property, not a promise. You can't break it without breaking the architecture.

## One Word That Earns Its Keep

The tagline says "a world that's always **current**." Not "today's." Not "latest." Not "up-to-date." Current. The team has a memory file dedicated to defending this single word.

- "Today's" anchors to a specific date. A snapshot. "Current" anchors to "whenever the student is using the product." Evergreen versus dated.
- The word has to cover three roadmap phases: pre-generated content now, teacher-generated content soon, AI-agent on-demand later. "Today's" breaks at phase two. "Current" doesn't.
- The memory note says it explicitly: do not swap this word. If "current" feels awkward in a sentence, restructure the sentence.
- That level of discipline about a single word is the gold standard. Most companies will swap their tagline three times before noticing the structural failure.

## How a Single Demo Almost Caused a Codebase Fork

A reviewer named John Thomas suggested a corporate compliance training use case. Within 24 hours the project was halfway to forking the entire codebase. Then the advisor stepped in.

- The advisor's first counterpoint cut deep: "The scoped-retrieval IP generalises. Corporate L&D is a tenant config dimension, not a fork."
- Forking would have hard-coded what should have been a parameter. That's the difference between architecture and reflex.
- Three demo signals were being conflated as one product mandate. None of them said "build a separate product." Reading a data point as a directive is the founder's classic mistake.
- The codified rule that came out of it: "≥2 independent signals + paid LOI/pilot + code paths that genuinely cannot coexist as tenant config" before any repo-level split.
- Path A — don't fork, use a tenant_type enum, build one slice for a design partner — won. Path B and Path C live in the docs as the alternatives that didn't.

## The Four Signals That Killed the Fork Argument

The fork hypothesis got even weaker once more demand signals surfaced.

- Sridhar wanted a B2C interface to LLM content. John Thomas wanted corporate compliance quizzes. Venkit wanted teacher-authored content with AI as optional assist. Silas's mom wanted a visual social-story video for her autistic son.
- All four want the same engine. Each wants a different wrapper.
- Output medium varies wildly: text quiz, dialog scenario, social-story video, K-12 lesson. The upstream is identical: scoped query into structured generated content.
- The right structural answer becomes obvious once you see four signals at once. Build the engine. Ship multiple wrappers. Don't fork per vertical.
- Silas's mom is parked, not abandoned. The trigger to unpark is a video-rendering substrate getting built for an adjacent reason. Patience as architecture.

## How They Keep Three User Worlds From Touching

The auth model handles three completely different user populations without contaminating any of them. The RLS layer makes sure even a leaked credential can't cross tenants.

- Auth0 exchange handles self-registered students and teachers. Local bcrypt handles school-provisioned users. Admin bcrypt with a separate JWT secret handles internal staff.
- Each track has its own login endpoint, its own JWT secret, its own token storage key. A student JWT cannot leak into the teacher endpoints.
- First-login forced password reset is enforced at the **portal layout level**, not just the login page. Direct navigation to `/school/dashboard` after a token issue still bounces to change-password.
- Every tenant-scoped table has FORCE ROW LEVEL SECURITY plus a `tenant_isolation` policy keyed on `app.current_school_id`. The session variable is set in the connection-pool acquire wrapper.
- A sentinel bcrypt hash is computed at module import and burned on unknown-email lookups, specifically to prevent timing-attack email enumeration. That detail tells you someone has been thinking about the threat model.
- A non-superuser test role exists because the main DB user is a superuser and bypasses FORCE ROW LEVEL SECURITY. RLS tests against a superuser are theatre.

## How to Not Block the Event Loop on Your Own Database

Backend rules read like commandments and they're the right ones.

- "The hot read path touches zero DB queries on cache-warm requests." JWT verify is in-memory. Curriculum trees are L1 TTL cache. Content is L2 Redis. Postgres is the last resort.
- "Audio is never proxied through the API server." The endpoint returns a pre-signed CloudFront URL. The client fetches MP3 bytes from the CDN. That single decision is the difference between scaling and falling over.
- "Progress writes are fire-and-forget." Dispatch a Celery task, return 200, never await a DB write on the request path. Idempotency at the consumer side via `event_id`.
- "Redis AOF persistence is mandatory in production." Without it, a Redis restart logs out every student and resets every rate-limit counter.
- Connection pools initialised once per worker in the lifespan context. PgBouncer in transaction-pooling mode in front. Numbers chosen with worker count in mind.
- Clearing Redis cache without invalidating the CDN is a pitfall. The team writes them as a paired operation. Stale JSON for an hour will ruin a content version bump.

## The 33-Pitfall Manifesto

There's a section in CLAUDE.md called "Top Pitfalls." It has 33 items. Some teams call this technical debt. This team calls it institutional memory.

- "Mobile/web app calling Anthropic directly — it has no API key and must never do this." Pitfall #1. The kind of rule you write after almost shipping the wrong architecture.
- Pitfall #25: parallel pipeline runs race on `meta.json`. Firing `build_grade.py --force` while a Celery trigger is running for the same curriculum causes unit-level collisions. Specific. Hard-won.
- Pitfall #29 catches a bug that takes a full day to find: `published_at` must be a `datetime` instance, not a string, or asyncpg silently fails the INSERT.
- Pitfall #30: `unit_name NOT NULL` in `curriculum_units` — pass `title` as both `title` and `unit_name`, or every row insert silently fails. Caught by issue #249, written down to never happen again.
- Pitfall #28 documents the worst class of RLS bug — pipeline CLI must `SET app.current_school_id = 'bypass'` after acquiring a connection, or every platform-curriculum write silently drops.
- The pattern across all 33: who would forget this, how would they fail, what specifically would go wrong. Documentation as failure-mode prevention.

## Spicy Takes Stitched into the Doctrine

Memory files double as a manifesto. Several read like opinions, not procedures.

- "Don't recommend repo fork or monorepo extraction on a single demo signal." Codified after broker almost made that exact mistake.
- "Naming before positioning is a founder trap." Logged after the brand shortlist exercise was rightly paused.
- "Domain language IS positioning. Corporate buyers will not buy a 'StudyBuddy'-branded compliance trainer."
- "When Forge returns `unavailable`, re-route the spec to Engineer rather than silent fallback." Even the agent fallback policy has a position.
- "Plan means stop. Present and STOP. No execution without approval." Reversibility-aware, not reflexive.

## The Honest-Cost UI

Use Case #3 ships as a text-only preview because the videos haven't been generated. Most products would hide that. This one labels it.

- The landing page shows an amber "Preview · text only" chip on cards without video assets. Honesty as a UX feature, not a confession.
- Each card shows itemised cost: LLM authoring, image generation, D-ID video, plus a total. The numbers are estimates and the UI says so.
- A catalog footer aggregates time and cost across all scenarios. It recomputes when you add a scenario, with no manual maintenance.
- The transparency is structural. The data type itself has a `ship_status: "live" | "preview"` field. The UI just renders the truth.

## Pinning as Memory Architecture

Multiple things are deliberately parked, with explicit unpark triggers and full state captured. The team has internalised "park well" as a primitive.

- The Silas's-mom autism-video use case is parked but not abandoned. The unpark trigger is a video-rendering substrate getting built for an adjacent reason. Resume-able patience.
- Use Case #3 video generation is pinned with a specific resume command. Say "finish #3" and broker picks up exactly where it stopped. No recap needed.
- `project_parked_topics.md` is the index. Each parked item links to a dedicated memory file with full context.
- The same pattern applied to discussion topics — "hosting decision parked while testing" — shows the team treats deferral as a first-class operation, not a one-off.

## Quotes That Hit Different

- "The LLM is the commodity. The scoping layer is the product IP."
- "A library is curated by selection. A search engine is curated by query. StudyBuddy is the second kind."
- "Domain language IS positioning."
- "Naming before positioning is a founder trap."
- "Three similar lines is better than a premature abstraction."
- "If 'current' feels awkward in a sentence, restructure the sentence — do not swap the word."
- "Plan means stop."

## First-Time Revelations

- D-ID's `s3://...` URLs are an internal storage format. The `/talks` API returns a 403 "explicit deny" when account credits hit zero. The error message lies, but only a little.
- The pipeline has a `format_drift` validator that fires when a section title says "Table of X" but the output is plain text. Quality control as a first-class concept in content generation.
- StudyBuddy supports curriculum streams as a curriculum-identity suffix. Five system streams seed the registry. Schools register more on first use, no migration needed.
- COPPA compliance is structural. Students under 13 must get parental consent before account activation. The `parental_consents` table existed since migration 0001.
- The Preview-vs-Live distinction is a `ship_status` field on the metric struct, not a feature flag. The product treats "incomplete" as a valid state, not a hidden one.

---

## One-Sentence Takeaway

A K-12 platform built as a scoped-retrieval engine, where every product decision protects the line between commodity model and proprietary scoping.

## If You Only Have 2 Minutes

- StudyBuddy is a scoped-retrieval search engine, not a content library. That's why "always current" is structural truth.
- The IP is the scoping layer (six dimensions), not the LLM. Every code touchpoint is a knob in that scoping layer.
- Four independent demand signals proved the engine generalises. The wrappers vary; the engine doesn't.
- The advisor caught a near-fork on a single signal. The codified lesson: don't split codebases on demo signals.
- Three auth tracks plus RLS-as-tenant-boundary plus fire-and-forget writes plus pre-signed CDN audio. Standard architecture done with discipline.
- The 33-item "Top Pitfalls" list reads like a manifesto. Specific failure modes, not generalities.
- Honest-cost UI: text-only preview labelled as preview. Transparency as a UX feature.

## References & Rabbit Holes

- **Carol Gray's Social Stories™** — research-validated intervention with a strict sentence-ratio formula; the methodology any future autism-video wrapper would need to honour.
- **D-ID `/talks` API** — talking-avatar generation; the project's path from text dialog to video. Cost gates the catalog.
- **FCPA §78dd-1 + §78m** — the statutory anchors for the corporate-compliance scenarios; books-and-records plus anti-bribery.
- **Postgres FORCE ROW LEVEL SECURITY** — the multi-tenancy primitive; the project's RLS implementation is one of the cleaner real-world examples to study.
- **The "scoped retrieval" mental model** — applies far beyond StudyBuddy. Any LLM product hits a moment where it has to decide: are we a content library or a scoping engine?
- **PAI Algorithm v6.3.0** — the meta-process that produced the advisor pushback that reshaped the fork decision. The "ISA as system of record" pattern transfers.
