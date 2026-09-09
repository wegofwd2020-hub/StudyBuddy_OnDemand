# StudyBuddy OnDemand — CLAUDE.md

Backend-powered AI education platform for Grades 5–12. StudyBuddy is the
information bridge between classroom lessons and the current world. Students
get instant pre-generated content (lessons, quizzes, audio) in English, French,
and Spanish — no Anthropic API key required on the client. Schools and teachers
can upload custom curricula. Subscription-based.

---

## Positioning

StudyBuddy has two framings that serve different audiences. Both are correct;
use the one matched to the reader. Full decision log in
[`docs/BRANDING_TAGLINE_OPTIONS.md`](docs/BRANDING_TAGLINE_OPTIONS.md); epic spec
in [`docs/epics/EPIC_13_branding_refresh.md`](docs/epics/EPIC_13_branding_refresh.md).

### Consumer framing — "information bridge"

- **Tagline:** *"Lessons, always current."*
- **Sub-headline:** *"AI-powered lessons, quizzes, and tutorials — your bridge from classroom to a world that won't sit still."*

Use this framing on: landing page, emails, help-widget responses, marketing
pages, anything user-facing for parents / students / teachers / school admins.

### Engineering mental model — "scoped retrieval over the world of knowledge"

Every content generation is a **scoped query** against the LLM, parametrised
by six dimensions that together form the product's IP:

| Scope dimension | What it enforces |
|---|---|
| Topic / subject / unit | Curriculum alignment |
| Grade | Reading level, conceptual depth, age-appropriateness |
| Language | en / fr / es / vernacular |
| Curriculum context | What the student has already covered |
| Format | Lesson / quiz / tutorial / experiment |
| Real-world framing | The bridge — connect to something current the student recognises |

The LLM is the commodity. The **scoping layer** is the product IP. When
touching `pipeline/prompts.py`, `pipeline/build_grade.py`, or any LLM-calling
code: think "I'm tuning a scoped-retrieval system," not "I'm writing a content
library."

**Structural consequence — why "current" holds:** a *library* is curated by
selection (static, goes stale); a *search engine* is curated by query
(dynamic, re-runs each time). StudyBuddy is the second. This is why the
"always current" tagline claim is defensible, not cosmetic.

### Audience translation matrix

| Audience | Use which framing |
|---|---|
| Parents, students, teachers, school admins | Information bridge |
| Developers, architects, internal technical discussions | Scoped retrieval |
| VCs / B2B pitch decks | Scoped retrieval first (30 sec), then bridge metaphor |

### Load-bearing word — "current" (not "today's")

Tagline uses **"current"** deliberately. **Do not** swap it for "today's",
"latest", or any dated alternative. Reason: "today's" anchors to a specific
date (a snapshot); "current" anchors to "whenever the student is using the
product" (evergreen). The tagline has to cover three phases:

1. **Now** — pre-generated content per curriculum
2. **Soon** — teachers generate more content as a course progresses
3. **Roadmap** — AI Agent where students query and learn more on demand

"Today's" breaks at Phase 2/3. "Current" is the agent's actual promise. If
"current" feels awkward in a sentence, restructure the sentence (e.g. *"a
world that's always current"*, *"keeping lessons current with the world"*) —
do not swap the word.

---

## Project Status

**Phases 1–11 complete. Phase A (local auth) shipped. Phases B–E complete. Epic 1 complete. Epic 8 H-8/H-9/H-10 (Stream layer) shipped. Epic 10 L-1 through L-5 + L-7 + L-8 shipped. Epic 11 C-1 through C-6 + C-9 shipped; C-5 in progress. Epic 12 TA-0 through TA-4 shipped. Epic 15 BR-1 through BR-6 complete. Epic 16 S-1 through S-5 shipped.**

| Phase | Status |
|---|---|
| 1 — Backend Foundation | ✅ Complete (38 tests) |
| 2 — Content Pipeline + English Delivery | ✅ Complete (52 tests) |
| 3 — Progress Tracking | ✅ Complete (73 tests) |
| 4 — Offline Sync + Push + Analytics | ✅ Complete (87 tests) |
| 5 — Subscription + Payments | ✅ Complete (99 tests) |
| 6 — Experiment Visualization | ✅ Complete (100 tests) |
| 7 — Admin Dashboard + Analytics + Content Review | ✅ Complete (124 tests) |
| 8 — School & Teacher + Curriculum Upload + Academic Year | ✅ Complete (159 tests) |
| 9 — Student–School Association + Routing | ✅ Complete (176 tests) |
| 10 — Extended Analytics + Student Feedback | ✅ Complete (197 tests) |
| 11 — Teacher Reporting Dashboard | ✅ Complete (215 tests) |
| Phase A — Local Auth (school-provisioned users) | ✅ Complete (678 tests) |
| Phase B — Classrooms | ✅ Complete (migration 0038, 21 tests, web UI) |
| Phase C — Curriculum Catalog | ✅ Complete (6 tests, catalog browser UI) |
| Phase D — Curriculum Builder | ✅ Complete (migration 0039, 19 tests, definition form + approval queue UI) |
| Phase E — Pipeline Billing | ✅ Complete (10 tests, cost estimate + Stripe-gated trigger) |
| Epic 1 — Multi-Provider LLM Pipeline | ✅ Complete (migration 0043, 19 tests, F-1–F-5) |
| Epic 8 H-8/9/10 — Stream layer + registry | ✅ Complete (migrations 0044, 0045, 18 tests; admin CRUD, upsert-on-use) |
| Epic 10 L-1…L-5 + L-7 + L-8 — Curriculum lifecycle (archive) | ✅ Complete. L-7: `/admin/archive/curricula` with filters, TTL badge, unarchive action. L-8: catalog filters archived; library shows amber banner with reason for platform-archived adoptions; fork content still served. L-6 sweeper paused; L-9/L-10 pending. |
| Epic 11 C-1…C-4, C-6, C-9 — Content formatting | ✅ Pipeline + renderer complete (GFM tables, KaTeX math, per-subject guidelines, format-drift validator, attributed quotes). C-5 in progress (regen); C-7/C-8 pending |
| Epic 12 TA-0…TA-4 — School curriculum library | ✅ Backend + web complete (migrations 0050, 0051; adopt/deactivate, fork-on-import, draft/review/approve/reject workflow; pipeline guard; 27 tests; /school/library + /school/content UI) |
| Epic 15 BR-1…BR-6 — Curriculum backup & restore | ✅ Complete (migrations 0053–0055; BackupStorageBackend, SHA-256 manifest, Celery tasks, 14 REST endpoints, 5 admin pages + 4 school portal pages; 27 tests; router bug fixed: `async with get_db(request)` pattern). |

**Active branch:** `main` (next: see `docs/epics/` — product backlog)

**Recently shipped (beyond Phase 11):**
- **School-admin UX overhaul (2026-06) — Administration menu + pickers + setup wizard:**
  - **Administration menu (#415 / #417):** top-bar `web/components/layout/AdministrationMenu.tsx`
    replaces the standalone "Curriculum Management" dropdown — groups a **Curriculum**
    section (gated `canManageCurriculum`) + a **User Management** section
    (Students/Teachers, `school_admin` only); left-rail infra group renamed **"Settings"**;
    `isSchoolAdmin()` helper added to `web/lib/hooks/useTeacher.ts`.
  - **Classroom assignment pickers (#418 / #419):** the classroom curriculum and student
    "assign" controls are now **dropdowns** (from the school library / roster,
    grade-filtered, excluding already-assigned) instead of raw-UUID text inputs.
  - **"Set up your school" wizard (#420):** guided 6-step checklist at `/school/setup`
    ("Get started" rail item, school_admin), auto-ticked from existing data; pure logic
    in `web/lib/school/setup-checklist.ts`.
  - **School user-management decisions:** [`docs/ADR_005_school_roles_and_uniqueness.md`](docs/ADR_005_school_roles_and_uniqueness.md)
    (school_admin = teacher **superset** role · **email-only** uniqueness · account delete =
    **soft-delete + archive** + FERPA retention) + the [`docs/SCHOOL_USER_MANAGEMENT.md`](docs/SCHOOL_USER_MANAGEMENT.md)
    Type-1 self-managed onboarding spec.
- **Backup & Restore investigation closed (2026-06):** #410 fixed backup creation
  (`backup_school_task` read `r["id"]` but the `curricula` PK is `curriculum_id`, TEXT);
  #423 reconciled the **restore path** schema (#411 — `dry_run_/execute_restore_task`
  referenced non-existent `id`/`grade`/`ordering`/`updated_at`, omitted NOT NULL `year`,
  used `ON CONFLICT (id)`); #424 stopped failure-notification emails leaking raw
  `str(exc)` + school/backup UUIDs to the contact (#413, Content Rule #5).
  `backend/scripts/purge_account.py` (#416) hard-deletes a single teacher/student by email for test cleanup.
- Content review unit viewer — Lesson / Tutorial / Quiz / Experiment renderers
- Inline reviewer annotations scoped per section, question, and step
- Side-by-side version diff with word-level highlighting
- Pipeline improvements: `max_tokens=8192`, `subject_name` column, `payload_bytes` tracking
- Demo teacher account request / verify / login flow
- Admin pipeline jobs table: sortable, filterable, horizontal scroll
- School-as-primary-entity model: `student_teacher_assignments` (migration 0024), per-student grade+teacher assignment, bulk reassign, grade self-change guard
- **Phase A local auth**: third auth track for school-provisioned users — email+password login, `first_login` forced reset, school self-registration, teacher/student provisioning UI, `LocalAuthGuard` portal gate, JWT refresh interceptor (migrations 0030–0037)
- **Phase B Classrooms**: `classrooms`, `classroom_packages`, `classroom_students` tables (migration 0038); classroom CRUD + package/student assignment endpoints; Classrooms nav + list/detail pages in school portal; 21 tests
- **Phase C Curriculum Catalog**: `GET /curricula/catalog` endpoint with optional `?grade=N` filter; lists platform packages with per-subject content readiness; catalog browser page at `/school/catalog` with expandable subject list and readiness bar; 6 tests
- **Phase D Curriculum Builder**: `curriculum_definitions` table (migration 0039, RLS); submit/list/get/approve/reject endpoints; 4-step definition form at `/school/curriculum/definitions/new`; approval queue at `/school/curriculum/definitions`; detail+review page; 19 tests
- **Phase E Pipeline Billing**: cost estimate endpoint (`/definitions/{id}/estimate`) — unit runs, token forecast, `within_allowance`, `card_last4`; trigger endpoint (`/definitions/{id}/trigger`) — confirm gate, concurrency guard, Stripe PaymentIntent on allowance exhaustion, Celery dispatch; `source_type='school'`; 10 tests; `run_stripe` module-level import for patchability
- **Epic 1 Multi-Provider LLM**: `pipeline/providers/` package — `LLMProvider` ABC + `AnthropicProvider`, `OpenAIProvider`, `GeminiProvider`; `get_provider()` registry; `provider` column on `content_subject_versions` + `pipeline_jobs` (migration 0043); `--provider` CLI flag; comparison builds via `run_grade(providers=[...])` sequential loop; `ProviderBadge` UI chip on review queue; `school_llm_config` table with RLS; `GET/PUT /schools/{id}/llm-config`; DPA acknowledgements as append-only JSONB; 19 tests
- **Epic 8 Stream layer (H-8/H-9/H-10)**: Stream as curriculum-identity suffix (Option A). Migration 0044 adds nullable `curricula.stream_code`, `students.stream`, `teachers.stream`. Migration 0045 adds the soft-registry `streams` table with 5 system seeds (`science`, `commerce`, `humanities`, `english`, `stem`) — no FK from curricula so rename/merge is a data action. Admin `/admin/streams` CRUD + archive/unarchive/merge/delete endpoints; upload-grade endpoint upserts unknown streams on-first-use when `stream_display_name` is supplied. Admin UI at `/admin/streams`, `/admin/streams/new`, `/admin/streams/[code]` with typeahead on the Upload page. 18 stream-specific tests
- **Epic 10 Curriculum lifecycle (L-1…L-5)**: Migration 0046 adds three per-command RESTRICTIVE RLS policies on `curricula` refusing INSERT/UPDATE/DELETE on `owner_type='platform'` rows from non-bypass sessions (schools still SELECT via the existing permissive policy). Migration 0047 adds `retention_status='archived'` + partial index for the TTL sweeper. Migration 0048 drops stale policies from the L-1 debug draft. `is_curriculum_in_use()` + `get_curriculum_usage_summary()` helpers gate archive on active-enrolment count via `grade_curriculum_assignments`. `POST /admin/curricula/{id}/archive` (super-admin-for-platform, super-admin-archives-school with required reason); `POST /schools/{school_id}/curricula/{curriculum_id}/archive` (school_admin own-content only). Fire-and-forget audit events via `write_audit_log`: `curriculum.archive`, `curriculum.archive_by_platform_admin`, `curriculum.unarchive`, `curriculum.hard_delete_by_sweeper` (sweeper unimplemented yet). 1-year TTL. L-6 sweeper paused per user call; L-7 super-admin archive view + L-8 school UI pending
- **Epic 11 Content Formatting (C-1…C-4, C-6, C-9)**: `pipeline/prompts.py` now embeds a universal formatting block (GFM tables with alignment markers, KaTeX `$...$` delimiters, currency-escape rules, fenced code blocks, attributed blockquotes with no invented citations) plus a per-subject block keyed by subject name (Commerce → Balance Sheet / P&L templates; Natural Sciences → KaTeX formulae + reaction mechanisms; Mathematics → every expression in KaTeX; CS → truth tables + Big-O). Web renderer: shared `<SBMarkdown>` component at `web/components/content/Markdown.tsx` with `remark-math` + `rehype-katex` wired; KaTeX CSS imported globally; Examples in tutorials now route through markdown rather than `<pre>` (previously rendered GFM tables as ASCII art). `max_tokens` raised from 8192 → 16384 on both Anthropic + OpenAI providers to prevent mid-string JSON truncation under richer prompts. `pipeline/content_format_validator.py` emits `format_drift` warnings when a section title suggests tabular/formula content but the output lacks it. C-5 targeted regen in progress (Grade 11 Commerce done; Grade 11 Science in flight). C-7 PDF smoke-check + C-8 mobile parity pending
- **Epic 12 School Curriculum Library (TA-0…TA-4)**: Fork/import content model — schools adopt OOB platform curricula (`school_adopted_curricula` table, migration 0050); on first teacher import a school-owned fork is created (`curricula.source_curriculum_id`) and overrides stored in `unit_content_overrides` (append-only version table) + `unit_content_active_versions` (active pointer), migration 0051. Content lifecycle: draft → pending_review → approved/rejected → active. `pipeline/guard.py` advisory check warns when pending school overrides exist for an OOB unit being regenerated. School portal: `/school/library` adoption browser, `/school/content/[curriculum_id]` unit list + import entry, `/school/content/adopt/[adoption_id]` draft editor + review UI. 27 tests (914 total; 0 failing)
- **Epic 15 Backup & Restore (BR-1…BR-6)**: Migrations 0053–0055 (`curriculum_backups` + `backup_restore_requests` + `schools.backup_cron`, all RLS-scoped per school). `src/backup/` package: `BackupStorageBackend` ABC with `LocalBackupStorage` + `S3BackupStorage`; SHA-256 manifest; 5 Celery tasks; 11 service functions (deduplication, 8-state machine); 14 REST endpoints (10 admin, 4 school). Router bug fixed: all handlers now use `async with get_db(request) as conn:` (was `Depends(get_db)` which is incompatible with `@asynccontextmanager` in Python 3.12+). Admin UI: 5 pages. School portal (BR-6): `/school/backups`, `/school/restore-requests`, `/school/restore-requests/new`, `/school/restore-requests/[id]/confirm`. 27 tests in `tests/test_backup.py`.
- **Epic 16 Public Site Redesign (S-1…S-5)**: School-first PublicNav (school sign-in + register CTAs); landing page rewrite (hero tagline + 6 feature cards + tour gateway); `/for-schools` page (hero + how-it-works + 8-feature grid + pricing tiers + FAQ + CTA); About page trust signals (FERPA/COPPA/WCAG/data minimization cards); a11y pass (For Schools link in PortalFooter).

**Open tasks:**
- See `docs/epics/` for the full product backlog (11 epics; see `INDEX.md`)
- Epic 2 — Production launch & demo readiness (hosting blocker)
- Epic 3 — Student mobile app (Path B: Expo/RN chosen; parked behind testing + hosting)
- Epic 4 — Parent portal (💭 your call)
- Epic 5 — District admin (💭 your call)
- Epic 6 — Platform hardening (K-4/K-5 need staging)
- Epic 10 — Curriculum lifecycle remaining phases:
  - L-6 TTL sweeper (paused per user)
  - L-9 per-jurisdiction read-audit mode
  - L-10 TTL override endpoint
- Epic 11 — Content formatting remaining phases:
  - C-5 regen (Grade 11 Science resume in flight; Grade 12 Commerce + Grade 12 Science + Maths-heavy units pending)
  - C-7 PDF smoke check
  - C-8 mobile renderer parity (waits on Epic 3)
- Epic 15 — Backup & Restore remaining:
  - BR-DOC-1 Sys Admin Operations Guide (lower priority)
  - BR-DOC-2 School Admin User Guide (lower priority)
- Tracked issues:
  - #188 — e2e test case: school-admin curriculum submission → pipeline → student-visible content
  - #189 — a11y debt: `color-contrast`, `html-has-lang`, `document-title` axe rules disabled in persona Playwright specs

Predecessor project (UI + prompt reference):
`https://github.com/wegofwd2020-hub/studybuddy_free`

---

## Document Map

Before writing any code, read these in order:

All documentation has moved to **[studybuddy-docs](https://github.com/wegofwd2020-hub/studybuddy-docs)**.

| Doc | Read when |
|---|---|
| [ARCHITECTURE.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/ARCHITECTURE.md) | First — system design, data models, API contracts, all phases |
| [BACKEND_ARCHITECTURE.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/BACKEND_ARCHITECTURE.md) | Before touching backend — caching, hot path, SLOs, deployment |
| [UX_GOALS.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/UX_GOALS.md) | Before any UI/UX work — north star goals per persona; use as a prioritisation filter |
| [REQUIREMENTS.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/REQUIREMENTS.md) | Check requirement ID + status before implementing a feature |
| [AGENTS.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/AGENTS.md) | Conventions, layer rules, 35 pitfalls, phase-by-phase checklists |
| [CHANGES.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/CHANGES.md) | Design decisions log and pending work items |
| [OPERATIONS.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/OPERATIONS.md) | Runbooks, incident response, disaster recovery, deployment procedures |
| [CLOUD_HOSTING.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/CLOUD_HOSTING.md) | Cloud-hosting shopping list — components, sizing tiers, cost ballpark, phased rollout, AWS/GCP/Azure decision matrix |
| [OBSERVABILITY.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/OBSERVABILITY.md) | Local Grafana + Prometheus setup, instrumented metrics, dashboard generator, cardinality rules, alert roadmap |
| [CHEATSHEET.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/CHEATSHEET.md) | Operator one-liners — dev stack, RLS-aware DB queries, password reset, demo accounts, pipeline triggers, smoke tests, Redis ops, deck regeneration |
| [SCALABILITY.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/SCALABILITY.md) | Capacity planning, multi-region, load testing, academic year transitions, API versioning |
| [GLOSSARY.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/GLOSSARY.md) | Acronym and term definitions for all abbreviations used across the project |

**In-repo design docs / ADRs** (live under `docs/` in this repo, not studybuddy-docs):

| Doc | Read when |
|---|---|
| [`docs/ADR_001_tenancy_and_subscription_model.md`](docs/ADR_001_tenancy_and_subscription_model.md) | Tenancy / subscription / school-as-primary-entity decisions |
| [`docs/ADR_004_authoring_studio_home_repo.md`](docs/ADR_004_authoring_studio_home_repo.md) | Where the standalone authoring+reader lives (→ became Mentible, see below) |
| [`docs/ADR_005_school_roles_and_uniqueness.md`](docs/ADR_005_school_roles_and_uniqueness.md) | School roles (`school_admin` = teacher superset), email-only uniqueness, soft-delete + archive |
| [`docs/ADR_006_multi_provider_llm.md`](docs/ADR_006_multi_provider_llm.md) | Multi-provider LLM pipeline (Epic 1, migration 0043) — provider abstraction, `provider` column, `school_llm_config` + DPA, batch-not-agent |
| [`docs/ADR_007_academic_calendar.md`](docs/ADR_007_academic_calendar.md) | Academic calendar, terms and breaks · grade enrolments with outcomes · per-school grading scales (pass marks are NOT 60% everywhere) · promotion gating, the year-start freeze and its correction path |
| [`docs/ADR_008_delivery_calibration.md`](docs/ADR_008_delivery_calibration.md) | Institutional delivery calibration — schools tune delivery of a fixed syllabus year over year; stable question identity, per-question feedback, item analysis (discrimination, not difficulty) feeding generation as a 7th scoping dimension; local loop approved, cross-school platform loop deferred |
| [`docs/SCHOOL_USER_MANAGEMENT.md`](docs/SCHOOL_USER_MANAGEMENT.md) | The Type-1 (self-managed) school user lifecycle + the top-bar **Administration** menu IA (§8.1) |
| [`docs/DESIGN_curriculum_mgmt_capability.md`](docs/DESIGN_curriculum_mgmt_capability.md) · [`docs/SPEC_curriculum_mgmt_capability.md`](docs/SPEC_curriculum_mgmt_capability.md) | The `curriculum_mgmt` capability (#358) — additive grants; menu now lives under Administration (#415) |
| [`docs/COMPETITIVE_kolibri.md`](docs/COMPETITIVE_kolibri.md) | Landscape read on Kolibri (Learning Equality) — offline-first, OER-curated, free; where it overlaps StudyBuddy and where it does not |
| [`docs/DESIGN_kolibri_site_teardown.md`](docs/DESIGN_kolibri_site_teardown.md) | Why the Kolibri marketing page reads as calm — measured type scale, palette and structure, and what is worth borrowing |
| [`docs/DESIGN_public_audience_map.md`](docs/DESIGN_public_audience_map.md) | Mapping Kolibri's audience cards onto our roles — what `/tour` already ships, the unnamed curriculum-specialist role, and why our audience list contains the buyer |

> **Sibling / spun-out projects (2026-06-09):** the standalone, non-school products
> moved to **Mentible** — the `StudyBuddy_SelfLearner` repo (rebrand of "StudyBuddy Q"):
> **StudyBuddy Q + BriefCase + Special-needs Social Stories**. Don't build those here.
> The **home-schooling wedge stays with StudyBuddy** (for now). **MarketingTools**
> (`wegofwd2020-hub/MarketingTools`) is the cross-portfolio promo repo for any
> client-facing product.

---

## Repository Layout

```
StudyBuddy_OnDemand/
  backend/
    main.py              ← FastAPI app entry point + lifespan (DB/Redis pools)
    config.py            ← pydantic-settings; all config from env vars; fail-fast if missing
    alembic/
      versions/          ← migrations 0001…000N; run in order; never skip
    scripts/
      reset_admin_password.py  ← dev utility: reset an admin user's password
      seed_super_admin.py      ← create the initial super_admin account
    src/
      auth/              ← register · login · refresh · forgot-password · reset · delete
      curriculum/        ← serve grade/subject/unit tree from DB
      content/           ← lesson · quiz · tutorial · experiment · audio (pre-generated)
      progress/          ← session · answer · session/end · history
      subscription/      ← Stripe checkout · webhook · plan status
      school/            ← registration · teacher invite · enrolment roster
      analytics/         ← lesson-view events · class metrics · student metrics
      feedback/          ← submit · admin list
      admin/             ← pipeline status · regenerate · audit log · content review
      demo/              ← demo student + demo teacher request/verify flows
      core/              ← cache manager (L1+L2) · entitlement checker · circuit breakers
                            curriculum resolver dependency · Celery dispatcher
                            observability.py  ← Prometheus metrics, GET /metrics, health probes, correlation ID middleware
                                                 Liveness/readiness/health probes are served BOTH at root
                                                 (/healthz, /readyz, /health) and under the API prefix
                                                 (/api/v1/healthz, /api/v1/readyz, /api/v1/health) — the
                                                 /api/v1 aliases exist because nginx proxies /api/v1/* to the
                                                 backend; all probes are include_in_schema=False (not in OpenAPI)
                            events.py         ← emit_event() structured log + metric counter · write_audit_log() Celery dispatch
    tests/               ← pytest; ALL external calls mocked; no live DB in CI
    quiz_suite/          ← live-stack quiz testing suite (pytest, marker: quiz_live); a SIBLING
                            of tests/, never a subdirectory — run explicitly via scripts/quiz_suite.sh,
                            never by plain `pytest -q`; see Testing section below
    requirements.txt

  web/                   ← Next.js 15 app (admin console + public pages)
    app/
      (admin)/           ← admin-only routes (JWT-gated); no SSR — all "use client"
        admin/
          content-review/  ← review queue · version detail · unit viewer · version diff
          pipeline/        ← job list · job detail · upload grade JSON
          demo-teacher-accounts/
          feedback/ · analytics/ · audit/ · ci/ · pipeline/
      (public)/          ← public-facing pages (landing, about, demo request)
      (student)/         ← student portal (Auth0-gated)
      (school)/          ← school/teacher portal (Auth0-gated)
    components/
      layout/            ← PortalHeader · PortalFooter · AdminNav
      demo/              ← DemoRequestModal · DemoTeacherRequestModal · DemoTeacherGate
    lib/
      api/               ← admin.ts · demo.ts · client.ts (Axios instances per role)
      hooks/             ← useAdmin · useTeacher · useDemoStudent · useDemoTeacher
    i18n/                ← en.json (UI strings; AI content is never passed through i18n)

  mobile/
    main.py              ← Kivy entry; thin client; version check on startup
    config.py            ← BACKEND_URL · SQLite path · JWT path; no secrets
    src/
      api/               ← async HTTP client (httpx); all network calls here
      ui/                ← Kivy screens
      logic/             ← SyncManager · LocalCache · ProgressQueue · CurriculumResolver
      utils/             ← structured logger (JSON, same pattern as Free edition)
    data/                ← grade JSON files (curriculum metadata only; no AI content)
    i18n/                ← en.json · fr.json · es.json (UI strings only)

  pipeline/
    build_grade.py       ← CLI: --grade N --lang en,fr,es [--force] [--dry-run]
    build_unit.py        ← CLI: --curriculum-id UUID --unit G8-MATH-001 --lang en
    seed_default.py      ← CLI: --year 2026; seeds default curricula from data/*.json
    tts_worker.py        ← lesson text → MP3 via Polly / Google TTS
    prompts.py           ← prompt builders; shared with Free edition
    config.py            ← ANTHROPIC_API_KEY · TTS_API_KEY · CONTENT_STORE_PATH · CLAUDE_MODEL

  data/                  ← grade5_stem.json … grade12_stem.json (source of truth for default curricula)
  docs/                  ← additional design documents
```

---

## Web Frontend — Tech Stack

| Layer | Choice |
|---|---|
| Framework | Next.js 15 (App Router) |
| Styling | Tailwind CSS v4 — config is in `globals.css` via `@import "tailwindcss"`, **no `tailwind.config.js`** |
| Data fetching | TanStack React Query v5 (`useQuery` / `useMutation`) |
| HTTP client | Axios — separate instances per role in `lib/api/client.ts` and `lib/api/admin-client.ts` |
| Markdown rendering | `react-markdown` + `remark-gfm` (tables, code blocks, bold/italic) |
| Text diffing | `diff` package (`diffWords`) for version diff view |
| Icons | `lucide-react` |
| Auth | Admin: local JWT in `localStorage` key `sb_admin_token`. Students/Teachers: Auth0 |

**Critical Tailwind v4 note:** There is no `tailwind.config.js`. Plugins are added via `@plugin` in
`globals.css`. The `prose` class requires `@plugin "@tailwindcss/typography"` — do not use `prose`
without confirming the plugin is configured. Custom theme values go in `@theme` blocks in the CSS file.

**Hydration rule:** Never read `localStorage` during SSR. Always initialise state as `undefined`/`null`
and populate in `useEffect`. The `PortalHeader` `userName` prop is the canonical example of this pattern.

---

## Admin Console — Route Map

All admin routes live under `/admin/` and require a valid `sb_admin_token` JWT checked in
`app/(admin)/layout.tsx`. Unauthenticated requests redirect to `/admin/login`.

| Route | Purpose |
|---|---|
| `/admin/login` | Local bcrypt login → issues JWT |
| `/admin/` | Dashboard — subscription analytics, system health, CI status |
| `/admin/content-review` | Review queue (filterable by status) |
| `/admin/content-review/[version_id]` | Version detail — units, annotations summary, actions (approve/reject/publish/rollback) |
| `/admin/content-review/[version_id]/unit/[unit_id]` | Unit content viewer — per-section inline annotations |
| `/admin/content-review/[version_id]/diff` | Side-by-side version diff with word-level highlighting |
| `/admin/pipeline` | Pipeline job list — sortable, filterable |
| `/admin/pipeline/[job_id]` | Job detail — progress, payload size, duration |
| `/admin/pipeline/upload` | Upload grade JSON to trigger pipeline |
| `/admin/demo-accounts` | Manage demo student accounts |
| `/admin/demo-teacher-accounts` | Manage demo teacher accounts |
| `/admin/feedback` | Student feedback list |
| `/admin/audit` | Audit log |
| `/admin/authoring` | Authoring Studio — project list + create (super_admin only) |
| `/admin/authoring/[projectId]` | Authoring workspace — analyze · edit structure · materialize · generate · per-topic review/regenerate/accept · snapshots/restore · publish |

**Curriculum Authoring Studio (super-admin only — backend API + web UI):**
Gated by the `curriculum:author` permission, which only `super_admin` holds (via its
`{"*"}` wildcard); `product_admin` and below get 403. Endpoints under
`/api/v1/admin/authoring/` (`backend/src/admin/authoring_router.py`):
- **PR-A — intake → structure:** `POST /projects` (create from pasted free-text TOC) ·
  `GET /projects` · `GET /projects/{id}` · `POST /projects/{id}/analyze` (Celery: structure +
  advisory flow, 202) · `PUT /projects/{id}/structure` (save edits) ·
  `POST /projects/{id}/materialize` (→ staged platform curriculum, `owner_type='platform'`,
  `source_type='admin_authored'`, `is_default=FALSE`, no `school_id`).
- **PR-B — generate → review → publish:** `POST /projects/{id}/generate` (Celery, all topics,
  202) · `GET /projects/{id}/topics/{unit_id}?content_type=&history=` (active or full history) ·
  `POST .../topics/{unit_id}/regenerate` (sync, append-only version with reason + deterministic
  flow recheck; unlimited) · `POST .../topics/{unit_id}/accept` ·
  `POST /projects/{id}/snapshots` + `GET …` + `POST …/{snapshot_id}/restore` (manifest snapshots:
  per-topic append-only versions + whole-curriculum pointer rollback) ·
  `POST /projects/{id}/flow-recheck` (Celery, full LLM re-analysis of current TOC, 202) ·
  `POST /projects/{id}/publish` (`{visibility: private|catalog}`: gates on all active topics
  accepted, writes accepted bodies to the content store + `content_subject_versions`, sets
  `curricula.is_default = (visibility=='catalog')`).

Content model: generated content lives in `authoring_topic_versions` (append-only) with
`authoring_active_versions` pointing at the live version; `authoring_snapshots` hold manifest
snapshots. TOC structuring + flow analysis: `pipeline/toc_structurer.py` +
`pipeline/flow_analyzer.py`; per-topic generation + regenerate: `backend/src/admin/authoring_generation.py`;
cheap no-LLM ordering check: `backend/src/admin/authoring_flow.py`. Generation uses the shared
prompt builders with `diagram_emphasis=True` (Mermaid diagrams + richer prose — counters
"too terse"); `web/components/content/MermaidDiagram.tsx` renders fenced ```mermaid blocks in
`SBMarkdown`. State machine: `draft → analyzing → analyzed → structured → generating → generated
→ published`. Celery tasks (raw asyncpg connections) register the jsonb codec before binding
dict payloads (else asyncpg rejects them — "expected str, got dict").

Web UI (super_admin nav item "Authoring Studio"): `web/app/(admin)/admin/authoring/page.tsx`
(list + create), `web/app/(admin)/admin/authoring/[projectId]/page.tsx` (staged workspace),
`web/components/authoring/*` (StatusBadge, StructuredTocEditor, TopicReviewPanel), API client
`web/lib/api/authoring.ts`. A `GET …/projects/{id}/topics` endpoint backs the topic list. The
topic review panel renders lesson/tutorial via `<SBMarkdown>` so Mermaid diagrams render.

---

## Three Runtime Contexts

These are completely independent at runtime. Never mix their concerns.

```
1. Content Pipeline  (offline, operator-run)
   CLI/Celery → Anthropic API + TTS → Content Store (S3 or filesystem)
   Reads curriculum units from PostgreSQL (or data/*.json for defaults)
   Writes: curricula/{curriculum_id}/{unit_id}/lesson_{lang}.json + MP3 + meta.json

2. Backend API  (always-on server)
   FastAPI + uvicorn → PostgreSQL + Redis + Content Store
   JWT auth · entitlement gating · content serving · progress recording · subscriptions

3. Web / Mobile App  (user device)
   Next.js (admin + public) or Kivy (student mobile) → backend REST API
   NEVER calls Anthropic directly. NEVER has Anthropic or Stripe keys.
```

---

## Layer Rules — Dependencies flow downward only

```
web/app/(admin)/       → web/lib/api/admin.ts → backend /api/v1/admin/*
web/app/(student)/     → web/lib/api/client.ts → backend /api/v1/*
mobile/src/ui/         → mobile/src/logic/,  mobile/src/api/
mobile/src/logic/      → mobile/src/api/
mobile/src/api/        → (external: backend REST)

backend/src/content/      → backend/src/core/  (auth checks, entitlement, cache)
backend/src/progress/     → backend/src/core/
backend/src/subscription/ → backend/src/core/
backend/src/school/       → backend/src/core/
backend/src/analytics/    → backend/src/core/
backend/src/admin/        → backend/src/content/, backend/src/curriculum/,
                             backend/src/subscription/

pipeline/                 → prompts.py, Anthropic API, TTS API, Content Store
                            (completely independent of backend and mobile at runtime)
```

---

## Content Store Layout

All content — default and school — uses the same path shape keyed by `curriculum_id`.
Default IDs follow `default-{year}-g{grade}`. School IDs are UUIDs.

```
{CONTENT_STORE_PATH}/
  curricula/
    {curriculum_id}/
      {unit_id}/
        lesson_en.json      quiz_set_1_en.json   tutorial_en.json
        lesson_fr.json      quiz_set_2_en.json   experiment_en.json  ← only if has_lab
        lesson_en.mp3       quiz_set_3_en.json   meta.json
        …                   …
```

`meta.json` per unit: `{generated_at, model, content_version, langs_built: []}`.
The mobile app caches by `unit_id + curriculum_id + content_version + lang`.

The admin content viewer checks `has_content` by scanning this directory — if a subject's unit
directories are absent, the Review Queue shows "No content" instead of a Review link.

---

## Database Migrations (Alembic)

Migrations live in `backend/alembic/versions/` and are numbered `0001_…` → `000N_…`.

- **Never skip a migration.** Run `alembic upgrade head` after pulling new code before restarting the API.
- **Naming convention:** `{NNNN}_{short_description}.py` — e.g. `0015_subject_name.py`
- **In Docker:** migrations run automatically via the `migrate` service in `docker-compose.yml` on `./dev_start.sh`
- **Manual run:** `docker compose exec -e TEST_DB_URL= api alembic upgrade head`
  ⚠️ The `-e TEST_DB_URL=` is **required**. The `api` service has `TEST_DB_URL` set, and
  `alembic/env.py` prefers it — so a plain `docker compose exec api alembic upgrade head`
  migrates **`studybuddy_test`**, prints "success", and leaves the dev database untouched
  (→ pitfall #18, `UndefinedColumnError` *after* you migrated). Alembic now prints which
  database it is targeting on every run; read that line.
- If the API starts throwing `UndefinedColumnError`, a migration is almost certainly missing.

Current migrations (as of last commit):
| # | Description |
|---|---|
| 0001–0011 | Phase 1–11 schema |
| 0012 | Demo teacher accounts |
| 0013 | Pipeline jobs table |
| 0014 | `payload_bytes` on pipeline_jobs |
| 0015 | `subject_name` on content_subject_versions |
| 0016–0023 | School/teacher/enrolment schema (phases 8–9) |
| 0024 | `student_teacher_assignments` table + `grade`/`teacher_id` on `school_enrolments` |
| 0025 | Schema corrections (ADR-001 G1–G2): `schools.contact_email` UNIQUE + `teachers` school_id CHECK |
| 0026 | Remove private teacher tier (ADR-001): drop `private_teachers`, `teacher_subscriptions`, `student_teacher_access`; tighten `curricula.owner_type` CHECK |
| 0027 | Remove individual student subscriptions (ADR-001): drop `subscriptions` table; subscription webhook now school-only |
| 0028 | PostgreSQL Row-Level Security (ADR-001 Decision 3): `ENABLE/FORCE ROW LEVEL SECURITY` + `tenant_isolation` policy on 7 tables; `app.current_school_id` session variable stamped by `get_db()` |
| 0029 | Lesson Retention Service — Phase A schema (#90): `retention_status`, `expires_at`, `grace_until`, `renewed_at` on `curricula`; `tokens_used`, `cost_usd` on `content_subject_versions`; new `school_storage_quotas` and `grade_curriculum_assignments` tables with RLS |
| 0030 | AlexJS warning acknowledgements — `content_warning_acks` table (#76) |
| 0031 | At-risk seen tracking — `at_risk_seen` flag per teacher/student pair |
| 0032 | Build allowance — curriculum build quota per school subscription year |
| 0033 | Build credits balance — credit rollover balance for curriculum builds |
| 0034 | Independent teacher subscriptions schema |
| 0035 | Teacher Stripe Connect accounts |
| 0036 | Teacher subscription overage tracking |
| 0037 | Phase A local auth — `password_hash TEXT` + `first_login BOOLEAN` on `teachers` and `students` |
| 0038 | Phase B classrooms — `classrooms`, `classroom_packages`, `classroom_students` tables with RLS |
| 0039 | Phase D curriculum definitions — `curriculum_definitions` table with RLS |
| 0040–0043 | Epic 1 multi-provider LLM, school llm_config, provider columns |
| 0044 | Epic 8 stream layer — nullable `curricula.stream_code`, `students.stream`, `teachers.stream` |
| 0045 | Epic 8 streams registry — `streams` lookup table with 5 system seeds, no FK |
| 0046 | Epic 10 L-1 — per-command RESTRICTIVE write-guard RLS on `curricula` for `owner_type='platform'` rows |
| 0047 | Epic 10 L-3 — `retention_status='archived'` CHECK value + partial index for TTL sweeper |
| 0048 | Hotfix — drop stale RLS policies left on `curriculum_units` / `content_subject_versions` by the L-1 debug draft |
| 0049 | Fix unique index on materialized view `class_summary` |
| 0050 | Epic 12 — `school_adopted_curricula` + `unit_content_active_versions` tables with RLS |
| 0051 | Epic 12 — `unit_content_overrides` append-only version table with RLS |
| 0052 | Epic 13 — per-school theming (`school_theme` table with color palette + logo) |
| 0053 | Epic 15 — `curriculum_backups` table with RLS (scope, status, manifest, retention) |
| 0054 | Epic 15 — `backup_restore_requests` table with RLS (8-state machine, conflict catalog) |
| 0055 | Epic 15 — `schools.backup_cron` column (default `0 2 * * *` nightly at 02:00 UTC) |
| 0056 | Visual library — `visual_library_entries` table (kind, subject, topic_phrase, keywords, s3_path, license, source_unit, embedding) |
| 0057 | Visual library — `embedding` column → pgvector type for cosine similarity search |
| 0058 | Demo request — `name` column on demo lead requests |
| 0059 | Epic/#358 — `teacher_capabilities` table (RLS): additive `curriculum.commission` / `curriculum.review` / `curriculum_mgmt` grants |
| 0060 | Authoring Studio (PR-A) — `authoring_projects`, `authoring_topic_versions`, `authoring_active_versions`, `authoring_snapshots` (platform/admin-scoped, no tenant RLS); extends `curricula.source_type` CHECK with `admin_authored`. Downgrade deletes `source_type='admin_authored'` curricula before reverting the CHECK |
| 0061 | Server-side quiz grading — `progress_sessions.quiz_set` (SMALLINT, nullable, CHECK 1–3). Records which quiz set a session is graded against; `question_id` is `q1…qN` in every set with different answers, so the set must be pinned per session. See pitfall #35 |
| 0062 | Student lesson feedback (#600/#612) — `feedback.message` nullable, `helpful` + `content_type` columns, `feedback_has_content` CHECK. Thumbs-down offers a comment box; a rating with no words is still a valid submission |
| 0063 | #569 — `lesson_views.tutorial_viewed`, so lesson / tutorial / experiment views are distinguishable. The table already carried `experiment_viewed`, written by the end endpoint but never set by any page |
| 0064 | #664 — `password_expires_at` on `teachers` + `students`. Bounds a school-ISSUED temporary password; NULL means no expiry (a user's own password, or an account provisioned before this shipped — backfilling a date would lock them out). Enforced at login only when `first_login` is still TRUE |
| 0065 | #675 — `mv_student_curriculum_progress` rebuilt to union `lesson_views` with `progress_sessions`, so `in_progress` means "reached the unit" rather than "abandoned a quiz" and `not_started` means genuinely untouched. Quiz figures stay quiz-only. Downgrade restores the old MEANING with a sound key — 0003's GROUP BY included subject/grade while its unique index did not, which cannot be rebuilt against real data |
| 0066 | Report alerts — `resolved_at` + partial UNIQUE index on OPEN alerts (school, type, `details->>'unit_id'`). The evaluator's `ON CONFLICT DO NOTHING` had no constraint to act on, so it never deduplicated: 294 rows over 13 units on the demo, one repeated 69×. Also collapses existing duplicates (keeps the earliest, preserving "breaching since"). Partial so a dismissed alert can re-raise |
| 0067 | ADR-008 Phase 1 — `progress_answers.stable_question_id` (nullable) + partial index. `question_id` is `q1…qN` WITHIN a set, so it names a slot, not a question — `GROUP BY question_id` groups questions that merely share an index, which is why the per-answer data already collected (incl. `ms_taken`) cannot be aggregated. Value comes from `src/core/question_identity.py` (content-addressed: `curriculum_id\|unit_id\|lang\|stem`). Pre-migration rows stay NULL and must be EXCLUDED from item analysis, not treated as a group |
| 0068 | ADR-008 Phase 2 — `feedback.stable_question_id` (nullable) + partial index. `feedback` was keyed by unit + content_type, so a student could say "this lesson wasn't helpful" but nobody could say "question 4 is wrong" — the one signal that separates HARD from INCORRECT, and the only one available before a statistic has enough responses to mean anything. The API takes the POSITIONAL id plus the session and resolves the stable id server-side (ownership checked), so a client cannot flag a question it was never served |

---

## Backend: Non-Negotiable Performance Rules

1. **Hot read path touches zero DB queries on cache-warm requests.**
   JWT verify (in-memory) → L1 TTLCache → L2 Redis → only then PostgreSQL.
2. **The FastAPI event loop never blocks.**
   DB: `asyncpg`. Redis: `aioredis`. HTTP: `httpx.AsyncClient`.
   bcrypt and all CPU-bound work: `run_in_executor`.
3. **Audio is never proxied through the API server.**
   `GET /content/{unit_id}/lesson/audio` returns a pre-signed S3/CloudFront URL.
   The client fetches MP3 bytes directly from the CDN.
4. **Progress and analytics writes are fire-and-forget.**
   `POST /progress/answer` and `POST /analytics/lesson/end` dispatch a Celery task
   then return `200 OK` immediately — never await a DB write on the request path.
5. **Connection pools initialised once per worker in the lifespan context.**
   `asyncpg.create_pool(min_size=5, max_size=20)` and `aioredis` pool stored on
   `app.state`. PgBouncer runs in transaction-pooling mode in front of PostgreSQL.
6. **Redis AOF persistence is mandatory in production.**
   `appendonly yes` + `appendfsync everysec`. Without it a Redis restart logs out
   every student and resets all rate-limit counters.
7. **CDN invalidation must accompany Redis cache invalidation on content bumps.**
   Clearing `content:*` keys in Redis is not enough — CloudFront may still serve
   stale JSON for up to 1 hour. Call `cloudfront.create_invalidation` for the
   affected `curricula/{curriculum_id}/{unit_id}/*` paths.

---

## Backend: Non-Negotiable Security Rules

- **All secrets from env vars; never hardcoded.** Use `pydantic-settings`.
  Fail fast at startup if a required secret is missing (no defaults for secrets).
- **Stripe webhook must verify signature first.**
  Call `stripe.Webhook.construct_event(...)` before processing. Reject with 400
  on `SignatureVerificationError`. Log `stripe_event_id` to `stripe_events` table;
  return 200 immediately if already processed (idempotent).
- **Entitlement enforced on the backend only.** The mobile app never decides access.
  It reads the HTTP status code: 200 = serve, 402 = paywall, 403 = not enrolled.
- **`POST /auth/forgot-password` always returns 200** regardless of whether the
  email exists. Returning different responses leaks registered email addresses.
- **Teacher JWTs and student JWTs use separate secrets and separate auth paths.**
  A student JWT must never grant access to teacher/admin endpoints.
- **`attempt_number` is computed server-side** as `COUNT(*) + 1` from prior sessions
  for `(student_id, unit_id, curriculum_id)`. Discard any client-supplied value.
- **COPPA:** there is **no parental-consent flow in the product** (decision
  2026-08-24, #609). StudyBuddy is school-provisioned — schools create student
  accounts — so the applicable route is the school acting as the consent
  authority for an educational service, not a parent-facing form. Do NOT write
  code or copy asserting a consent flow that does not exist. The orphaned
  `/consent` page and its dead client call were removed rather than built.
  Reopening this means deciding on a verification method first; "verifiable
  parental consent" is a legal standard, not an email capture.
- **Rate limiting on all public endpoints.** Auth: 10 req/min per IP.
  Content: 100 req/min per student JWT. Feedback: 5 submissions/student/hour.

---

## Pipeline Rules

- **Pin the Claude model ID** in `pipeline/config.py` (`CLAUDE_MODEL = "claude-sonnet-4-6"`).
  Never use an implicit "latest". Upgrading models is a deliberate act.
- **`max_tokens` must be `16384`** (raised from 8192 on 2026-04-15). Epic 11 C-1/C-2 richer
  prompts (tables + KaTeX) regularly exceed 8192 output tokens, causing mid-string JSON
  truncation. 16K is the conservative headroom; Sonnet 4.6 supports up to 64K. Always set
  `max_tokens=16384` in provider `generate()` methods (`pipeline/providers/anthropic.py`,
  `pipeline/providers/openai.py`).
- **Pipeline is idempotent.** Check `meta.json` at unit start; skip if
  `content_version` matches and all expected files exist. Use `--force` to override.
- **Validate every Claude response** against a JSON schema before writing to the
  Content Store. On `ValidationError`, retry up to 3×; then mark unit as failed and
  continue. Never write malformed content.
- **Spend cap:** abort if `tokens_used × TOKEN_COST_USD > MAX_PIPELINE_COST_USD`
  (default $50). Log and alert.
- **Pipeline jobs triggered via API are async (Celery).** `POST /admin/pipeline/trigger`
  returns `{job_id}` immediately. Status polled via `GET /admin/pipeline/{job_id}/status`.
- **Known issue — `unit_name NOT NULL`:** `curriculum_units` has a `unit_name` NOT NULL
  constraint added in Phase 8. The pipeline's `_upsert_curriculum_units()` must include
  `unit_name` in the INSERT (same value as `title`). If missing, the DB insert silently
  fails (caught and logged as `db_upsert_units_skip`) but content generation continues.
- **After rebuilding the `celery-pipeline` image, always restart the container:**
  `docker compose build celery-pipeline && docker compose up -d celery-pipeline`
- **`celery-pipeline` builds its own image — `docker compose build api` does not rebuild it.**
  Same for `celery-worker` and `celery-beat-primary`. See pitfall #38.

---

## Content Review Workflow

```
Pipeline generates content
  → content_subject_versions row created (status = "pending")
  → files written to Content Store

Admin opens Content Review Queue
  → "Review →" link shown only if has_content = true (files exist on disk)
  → Click Review → version detail page

Version detail page
  → List of units with "View →" links
  → Actions: Approve / Reject / Publish / Rollback / Block unit content
  → "Compare with previous version" link (if version_number > 1)

Unit viewer (/admin/content-review/{version_id}/unit/{unit_id})
  → Left nav: content types (Lesson / Tutorial / Quiz Set 1/2/3 / Experiment)
  → Tutorial: sections rendered as tabs
  → Inline reviewer notes per section/question/step (stored in content_annotations table)
  → Notes use compound key: {unit_id}::{content_type}::{section_id}

Version diff (/admin/content-review/{version_id}/diff)
  → Compare any two versions of the same subject
  → Word-level diff highlighting (green = added, red = removed)
  → Per content type, per field (section heading, question, step)
```

---

## Admin Account Management

Admin accounts use local bcrypt auth (not Auth0). They are stored in `admin_users`.

**Roles:** `developer` · `tester` · `product_admin` · `super_admin`

**Dev setup — create or reset an admin account:**
```bash
# Create initial super admin (run once)
docker compose exec api python scripts/seed_super_admin.py

# Reset password for existing admin
docker compose exec api python scripts/reset_admin_password.py \
  --email your@email.com --password NewPassword123!
```

**Test-only — hard-delete a school account (super-admin/operator):**
`scripts/purge_account.py` completely removes a teacher/student by email (no
soft delete, no archive, no retention) so the email can be re-added via the
admin screens on the next test run. It **deliberately bypasses** ADR-005
Decision 3 (the compliant soft-delete flow) and must never be wired into the
school-admin UI. Dry-run by default; `--commit` to persist. ⚠️ Never run against
real customer/student data — it destroys educational records irrecoverably.
```bash
# Dry-run (rolls back, prints what would go):
docker compose exec api python scripts/purge_account.py --email foo@example.com
# Execute:
docker compose exec api python scripts/purge_account.py --email foo@example.com --commit
```

**Login endpoint:** `POST /api/v1/admin/auth/login` → returns `{ token, admin_id }`
The token is stored in `localStorage` as `sb_admin_token` and sent as `Authorization: Bearer {token}`.

---

## Key Conventions

### Configuration
- Backend: `pydantic-settings`; all env vars. `config.py` is the single import point.
- Mobile: `config.py` holds `BACKEND_URL`, SQLite path, JWT path. No AI keys. No Stripe keys.
- Pipeline: `ANTHROPIC_API_KEY`, `TTS_API_KEY`, `CONTENT_STORE_PATH`, `CLAUDE_MODEL` from env.

### Authentication
**Three-track auth — do not mix tracks:**

| Track | Users | Login endpoint | JWT secret | Token key |
|---|---|---|---|---|
| Auth0 exchange | Self-registered students & teachers | `POST /auth/exchange`, `POST /auth/teacher/exchange` | `JWT_SECRET` (via Auth0 JWKS verify) | `sb_token` / `sb_teacher_token` |
| **Local (school-provisioned)** | School founders, provisioned teachers & students | **`POST /auth/login`** | `JWT_SECRET` | `sb_teacher_token` (teachers/admins), `sb_token` (students) |
| Admin bcrypt | Internal team (developer/tester/product_admin/super_admin) | `POST /admin/auth/login` | `ADMIN_JWT_SECRET` | `sb_admin_token` |

**Local auth flow (Phase A):**
- School founder registers via `POST /schools/register` (requires `password` ≥12 chars). Gets `auth_provider='local'`, `first_login=FALSE`.
- School admin provisions teachers via `POST /schools/{id}/teachers` and students via `POST /schools/{id}/students`. System generates a random default password, emails it, sets `first_login=TRUE`.
- `POST /auth/login` authenticates local users. Response includes `first_login: bool`.
- **`first_login=true` → client MUST redirect to `/school/change-password?required=1` before any portal page renders.** This is enforced in the school portal layout. Never skip it client-side.
- `PATCH /auth/change-password` verifies current password, sets `first_login=FALSE`.
- Password policy: ≥12 chars, ≤72 bytes (bcrypt limit). Validated at schema level.
- Timing-attack prevention: a sentinel bcrypt hash is computed at module import time and burned on unknown-email lookups to prevent email enumeration.

Internal JWT payloads:
- Student (Auth0): `{student_id, grade, locale, role: "student", exp}`
- Student (local): `{student_id, grade, locale, role: "student", account_status, first_login, exp}`
- Teacher (Auth0): `{teacher_id, school_id, role: "teacher|school_admin", exp}`
- Teacher (local): `{teacher_id, school_id, role: "teacher|school_admin", account_status, first_login, exp}`
- Admin: `{admin_id, role: "developer|tester|product_admin|super_admin", exp}`

- Locale is **authoritative from the JWT**. Content endpoints never accept `?lang=`.
- Refresh tokens stored in Redis with TTL (30 days). Admin reset tokens in Redis TTL 1 hr.
- Suspension: Redis `suspended:{id}` set checked in auth middleware after signature verify.
  Auth0 block is synced asynchronously via Celery.

### Logging
```python
from src.utils.logger import get_logger
log = get_logger("component")   # "auth", "content", "pipeline", "subscription", etc.
```
Never use `print()`. Never log passwords, JWT tokens, or Stripe keys.
Backend logs to stdout (captured by container runtime → log aggregation).

### Caching (read order: L1 → L2 → DB)
```
L1  cachetools TTLCache  (per-worker, in-process)  JWT keys · curriculum trees · config
L2  Redis                (shared)                  Entitlement · curriculum resolver · content JSON · rate limits
L3  CloudFront CDN       (global edge)             Audio MP3 · large JSON files
```
Invalidate L2 *and* CDN together on content version bump. Invalidate `ent:{student_id}`
and `cur:{student_id}` on subscription change, school transfer, or curriculum activation.

### Mobile Offline / Sync
- All network calls run in daemon threads. UI callbacks use `@mainthread`.
- Progress + analytics events queued in local SQLite `event_queue` with a UUID `event_id`.
- `SyncManager` flushes queue on app foreground and network restore.
- Backend deduplicates by `event_id` (`ON CONFLICT DO NOTHING`).
- Cache size is bounded by `MAX_CACHE_MB`; LRU eviction when limit is approached.

### i18n
- AI-generated content is already in the correct language — never run it through i18n.
- UI strings only: `web/i18n/en.json` and `mobile/i18n/{lang}.json`. Load at startup; fall back to `en` on missing key.
- Never hardcode user-facing strings in screen files.

---

## Testing

```
Backend : pytest + httpx.AsyncClient
           Mock PostgreSQL: pytest-asyncio + testing.postgresql (no live DB in CI)
           Mock Stripe SDK calls
           Mock Redis: fakeredis or pytest fixture

Web     : Playwright E2E — 120 tests across 4 projects (chromium + persona-student/teacher/admin).
           Runs from host (not container; Chromium glibc vs Alpine musl).
           See `web/tests/e2e/README.md` for the runbook.
           TypeScript type-check via `npm run typecheck`.

Mobile  : pytest for logic only (SyncManager, LocalCache, ProgressQueue, i18n loader)
           No Kivy widget tests in CI

Pipeline: pytest with mocked Anthropic SDK + mocked TTS provider SDK
           Test schema validation logic and idempotency checks
```

**Never** hit a live database, live Redis, or any external API in CI.

### Quiz testing suite (live stack, explicitly invoked)

`backend/quiz_suite/` + `web/tests/e2e/quiz-suite/` are a **separate**, live-stack
suite that runs against a real local dev stack (dev DB, `/data/content`, a running
`api` and `web` container) instead of mocks. It exists to close the gap that let
[#524](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/524) ("Submit
answer" a dead button for every student) ship green — every mocked layer stubbed
the exact seam that broke.

Covers four areas end to end: the full student journey (login → resolve
curriculum → serve quiz → answer → end → history/stats), the #506 anti-cheat
invariants, honest failure surfacing (a real 404 + a real player message, not a
dead button), and a sweep of REAL on-disk quiz content for `correct_option`
values that don't resolve (which silently misgrades students).

It is **excluded from every normal run**, on purpose:
- the API tier is marked `quiz_live` and `backend/setup.cfg`'s `addopts` runs
  with `-m "not quiz_live"`, so plain `pytest -q` never collects it
- the browser tier is an env-gated Playwright project (`QUIZ_SUITE=1`) that
  `npx playwright test` never selects without that variable

Run it explicitly: `./scripts/quiz_suite.sh` (see Running Things below) or the
`/quiz-suite` command. Full design: `docs/superpowers/specs/2026-08-01-quiz-testing-suite-design.md`.

---

## Running Things

```bash
# ── Dev environment ───────────────────────────────────────────────────────────

# Start everything (DB, Redis, migrations, API, Celery, web — all with hot-reload)
./dev_start.sh

# Run automated test suite (no API key or Auth0 needed)
./dev_start.sh test

# Stop background containers
./dev_start.sh stop

# Wipe DB and start fresh
./dev_start.sh reset

# ── Docker Compose — targeted rebuilds ───────────────────────────────────────

# Rebuild and restart a single service (e.g. after changing backend code)
docker compose build api && docker compose up -d api

# Rebuild pipeline worker (e.g. after changing build_unit.py or prompts.py)
docker compose build celery-pipeline && docker compose up -d celery-pipeline

# Rebuild web frontend (e.g. after npm install of a new package)
docker compose build web && docker compose up -d web

# After a requirements.txt change, rebuild ALL FOUR backend services.
# api, celery-worker, celery-pipeline and celery-beat-primary each build their OWN
# image from ./backend — `build api` leaves the three workers on a stale image (pitfall #38).
docker compose build api celery-worker celery-pipeline celery-beat-primary \
  && docker compose up -d api celery-worker celery-pipeline celery-beat-primary

# Verify a new dependency actually landed in every service that imports it:
for s in api celery-worker celery-pipeline celery-beat-primary; do \
  printf "%-22s " "$s"; docker compose exec -T $s python -c "import croniter; print('OK')"; done

# Source-only change needs NO rebuild — all four bind-mount ./backend:/app.
# api hot-reloads via uvicorn --reload; the celery services do not, so restart them:
docker compose restart celery-worker celery-pipeline celery-beat-primary

# Apply pending migrations manually.
# -e TEST_DB_URL= is required: without it env.py targets studybuddy_test, not dev.
docker compose exec -e TEST_DB_URL= api alembic upgrade head

# Check logs for a specific service
docker compose logs celery-pipeline --since 10m -f

# ── Quiz testing suite (live stack; requires ./dev_start.sh already running) ──

# Everything: seed → API tier → browser tier → teardown. ~90s budget.
./scripts/quiz_suite.sh
# Exit codes: 0 pass · 1 genuine test failure · 2 environment problem
#             (stack not up / not healthy — start it with ./dev_start.sh).
./scripts/quiz_suite.sh --api-only        # skip the Playwright tier
./scripts/quiz_suite.sh --browser-only    # skip the pytest tier
./scripts/quiz_suite.sh --keep            # leave the fixture in place for debugging
# Or via the slash command: /quiz-suite

# ── Production-like ───────────────────────────────────────────────────────────

# Backend
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Celery workers
celery -A src.auth.tasks worker -Q pipeline --concurrency=2
celery -A src.auth.tasks worker -Q io,default --concurrency=4
celery -A src.auth.tasks beat

# ── Pipeline ──────────────────────────────────────────────────────────────────

# Seed and build default curriculum (requires ANTHROPIC_API_KEY)
python pipeline/seed_default.py --year 2026
python pipeline/build_grade.py --grade 8 --lang en,fr,es

# Regenerate a single unit
python pipeline/build_unit.py --curriculum-id default-2026-g8 --unit G8-MATH-001 --lang en --force

# Trigger pipeline via API (returns job_id immediately)
curl -X POST http://localhost:8000/api/v1/admin/pipeline/trigger \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"grade": 12, "langs": "en", "force": true, "year": 2026}'
```

---

## Doc Audit (drift checking)

Local toolkit at `scripts/doc_audit/` for catching drift between the repo's
documentation and its actual state. Three checkers ship today (issue #337,
phases A–D):

| Checker | What it catches |
|---|---|
<!-- doc-audit:ignore -->
| `check_link_integrity.py` | Broken `[label](path)` links in any `*.md` file; bare repo-path mentions in prose or inline backticks (e.g. `backend/src/foo.py`) that don't exist on disk |
| `check_migrations_table.py` | Migration files in `backend/alembic/versions/` not listed in this CLAUDE.md table; rows in the table referring to non-existent migrations; numbering gaps |
| `check_test_counts.py` | The `(NNN total)` claim near the latest epic line vs `pytest --collect-only` actual (uses docker compose if local pytest unavailable) |

Run individually or via the orchestrator:

```bash
# Just link integrity:
python3 scripts/doc_audit/check_link_integrity.py --quiet --out drift.json

# Everything; aggregate JSON:
python3 scripts/doc_audit/run_all.py --out drift-report.json

# Skip the slow test-count check:
python3 scripts/doc_audit/run_all.py --skip test_counts
```

Each checker exits 0 (clean) or 1 (drift). The orchestrator's exit code is
the worst of any checker.

### `<!-- doc-audit:ignore -->` marker

A line containing `<!-- doc-audit:ignore -->` suppresses all
link_integrity findings on that line OR the line immediately following.
Use sparingly — for:

- **Historic CHANGES.md entries** — files since renamed/deleted whose references are an accurate frozen record
<!-- doc-audit:ignore -->
- **Aspirational paths in epic specs** — `web/lib/units.ts` etc. referenced before they're built
<!-- doc-audit:ignore -->
- **Known-absent files mentioned by their absence** — e.g. mobile ARCHITECTURE.md notes "no mobile/README.md" as a gap
- **Cross-repo references that resolve in studybuddy-docs** — prefer rewriting as full GitHub URLs; the ignore marker is for cases where the bare path mention is genuinely the right form
<!-- doc-audit:ignore -->
- **Examples in doc-audit's own description** — e.g. the `backend/src/foo.py` placeholder in the table above

Do not use the marker to silence real drift. The convention is
deliberately verbose so it's grep-able for periodic review.

**Out of scope today:** the GitHub Actions nightly workflow + auto-PR for
mechanical sections + `<!-- AUTOGEN:* -->` markers + the Celery Beat
companion task. Those land in the post-#337 successor (#347 to be filed)
once the local toolkit's signal-to-noise has been validated against a
clean main.

---

## Phase Checklist Quick Reference

See [AGENTS.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/AGENTS.md) for the full per-phase checklist. Build in this order:

| Phase | Goal | Key deliverable |
|---|---|---|
| 1 | Backend Foundation | Auth, curriculum endpoints, PgBouncer, Redis pools, health check; all routes under `/api/v1/` |
| 2 | Content Pipeline + English Delivery | `build_grade.py`, content endpoints, entitlement, L1/L2 cache, nginx |
| 3 | Progress Tracking | Session, answer, history endpoints; student dashboard, curriculum map, usage stats, streak counter; result screen |
| 4 | Offline Sync + Multi-language + TTS + Push | SQLite queue, SyncManager, fr/es pipeline, MP3, CloudFront; FCM token registration, `push_tokens`/`notification_preferences` schema, streak/nudge/summary Celery Beat tasks |
| 5 | Subscription + Payments | Stripe checkout, webhook, Redis entitlement cache |
| 6 | Experiment Visualization | Lab detection, experiment JSON, ExperimentScreen |
| 7 | Admin Dashboard + Analytics + Content Review | RBAC (`permissions.py`), content review queue, AlexJS results, annotations, approve/publish/rollback/block, admin API, platform analytics |
| 8 | School & Teacher + Curriculum Upload + Academic Year | XLSX upload, async pipeline trigger, school auth; `promote_student_grades` Celery Beat task, `GRADE_PROMOTION_DATE` config, 30-day grace period for old content |
| 9 | Student–School Association + Routing | Enrolment, curriculum resolver, restrict_access |
| 10 | Extended Analytics + Feedback | Lesson-view timing, attempt tracking, feedback endpoints |
| 11 | Teacher Reporting Dashboard | 6 report types, CSV export, alerts, weekly digest, materialized views |

---

## Top Pitfalls

1. Mobile/web app calling Anthropic directly — it has no API key and must never do this.
2. Blocking the async event loop — use asyncpg, aioredis, httpx; wrap bcrypt in executor.
3. Proxying audio through FastAPI — return a pre-signed URL; never stream MP3 bytes.
4. Progress writes blocking the student response — Celery fire-and-forget only.
5. Not sizing connection pools relative to worker count — deploy PgBouncer; set `max_connections ≥ 200`.
6. Clearing Redis cache but not the CDN — invalidate both together on content version bump.
7. Redis without AOF persistence — all sessions lost on restart.
8. Accepting Stripe webhooks without signature verification — always `construct_event` first.
9. No idempotency on the Stripe webhook handler — dedup by `stripe_event_id`.
10. Entitlement gating in the mobile app — backend is the sole source of truth (HTTP status codes).
11. Locale as a query parameter — locale comes from the JWT only, never from request params.
12. `attempt_number` trusted from client — always compute server-side from DB count.
13. Teacher JWT accepted on student endpoints (and vice versa) — separate secrets + role checks.
14. Pipeline not idempotent — check `meta.json` content_version before generating; use `--force` to override.
15. XLSX parse errors surfaced as 500 — return HTTP 400 with per-row structured error list.
16. `max_tokens=4096` or `8192` in pipeline — content with Epic 11 tables + KaTeX regularly exceeds 8192. Always use `16384` in both `pipeline/providers/anthropic.py` and `pipeline/providers/openai.py`.
17. Reading `localStorage` during SSR in Next.js — initialise as `null`, populate in `useEffect`.
18. Missing migration after pull — API throws `UndefinedColumnError`; run `alembic upgrade head`.
19. Rebuilding a Docker image without restarting the container — old image stays running; always `up -d` after `build`.
20. `unit_name NOT NULL` in `curriculum_units` — include `unit_name` in pipeline INSERT or the row silently fails.
21. Roster upload uses `{students: [{email, grade?, teacher_id?}]}`, NOT `{student_emails: [...]}` — the old flat list format was removed in migration 0024.
22. Grade self-change blocked for school-enrolled students — `PATCH /student/profile` returns 403 on `grade` if `students.school_id IS NOT NULL`. Grade is set exclusively via `PUT /schools/{school_id}/students/{student_id}/assignment`.
23. **`login_local_user` must stamp `app.current_school_id='bypass'` before querying** — the RLS policy (migration 0028) hides all teacher/student rows when this is not set. Always acquire a pool connection and call `set_config` before the SELECT. Never use `pool.fetchrow()` directly on RLS-protected tables in an unauthenticated context.
24. **`first_login=true` must block navigation at the portal layout level** — not just on the login page. A user who navigates directly to `/school/dashboard` after receiving a token with `first_login=true` must still be redirected to `/school/change-password?required=1`. Check the decoded JWT in the layout `useEffect`, not only in the login handler.
25. **Parallel pipeline runs race on `meta.json`** — firing `build_grade.py --force` via `docker exec` while a Celery trigger is also running for the same curriculum causes unit-level collisions (one writes meta, the other's idempotency check races, some units fail). For manual runs, confirm no `pipeline_jobs` row with `status IN ('queued','running')` for that curriculum_id first.
26. **Playwright Chromium cannot run in the Alpine `web` container** — the binary is glibc-linked; Alpine is musl. Error: `symbol not found: __memset_chk`. Run `npx playwright test` on the host from `web/` directory. Browsers install to `~/.cache/ms-playwright/`. See `web/tests/e2e/README.md`.
27. **Alembic migrations that fail mid-upgrade can leave orphan state** — the L-1 debug draft of migration 0046 enabled RLS + policies on `curriculum_units` and `content_subject_versions` before it was rewritten to Option 3 (curricula-only). The shipped migration didn't drop the orphans; hotfix migration 0048 cleaned them up. When iterating on a migration, always run a full downgrade → upgrade cycle against a fresh DB before committing to catch orphan state.
28. **Pipeline CLI connections must set `app.current_school_id='bypass'`** — same root cause as pitfall #23, different entry point. Since Epic 10 L-1 (migration 0046) added RESTRICTIVE RLS on `curricula` for `owner_type='platform'` rows, `pipeline/build_grade.py` and `pipeline/seed_default.py` running against a real DB silently fall back to "no DB" mode (logged as `db_connect_skip: new row violates row-level security policy "no_write_platform_curricula_insert"`). Content files still get written to `/data/content`, but `curricula`, `curriculum_units`, and `content_subject_versions` rows never appear — leaving the admin review queue blind. Any code path that opens an asyncpg connection for platform-owner writes must `await conn.execute("SET app.current_school_id = 'bypass'")` immediately after connect.
29. **Pipeline `content_subject_versions.published_at` must be a `datetime` instance, not a string** — `pipeline/build_grade.py::_upsert_content_subject_version` uses `_now_iso()` (which returns a string) for the `published_at` column when `REVIEW_AUTO_APPROVE=true`. asyncpg fails the INSERT with `invalid input for query argument $N: '...iso string...' (expected a datetime.date or datetime.datetime instance, got 'str')` and the broad `except` logs `db_csv_upsert_skip`. Net effect: content files land on disk but zero `content_subject_versions` rows appear. Use `datetime.now(tz=timezone.utc)` for this column (and any other TIMESTAMPTZ asyncpg binding). Keep `_now_iso()` for JSON serialisation only.
30. **Pipeline `_upsert_curriculum_units` must include `unit_name`** — Phase-8 schema added `unit_name NOT NULL` to `curriculum_units`, but the pipeline's INSERT only passed `title`. Net effect: every row insert fails with `null value in column "unit_name"` logged as `db_upsert_units_skip`, and no `curriculum_units` rows are created for any new curriculum built via CLI — admin review UI shows empty unit lists even though content is on disk. Fix: pass `title` as both `title` and `unit_name` in the INSERT for platform-seeded curricula (was [issue #249](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/249)).
31. **`get_curriculum_tree` must use the full 3-step resolver and load units from DB** — the original implementation called `_load_grade(grade)` which reads `grade{N}_stem.json` and ignores the resolved `curriculum_id`. Stream students (G11 Science, G11 Commerce, G12 Science, G12 Commerce) saw STEM subjects/units instead of their actual stream content. Fix: use the same 3-step resolver (school-owned → classroom packages RLS bypass → STEM fallback) as `content/service.py::resolve_curriculum_id`, then query `curriculum_units` WHERE `curriculum_id = $resolved`. JOIN `content_subject_versions` for the human-readable `subject_name`.
32. **`curriculum_units.subject` stores subject codes, not display names for stream curricula** — platform stream curricula (G11-science, G12-commerce, etc.) seed `subject` as abbreviated codes (`G11-PHYS`, `G12-ACC`). The human-readable names (`Physics`, `Accountancy`) live in `content_subject_versions.subject_name`. In `get_curriculum_tree`, use `COALESCE(MAX(csv.subject_name), cu.subject)` joined on `(curriculum_id, subject)` to get display names; fall back to the raw code for newly-seeded curricula with no CSV rows.
33. **`build_lesson_prompt` must generate a `sections` array** — the old schema produced only `synopsis`/`learning_objectives`/`reading_level` (3 sparse fields). Students saw "Overview and Learning Objectives but no lesson body." The new schema requires `sections` (Introduction, Core Concepts, Worked Examples, Real-World Applications, Summary) and `key_points`. `_normalize_lesson` handles three formats: old-format (has `title`), new rich (has `sections`), and legacy minimal (pre-C5-regen content that has only `synopsis`). Do not run C-5 regen until the new prompt is in place.
34. **`docker compose exec api alembic upgrade head` migrates the TEST database, not dev** — the `api` service sets `TEST_DB_URL`, and `alembic/env.py` prefers it over `DATABASE_URL`. The command reports success, `alembic current` says `head`, and the dev DB is untouched — a nastier variant of pitfall #18, because it strikes *after* you ran the migration. Always pass `-e TEST_DB_URL=`. `env.py` now prints the target database on every run; read that line before trusting the result. (`docker-compose.yml` already blanks the var for the `migrate` service, which is why `./dev_start.sh` is unaffected.)
35. **Never trust the client for quiz grading** — `POST /progress/answer` and `/end` once accepted `correct: bool` and `score: int` and stored them verbatim, while the quiz payload shipped `correct_option` for every question: a student could read the answers from the network tab and post themselves a perfect score. Grading is now server-side (`get_quiz_answer_key` → the content store), the answer key is stripped from the served quiz (`_strip_answer_key`), and the score is a Redis tally of server-graded answers. Two consequences to preserve: (a) `question_id` is `q1…qN` in **every** quiz set with **different** answers per set, so the graded set must be pinned per session (`quizset:{session_id}`, `progress_sessions.quiz_set`) — resolving it from the per-unit rotation pointer at answer time grades later answers against the wrong key; (b) answer writes are fire-and-forget, so `end_session` **cannot** count `progress_answers` (rows may not exist yet) — that race is why the score is tallied in Redis.
36. **Placeholder content must never reach a student** — `scripts/seed_dev_content.py` and `scripts/setup_dev.py` backfill missing units with stub lessons/quizzes ("Sample question 1 about X?", options "Option A"…"Option D", correct answer always "A") tagged `model: "dev-placeholder"`. They only write where a file is *absent*, so any unit the pipeline hasn't generated keeps its stub indefinitely and used to be served as if real — students were graded on fiction. `get_content_file` now refuses `dev-placeholder` content on both the store and cache paths, so an ungenerated unit 404s honestly. Do not "fix" a 404 by re-running the seeder.
37. **`-e TEST_DB_URL=` is REQUIRED for alembic and FORBIDDEN for pytest — the two rules are opposite, and conflating them destroyed the dev database on 2026-08-01.** Pitfall #34 already covers the alembic side: without `-e TEST_DB_URL=`, `alembic upgrade head` silently migrates `studybuddy_test` instead of dev. But `backend/tests/conftest.py` defines a session-scoped autouse `run_migrations` fixture that ends in `command.downgrade(cfg, "base")` — dropping every table — and that fixture is normally safe only because it targets `studybuddy_test`. Passing `-e TEST_DB_URL=` to a **pytest** invocation blanks the variable, `backend/alembic/env.py` falls back to `DATABASE_URL`, and the downgrade-to-base runs against the **dev** database instead — which is exactly what happened, wiping 30 `@riverside.demo` students, 1 school, and 15 curricula. This is why `backend/quiz_suite/` lives as a **sibling** of `backend/tests/`, not a subdirectory of it: living outside `backend/tests/` means that conftest's autouse fixture can never apply to it, no matter how it's invoked. Never pass `-e TEST_DB_URL=` to any `pytest` command, full stop — including `scripts/quiz_suite.sh`'s internal `docker compose exec` calls, which deliberately omit it.
38. **`docker compose build api` does NOT rebuild the Celery workers — they build their own images.** `api`, `celery-worker`, `celery-pipeline` and `celery-beat-primary` each declare a separate `build:` block over the same `./backend` context, so Compose produces four independent images (`studybuddy_ondemand-api`, `…-celery-worker`, …). Rebuilding only `api` leaves the three workers running whatever image they were last built from — on 2026-08-17 the `celery-worker` image was **3 months old**, missing `croniter` (added to `requirements.txt` for the #527 per-school backup schedule), so any task importing it died with `ModuleNotFoundError: No module named 'croniter'` while `api` imported it fine. The failure is easy to misread because all four **bind-mount `./backend:/app`**: *source* edits are shared instantly (so code changes look like they propagate), but the site-packages layer comes from each service's own image, so *dependency* changes do not. Rule: source change → no rebuild (restart the workers; only `api` hot-reloads). `requirements.txt` change → rebuild all four, then verify with `docker compose exec -T <svc> python -c "import <pkg>"` per service rather than trusting the build log. Pitfall #19 is the adjacent trap (rebuilt but not restarted); this one is "restarted, but never rebuilt".

39. **`npm run typecheck` silently reports NOTHING while the dev server is running — and filtering the `.next/` lines turns that into a false green.** Next writes `.next/dev/types/routes.d.ts` and `validator.ts` incrementally, and a partially-written file is a *syntax* error (`TS1005`, `TS1109`, `TS1128`). `tsconfig.json` explicitly `include`s `.next/dev/types/**/*.ts`, so tsc parses them, aborts before semantic analysis, and never reports a single error in `app/` — no matter how broken it is. `exclude` does not help: `include` wins. This shipped a red deploy on 2026-08-31 — a page used a field its type lacked, local "typecheck" was clean, and CI's `npm run build` caught it inside the Docker image build. **Before trusting a typecheck: `docker compose stop web`, remove `.next` (it is owned by the container's root — `docker run --rm -v "$PWD/web:/w" alpine rm -rf /w/.next`), then run `npx tsc --noEmit`.** A local `npm run build` is not a substitute — it dies with `EACCES` on `.next/trace-build` for the same ownership reason. Never dismiss `.next/` errors as generated noise; they suppress everything else.

40. **`web/lib/api/*.ts` hand-writes its DTOs — they do NOT derive from `lib/api/types.gen.ts`.** `reports.ts` alone declares 24 interfaces and imports nothing from the generated file. So regenerating the OpenAPI contract updates `types.gen.ts` and leaves the types the pages actually import untouched: adding a field to an API response means editing **both**, and the pages import the hand-written one. This is the other half of the 2026-08-31 red deploy — the generated `AlertItem` had `unit_title`, the hand-written one did not, and `alerts/page.tsx` imports the latter.

41. **Two pytest runs against the `api` container destroy each other — and the wreckage outlives the run that caused it.** `backend/tests/conftest.py`'s session-scoped autouse `run_migrations` fixture ends in `command.downgrade(cfg, "base")`, dropping every table in `studybuddy_test`. That is safe for ONE session and catastrophic for two: whichever finishes first drops the schema out from under the other. Pitfall #37 covers the `-e TEST_DB_URL=` half of this; the mechanism is broader, and no flag is needed to trigger it. On 2026-09-02 a full suite was launched in the background and a "quick" targeted run started while it was still going — 129 failures. A second full suite was then started before the first had actually exited (its completion notice arrived later) — 387 failures. The next run inherited a database with **no `alembic_version` row and one table** and reported 235 failures with nothing else running, which read exactly like a genuine regression: every failure was an `asyncpg` error, each failing test passed in isolation, and the same code was green in CI. One clean cycle (whose own teardown reset the schema) repaired it, and the control run was 1466/0. Rules: **never run pytest while another pytest is running against that container** — in this repo pytest is a write operation, not an observation, so "let me just check one file while that finishes" is the trap; checking `ps`/"is anything running now?" proves nothing, because the damage is at rest in the database rather than in a live process; and when a suite fails en masse, re-run it ALONE from a clean state before believing the number. Use `--tb=line` or `--tb=short` — a `-q` mass failure is nearly undiagnosable after the fact.

---

## Content Rules

These rules apply to all AI-generated content (lessons, quizzes, experiments, audio scripts)
and to all student-facing UI copy. They are non-negotiable.

1. **Age-appropriate:** No violence, profanity, or suggestive themes. All content targets Grades 5–12.
2. **Inclusive language:** Use gender-neutral phrasing (e.g., "the engineer", "they"). Do not use
   gendered emoji to represent professional roles in diagrams or examples.
3. **Reading level:** AI-generated lesson content must target 1–2 grade levels below the student's
   actual grade to ensure comprehension accessibility.
4. **STEM clarity:** Use Mermaid.js diagrams for flowcharts. Explain maths step-by-step.
5. **Student-facing error messages** must be age-appropriate and non-technical. Never expose stack
   traces, HTTP status codes, or internal identifiers in any message visible to students.
6. **PSA language (Accessibility AI):** Emergency notification content must use plain language
   (Flesch-Kincaid Grade 8 or below), be multi-channel (text + audio + visual), and be compatible
   with screen readers.

---

## Compliance — COPPA & FERPA

### COPPA (Children's Online Privacy Protection Act)
Applies to students under 13 in US distribution.

- **Not implemented:** there is no parental-consent capture in the product, and
  no `account_status` gate tied to consent (#609, decided 2026-08-24). Accounts
  are created by schools. If this is revisited, the verification method is the
  design question, not the endpoint.
- Public copy must not claim a consent flow exists. See the note in
  `docs/PENDING_DECISIONS.md`.
- Collect only minimum necessary PII: name, email, grade, locale.
- No tracking, location data, or behavioural fingerprinting of minors.

### FERPA (Family Educational Rights and Privacy Act)
Applies to educational records of students at schools receiving US federal funding.

- Parents (or eligible students aged 18+) have the right to inspect and review educational records.
- Schools must obtain written consent before disclosing student educational records to third parties.
- Student progress records, quiz scores, and lesson-view history are educational records under FERPA.
- Admin and teacher endpoints that expose student records must be scoped to the student's own
  institution and require a `teacher` or `school_admin` JWT. Never cross school boundaries.
- Default to not sharing directory information without explicit consent, even where technically
  permitted.

---

## Accessibility Standards

- UI (mobile and web) must target **WCAG 2.1 Level AA**.
- Minimum colour contrast ratio: 4.5:1 for normal text, 3:1 for large text.
- All interactive elements must have accessible labels (content descriptions on Android,
  `aria-label` on web).
- Audio content must have text alternatives.
- PSA Notification AI: must support TalkBack (Android), VoiceOver (iOS), and high-contrast mode.

---

## Data & Privacy Rules

- **No real student PII in dev or test environments.** Use synthetic data generators.
  CI must never connect to production databases.
- **Data minimisation:** Collect only name, email, grade, locale. No device ID, location,
  or behavioural fingerprinting.
- **Retention:** Progress records retained for the lifetime of the account, then anonymised
  (strip `student_id`) after deletion — 30-day GDPR schedule.
- **AI-generated content is never the output of the student.** Do not attribute AI content
  to the student or store it as their work product.

---

## Technical Preferences

- **Primary languages:** Python (backend / pipeline) · TypeScript/React (web) · Kotlin (Android).
- **Cloud:** Architecture decisions must remain cloud-agnostic where possible. Abstract storage
  behind an interface; avoid vendor-specific SDK lock-in in business logic.
- **Content moderation:** AlexJS is the current automated content analysis tool (pipeline phase).
  Azure AI Content Safety and other commercial options are deferred until AlexJS proves insufficient
  or a specific cloud platform is adopted.
- **Async pattern:** Kotlin Coroutines for all async operations on Android; no callbacks or blocking
  calls on the main thread.
- **Dependencies:** New dependencies must be reviewed for known CVEs before inclusion.
  After `npm install`, also run `docker compose exec web npm install` so the running container
  picks up the new package without a full rebuild.
