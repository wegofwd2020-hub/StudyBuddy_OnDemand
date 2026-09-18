# StudyBuddy OnDemand — CLAUDE.md

Backend-powered AI education platform for Grades 5–12. StudyBuddy is the
information bridge between classroom lessons and the current world. Students
get instant pre-generated content (lessons, quizzes, audio) in English, French,
and Spanish — no Anthropic API key required on the client. Schools and teachers
can upload custom curricula. Subscription-based.

---

## Positioning

StudyBuddy has two framings. Full decision log in
[`docs/BRANDING_TAGLINE_OPTIONS.md`](docs/BRANDING_TAGLINE_OPTIONS.md).

### Consumer framing — "information bridge"

- **Tagline:** *"Lessons, always current."*
- **Sub-headline:** *"AI-powered lessons, quizzes, and tutorials — your bridge from classroom to a world that won't sit still."*

Use for: landing page, emails, help-widget responses, marketing pages.

### Engineering mental model — "scoped retrieval over the world of knowledge"

Every content generation is a **scoped query** parametrised by six dimensions:

| Scope dimension | What it enforces |
|---|---|
| Topic / subject / unit | Curriculum alignment |
| Grade | Reading level, conceptual depth, age-appropriateness |
| Language | en / fr / es / vernacular |
| Curriculum context | What the student has already covered |
| Format | Lesson / quiz / tutorial / experiment |
| Real-world framing | Connect to something current the student recognises |

The LLM is the commodity. The **scoping layer** is the product IP.

### Audience translation matrix

| Audience | Use which framing |
|---|---|
| Parents, students, teachers, school admins | Information bridge |
| Developers, architects, internal technical discussions | Scoped retrieval |
| VCs / B2B pitch decks | Scoped retrieval first (30 sec), then bridge metaphor |

**Load-bearing word:** Tagline uses **"current"** — do not swap for "today's", "latest", or any dated alternative. "Today's" breaks at Phase 2/3; "current" is evergreen across all phases.

---

## Project Status

**Phases 1–11 complete. Phase A (local auth) shipped. Phases B–E complete. Epic 1 complete. Epic 8 H-8/H-9/H-10 shipped. Epic 10 L-1 through L-5 + L-7 + L-8 shipped. Epic 11 C-1 through C-6 + C-9 shipped; C-5 in progress. Epic 12 TA-0 through TA-4 shipped. Epic 15 BR-1 through BR-6 complete. Epic 16 S-1 through S-5 shipped.**

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
| Phase A — Local Auth | ✅ Complete (678 tests) |
| Phase B — Classrooms | ✅ Complete (migration 0038, 21 tests) |
| Phase C — Curriculum Catalog | ✅ Complete (6 tests) |
| Phase D — Curriculum Builder | ✅ Complete (migration 0039, 19 tests) |
| Phase E — Pipeline Billing | ✅ Complete (10 tests) |
| Epic 1 — Multi-Provider LLM Pipeline | ✅ Complete (migration 0043, 19 tests) |
| Epic 8 H-8/9/10 — Stream layer + registry | ✅ Complete (migrations 0044–0045, 18 tests) |
| Epic 10 L-1…L-5 + L-7 + L-8 — Curriculum lifecycle | ✅ Complete. L-6 sweeper paused; L-9/L-10 pending. |
| Epic 11 C-1…C-4, C-6, C-9 — Content formatting | ✅ Pipeline + renderer complete. C-5 regen in progress; C-7/C-8 pending. |
| Epic 12 TA-0…TA-4 — School curriculum library | ✅ Backend + web complete (migrations 0050–0051; 27 tests). |
| Epic 15 BR-1…BR-6 — Curriculum backup & restore | ✅ Complete (migrations 0053–0055; 27 tests). |
| Epic 16 S-1…S-5 — Public site redesign | ✅ Complete. |

**See git log / CHANGES.md for shipped feature history.**

**Active branch:** `main` (next: see `docs/epics/` — product backlog)

**Open tasks:**
- See `docs/epics/` for the full product backlog (11 epics; see `INDEX.md`)
- Epic 2 — Production launch & demo readiness (hosting blocker)
- Epic 3 — Student mobile app (Expo/RN; parked behind testing + hosting)
- Epic 4 — Parent portal
- Epic 5 — District admin
- Epic 6 — Platform hardening
- Epic 10 — L-6 TTL sweeper paused; L-9/L-10 pending
- Epic 11 — C-5 regen in flight; C-7/C-8 pending
- Epic 15 — BR-DOC-1/BR-DOC-2 lower priority
- Tracked: #188 e2e school→pipeline→student; #189 a11y debt

---

## Document Map

Before writing any code, read these in order. All documentation has moved to **[studybuddy-docs](https://github.com/wegofwd2020-hub/studybuddy-docs)**.

| Doc | Read when |
|---|---|
| [ARCHITECTURE.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/ARCHITECTURE.md) | First — system design, data models, API contracts, all phases |
| [BACKEND_ARCHITECTURE.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/BACKEND_ARCHITECTURE.md) | Before touching backend — caching, hot path, SLOs, deployment |
| [UX_GOALS.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/UX_GOALS.md) | Before any UI/UX work |
| [REQUIREMENTS.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/REQUIREMENTS.md) | Check requirement ID + status before implementing |
| [AGENTS.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/AGENTS.md) | Conventions, layer rules, 35 pitfalls, phase-by-phase checklists |
| [CHANGES.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/CHANGES.md) | Design decisions log and pending work items |
| [OPERATIONS.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/OPERATIONS.md) | Runbooks, incident response, disaster recovery, deployment |
| [CLOUD_HOSTING.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/CLOUD_HOSTING.md) | Cloud-hosting shopping list |
| [OBSERVABILITY.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/OBSERVABILITY.md) | Local Grafana + Prometheus setup |
| [CHEATSHEET.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/CHEATSHEET.md) | Operator one-liners |
| [SCALABILITY.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/SCALABILITY.md) | Capacity planning, multi-region, load testing |
| [GLOSSARY.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/GLOSSARY.md) | Acronym and term definitions |

> **Sibling / spun-out projects:** the standalone non-school products moved to **Mentible** (`StudyBuddy_SelfLearner`). Don't build those here. **MarketingTools** (`wegofwd2020-hub/MarketingTools`) is the cross-portfolio promo repo.

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
      reset_admin_password.py
      seed_super_admin.py
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
                            observability.py  ← Prometheus metrics, health probes, correlation ID middleware
                            events.py         ← emit_event() structured log · write_audit_log() Celery dispatch
    tests/               ← pytest; ALL external calls mocked; no live DB in CI
    quiz_suite/          ← live-stack quiz testing suite (pytest, marker: quiz_live); SIBLING of tests/
    requirements.txt

  web/                   ← Next.js 15 app (admin console + public pages)
    app/
      (admin)/           ← admin-only routes (JWT-gated); no SSR — all "use client"
      (public)/          ← public-facing pages
      (student)/         ← student portal (Auth0-gated)
      (school)/          ← school/teacher portal (Auth0-gated)
    components/
      layout/            ← PortalHeader · PortalFooter · AdminNav
    lib/
      api/               ← admin.ts · demo.ts · client.ts (Axios instances per role)
      hooks/             ← useAdmin · useTeacher · useDemoStudent · useDemoTeacher
    i18n/                ← en.json

  mobile/
    main.py              ← Kivy entry; thin client; version check on startup
    src/
      api/               ← async HTTP client (httpx)
      ui/                ← Kivy screens
      logic/             ← SyncManager · LocalCache · ProgressQueue · CurriculumResolver

  pipeline/
    build_grade.py       ← CLI: --grade N --lang en,fr,es [--force] [--dry-run]
    build_unit.py        ← CLI: --curriculum-id UUID --unit G8-MATH-001 --lang en
    seed_default.py      ← CLI: --year 2026
    tts_worker.py        ← lesson text → MP3
    prompts.py           ← prompt builders
    config.py            ← ANTHROPIC_API_KEY · TTS_API_KEY · CONTENT_STORE_PATH · CLAUDE_MODEL

  data/                  ← grade5_stem.json … grade12_stem.json
  docs/                  ← additional design documents
```

---

## Web Frontend — Tech Stack

| Layer | Choice |
|---|---|
| Framework | Next.js 15 (App Router) |
| Styling | Tailwind CSS v4 — config in `globals.css` via `@import "tailwindcss"`, **no `tailwind.config.js`** |
| Data fetching | TanStack React Query v5 |
| HTTP client | Axios — separate instances per role in `lib/api/client.ts` and `lib/api/admin-client.ts` |
| Markdown rendering | `react-markdown` + `remark-gfm` |
| Icons | `lucide-react` |
| Auth | Admin: local JWT `sb_admin_token`. Students/Teachers: Auth0 |

**Critical Tailwind v4 note:** No `tailwind.config.js`. Plugins via `@plugin` in `globals.css`. `prose` requires `@plugin "@tailwindcss/typography"`.

**Hydration rule:** Never read `localStorage` during SSR. Always initialise as `undefined`/`null` and populate in `useEffect`.

---

## Admin Console — Route Map

All admin routes require valid `sb_admin_token` JWT; unauthenticated → redirect to `/admin/login`.

| Route | Purpose |
|---|---|
| `/admin/login` | Local bcrypt login → issues JWT |
| `/admin/` | Dashboard — subscription analytics, system health, CI status |
| `/admin/content-review` | Review queue (filterable by status) |
| `/admin/content-review/[version_id]` | Version detail — units, annotations, actions |
| `/admin/content-review/[version_id]/unit/[unit_id]` | Unit content viewer |
| `/admin/content-review/[version_id]/diff` | Side-by-side version diff |
| `/admin/pipeline` | Pipeline job list |
| `/admin/pipeline/[job_id]` | Job detail |
| `/admin/pipeline/upload` | Upload grade JSON |
| `/admin/demo-accounts` | Manage demo student accounts |
| `/admin/demo-teacher-accounts` | Manage demo teacher accounts |
| `/admin/feedback` | Student feedback list |
| `/admin/audit` | Audit log |
| `/admin/authoring` | Authoring Studio — project list (super_admin only) |
| `/admin/authoring/[projectId]` | Authoring workspace |

---

## Three Runtime Contexts

These are completely independent at runtime. Never mix their concerns.

```
1. Content Pipeline  (offline, operator-run)
   CLI/Celery → Anthropic API + TTS → Content Store (S3 or filesystem)

2. Backend API  (always-on server)
   FastAPI + uvicorn → PostgreSQL + Redis + Content Store

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

backend/src/content/      → backend/src/core/
backend/src/progress/     → backend/src/core/
backend/src/subscription/ → backend/src/core/
backend/src/school/       → backend/src/core/
backend/src/analytics/    → backend/src/core/
backend/src/admin/        → backend/src/content/, backend/src/curriculum/,
                             backend/src/subscription/

pipeline/                 → prompts.py, Anthropic API, TTS API, Content Store
```

---

## Content Store Layout

```
{CONTENT_STORE_PATH}/
  curricula/
    {curriculum_id}/
      {unit_id}/
        lesson_en.json      quiz_set_1_en.json   tutorial_en.json
        lesson_fr.json      quiz_set_2_en.json   experiment_en.json
        lesson_en.mp3       quiz_set_3_en.json   meta.json
```

`meta.json` per unit: `{generated_at, model, content_version, langs_built: []}`.

---

## Database Migrations (Alembic)

Migrations live in `backend/alembic/versions/`, numbered `0001_…` → `000N_…`.

- **Never skip a migration.** Run `alembic upgrade head` after pulling.
- **In Docker:** migrations run automatically via `migrate` service on `./dev_start.sh`
- **Manual run:** `docker compose exec -e TEST_DB_URL= api alembic upgrade head`
  ⚠️ `-e TEST_DB_URL=` is **required** — without it, env.py targets `studybuddy_test` (pitfall #18/#34).

| # | Description |
|---|---|
| 0001–0011 | Phase 1–11 schema |
| 0012–0029 | Demo accounts, pipeline jobs, school/teacher, RLS, local auth (Phase A) |
| 0030–0036 | AlexJS acks, at-risk tracking, build allowance, credits, teacher subscriptions |
| 0037–0043 | Phase A local auth, B classrooms, C catalog, D definitions, E billing, Epic 1 multi-provider LLM |
| 0044–0048 | Epic 8 stream layer, Epic 10 L-1 archive RLS (+ 0048 hotfix) |
| 0049–0055 | Epic 12 school library, Epic 13 theming, Epic 15 backup/restore |
| 0056 | Visual library — `visual_library_entries` table |
| 0057 | Visual library — `embedding` → pgvector for cosine similarity |
| 0058 | Demo request — `name` column on demo lead requests |
| 0059 | Epic/#358 — `teacher_capabilities` table (RLS): additive curriculum grants |
| 0060 | Authoring Studio (PR-A) — `authoring_projects`, `authoring_topic_versions`, `authoring_active_versions`, `authoring_snapshots`; extends `curricula.source_type` CHECK with `admin_authored` |
| 0061 | Server-side quiz grading — `progress_sessions.quiz_set` (SMALLINT, nullable, CHECK 1–3) |
| 0062 | Student lesson feedback — `feedback.message` nullable, `helpful` + `content_type` columns, `feedback_has_content` CHECK |
| 0063 | `lesson_views.tutorial_viewed` — distinguishes lesson/tutorial/experiment views |
| 0064 | `password_expires_at` on teachers + students — bounds school-issued temporary passwords; NULL = no expiry |
| 0065 | `mv_student_curriculum_progress` rebuilt to union `lesson_views` with `progress_sessions` |
| 0066 | Report alerts — `resolved_at` + partial UNIQUE index on OPEN alerts; collapses existing duplicates |
| 0067 | ADR-008 Phase 1 — `progress_answers.stable_question_id` + partial index; content-addressed via `question_identity.py` |
| 0068 | ADR-008 Phase 2 — `feedback.stable_question_id` + partial index; resolved server-side from positional id + session |
| 0069 | ADR-008 Phase 3a — `quiz_questions` registry keyed by stable_question_id; enables drawing 8 from ~24 distinct questions |
| 0070 | `student_stuck_on_unit` alert type; `stuck_attempts_threshold`; SPLITS dedup index from 0066 |
| 0071 | `inactive_students` alert; `uq_report_alerts_open_inactive` keyed on (school, student); removes unused threshold columns |

---

## Backend: Non-Negotiable Performance Rules

1. **Hot read path touches zero DB queries on cache-warm requests.**
   JWT verify (in-memory) → L1 TTLCache → L2 Redis → only then PostgreSQL.
2. **The FastAPI event loop never blocks.**
   DB: `asyncpg`. Redis: `aioredis`. HTTP: `httpx.AsyncClient`. bcrypt: `run_in_executor`.
3. **Audio is never proxied through the API server.**
   `GET /content/{unit_id}/lesson/audio` returns a pre-signed S3/CloudFront URL.
4. **Progress and analytics writes are fire-and-forget.**
   Dispatch Celery task then return `200 OK` — never await a DB write on the request path.
5. **Connection pools initialised once per worker in the lifespan context.**
6. **Redis AOF persistence is mandatory in production.**
   `appendonly yes` + `appendfsync everysec`.
7. **CDN invalidation must accompany Redis cache invalidation on content bumps.**
   Call `cloudfront.create_invalidation` for affected paths.

---

## Backend: Non-Negotiable Security Rules

- **All secrets from env vars; never hardcoded.** Fail fast at startup if missing.
- **Stripe webhook must verify signature first.** `stripe.Webhook.construct_event(...)` before processing.
- **Entitlement enforced on the backend only.**
- **`POST /auth/forgot-password` always returns 200** regardless of email existence.
- **Teacher JWTs and student JWTs use separate secrets and separate auth paths.**
- **`attempt_number` is computed server-side** as `COUNT(*) + 1`.
- **COPPA:** No parental-consent flow — school-provisioned accounts only (decided 2026-08-24, #609).
- **Rate limiting on all public endpoints.** Auth: 10 req/min per IP. Content: 100 req/min per student JWT.

---

## Pipeline Rules

- **Pin the Claude model ID** in `pipeline/config.py` (`CLAUDE_MODEL = "claude-sonnet-4-6"`).
- **`max_tokens` must be `16384`** (raised 2026-04-15). Set in `pipeline/providers/_wegofwd_adapter.py`.
- **Pipeline is idempotent.** Check `meta.json` at unit start; use `--force` to override.
- **Validate every Claude response** against JSON schema before writing. Retry up to 3×.
- **Spend cap:** abort if `tokens_used × TOKEN_COST_USD > MAX_PIPELINE_COST_USD` (default $50).
- **Pipeline jobs triggered via API are async (Celery).** `POST /admin/pipeline/trigger` returns `{job_id}`.
- **After rebuilding `celery-pipeline`, always restart:** `docker compose build celery-pipeline && docker compose up -d celery-pipeline`
- **`celery-pipeline` builds its own image — `build api` does not rebuild it.** (pitfall #38)

---

## Content Review Workflow

```
Pipeline generates content
  → content_subject_versions row created (status = "pending")
  → files written to Content Store

Admin opens Content Review Queue
  → "Review →" link shown only if has_content = true
  → Click Review → version detail page

Version detail page
  → List of units with "View →" links
  → Actions: Approve / Reject / Publish / Rollback / Block unit content

Unit viewer (/admin/content-review/{version_id}/unit/{unit_id})
  → Left nav: content types (Lesson / Tutorial / Quiz Set 1/2/3 / Experiment)
  → Inline reviewer notes per section/question/step

Version diff (/admin/content-review/{version_id}/diff)
  → Word-level diff highlighting
```

---

## Admin Account Management

**Roles:** `developer` · `tester` · `product_admin` · `super_admin`

```bash
# Create initial super admin
docker compose exec api python /app/scripts/seed_super_admin.py

# Reset password
docker compose exec api python /app/scripts/reset_admin_password.py \
  --email your@email.com --password NewPassword123!

# Hard-delete a test account (dry-run by default; --commit to persist)
docker compose exec api python /app/scripts/purge_account.py --email foo@example.com
```

⚠️ `purge_account.py` bypasses ADR-005 soft-delete and destroys records irrecoverably. Never run against real data.

---

## Key Conventions

### Authentication — Three-track auth, do not mix tracks

| Track | Users | Login endpoint | Token key |
|---|---|---|---|
| Auth0 exchange | Self-registered students & teachers | `POST /auth/exchange` | `sb_token` / `sb_teacher_token` |
| **Local (school-provisioned)** | School founders, provisioned teachers & students | **`POST /auth/login`** | `sb_teacher_token` / `sb_token` |
| Admin bcrypt | Internal team | `POST /admin/auth/login` | `sb_admin_token` |

**`first_login=true` → client MUST redirect to `/school/change-password?required=1` at the portal layout level.** Never skip client-side.

### Logging
```python
from src.utils.logger import get_logger
log = get_logger("component")
```
Never `print()`. Never log passwords, JWT tokens, or Stripe keys.

### Caching (read order: L1 → L2 → DB)
```
L1  cachetools TTLCache  JWT keys · curriculum trees · config
L2  Redis               Entitlement · content JSON · rate limits
L3  CloudFront CDN      Audio MP3 · large JSON files
```

### i18n
- AI-generated content is already in the correct language — never run through i18n.
- UI strings only: `web/i18n/en.json` and `mobile/i18n/{lang}.json`.

---

## Testing

```
Backend : pytest + httpx.AsyncClient; mock PostgreSQL, Stripe, Redis — no live DB in CI

Web     : Playwright E2E — 120 tests (chromium + persona projects).
           Run from host (not container). See web/tests/e2e/README.md.
           TypeScript type-check: stop web container, rm .next/, then npx tsc --noEmit (pitfall #39).

Mobile  : pytest for logic only (SyncManager, LocalCache, ProgressQueue, i18n)

Pipeline: pytest with mocked Anthropic SDK + TTS SDK
```

**Never** hit a live database, live Redis, or any external API in CI.

**Quiz suite** (`backend/quiz_suite/` + `web/tests/e2e/quiz-suite/`): live-stack, excluded from normal runs.
Run: `./scripts/quiz_suite.sh` (exit 0=pass, 1=test failure, 2=stack not up). Never pass `-e TEST_DB_URL=` to pytest (pitfall #37).

---

## Running Things

```bash
# Start everything
./dev_start.sh

# Run automated test suite
./dev_start.sh test

# Stop / wipe DB
./dev_start.sh stop
./dev_start.sh reset

# Rebuild a single service
docker compose build api && docker compose up -d api

# requirements.txt change — rebuild ALL FOUR backend services
docker compose build api celery-worker celery-pipeline celery-beat-primary \
  && docker compose up -d api celery-worker celery-pipeline celery-beat-primary

# Source-only change — just restart workers (api hot-reloads)
docker compose restart celery-worker celery-pipeline celery-beat-primary

# Apply pending migrations (manually)
docker compose exec -e TEST_DB_URL= api alembic upgrade head

# Check logs
docker compose logs celery-pipeline --since 10m -f

# Quiz suite (requires ./dev_start.sh already running)
./scripts/quiz_suite.sh

# Pipeline
python pipeline/seed_default.py --year 2026
python pipeline/build_grade.py --grade 8 --lang en,fr,es
python pipeline/build_unit.py --curriculum-id default-2026-g8 --unit G8-MATH-001 --lang en --force
```

---

## Doc Audit

Local toolkit at `scripts/doc_audit/` for catching drift.

| Checker | What it catches |
|---|---|
| `check_link_integrity.py` | Broken `[label](path)` links; bare repo-path mentions that don't exist |
| `check_migrations_table.py` | Migration files not in this CLAUDE.md table; numbering gaps |
| `check_test_counts.py` | `(NNN total)` claim vs `pytest --collect-only` actual |

```bash
python3 scripts/doc_audit/run_all.py --out drift-report.json
python3 scripts/doc_audit/run_all.py --skip test_counts
```

`<!-- doc-audit:ignore -->` on a line suppresses link_integrity findings on that line or the next. Use sparingly.

See [AGENTS.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/AGENTS.md) for the per-phase build checklist.

---

## Top Pitfalls

1. **Mobile/web calling Anthropic directly** — no API key on client; never do this.
2. **Blocking the async event loop** — use asyncpg, aioredis, httpx; wrap bcrypt in executor.
3. **Proxying audio through FastAPI** — return a pre-signed URL; never stream MP3 bytes.
4. **Progress writes blocking student response** — Celery fire-and-forget only.
5. **Not sizing connection pools** — deploy PgBouncer; `max_connections ≥ 200`.
6. **Clearing Redis but not CDN** — invalidate both together on content version bump.
7. **Redis without AOF persistence** — all sessions lost on restart.
8. **Stripe webhook without signature verification** — always `construct_event` first.
9. **No idempotency on Stripe webhook** — dedup by `stripe_event_id`.
10. **Entitlement gating in mobile app** — backend only; read HTTP status codes.
11. **Locale as query param** — locale comes from JWT only.
12. **`attempt_number` from client** — compute server-side from DB count.
13. **Teacher JWT on student endpoints** — separate secrets + role checks.
14. **Pipeline not idempotent** — check `meta.json` content_version; use `--force` to override.
15. **XLSX parse errors as 500** — return HTTP 400 with per-row structured error list.
16. **`max_tokens` < 16384 in pipeline** — Epic 11 prompts exceed 8192; set 16384 in `pipeline/providers/_wegofwd_adapter.py`.
17. **`localStorage` during SSR** — initialise as `null`, populate in `useEffect`.
18. **Missing migration after pull** — API throws `UndefinedColumnError`; run `alembic upgrade head`.
19. **Rebuild without restart** — always `docker compose up -d` after `build`.
20. **`unit_name NOT NULL` in `curriculum_units`** — include `unit_name` (= `title`) in pipeline INSERT or row silently fails.
21. **Roster upload format** — use `{students: [{email, grade?, teacher_id?}]}` not `{student_emails: [...]}`.
22. **Grade self-change for school students** — `PATCH /student/profile` returns 403 on `grade`; use `PUT /schools/{id}/students/{id}/assignment`.
23. **`login_local_user` must stamp `app.current_school_id='bypass'`** — RLS hides all rows without it; `set_config` before SELECT, never `pool.fetchrow()` on RLS-protected tables unauthenticated.
24. **`first_login=true` must block at layout level** — check decoded JWT in layout `useEffect`, not only on the login page.
25. **Parallel pipeline runs race on `meta.json`** — confirm no `pipeline_jobs` with `status IN ('queued','running')` before manual `--force`.
26. **Playwright Chromium in Alpine container** — glibc binary, musl host; run `npx playwright test` from the host `web/` directory.
27. **Failed Alembic upgrade leaves orphan state** — always run downgrade → upgrade on a fresh DB before committing a migration.
28. **Pipeline CLI must set `app.current_school_id='bypass'`** — Epic 10 L-1 RESTRICTIVE RLS silently drops platform-owner inserts without it; `await conn.execute("SET app.current_school_id = 'bypass'")` immediately after connect.
29. **`published_at` must be `datetime`, not string** — use `datetime.now(tz=timezone.utc)` for TIMESTAMPTZ columns; `_now_iso()` is for JSON serialisation only.
30. **`_upsert_curriculum_units` must include `unit_name`** — pass `title` as both `title` and `unit_name`; missing = silent `db_upsert_units_skip`.
31. **`get_curriculum_tree` must use the 3-step resolver** — use `content/service.py::resolve_curriculum_id`, then query `curriculum_units WHERE curriculum_id = $resolved`.
32. **`curriculum_units.subject` stores codes, not display names** — use `COALESCE(MAX(csv.subject_name), cu.subject)` joined on `(curriculum_id, subject)`.
33. **`build_lesson_prompt` must generate `sections` array** — new schema requires `sections` (Introduction, Core Concepts, Worked Examples, Real-World Applications, Summary) and `key_points`; `_normalize_lesson` handles three formats.
34. **`alembic upgrade head` migrates TEST DB, not dev** — always pass `-e TEST_DB_URL=`; `alembic/env.py` prints the target DB on every run — read it.
35. **Never trust the client for quiz grading** — grading is server-side; pin the quiz set per session (`quizset:{session_id}`); `end_session` must use Redis tally, not `progress_answers` count (fire-and-forget race).
36. **Placeholder content must never reach students** — `get_content_file` refuses `dev-placeholder`; do not re-run the seeder to fix a 404.
37. **`-e TEST_DB_URL=` is REQUIRED for alembic and FORBIDDEN for pytest.** Without it, alembic migrates `studybuddy_test` instead of dev. With it on pytest, `conftest.py`'s `downgrade(base)` runs against the dev database — this wiped 30 demo students, 1 school, 15 curricula on 2026-08-01. `quiz_suite/` is a sibling of `tests/` so conftest's autouse fixture never applies to it. Never pass `-e TEST_DB_URL=` to any `pytest` command.
38. **`docker compose build api` does NOT rebuild Celery workers** — each service builds its own image; after `requirements.txt` changes, rebuild all four: `api celery-worker celery-pipeline celery-beat-primary`. Source changes need no rebuild (restart workers); dependency changes do.
39. **`npm run typecheck` reports nothing while dev server is running** — `.next/` partial files abort tsc before semantic analysis, masking all real errors. Stop the web container, remove `.next/`, then run `npx tsc --noEmit`.
40. **`web/lib/api/*.ts` DTOs do NOT derive from `types.gen.ts`** — adding a field means editing both the generated file AND the hand-written one the pages import.
41. **Two pytest runs against the `api` container destroy each other.** `conftest.py`'s session-scoped `run_migrations` ends in `downgrade(base)`, dropping every table; whichever finishes first destroys the other. The damage rests in the database, not a live process — `ps` proves nothing. Never run pytest while another pytest is running against that container. When a suite fails en masse, re-run it alone from a clean state before trusting the count.

---

## Content Rules

1. **Age-appropriate:** No violence, profanity, or suggestive themes. Grades 5–12.
2. **Inclusive language:** Gender-neutral phrasing. No gendered emoji for professional roles.
3. **Reading level:** Target 1–2 grade levels below the student's actual grade.
4. **STEM clarity:** Use Mermaid.js diagrams for flowcharts. Explain maths step-by-step.
5. **Student-facing error messages** must be age-appropriate and non-technical.
6. **PSA language:** Flesch-Kincaid Grade 8 or below; multi-channel; screen-reader compatible.

---

## Compliance — COPPA & FERPA

**COPPA:** No parental-consent flow — school-provisioned accounts only (#609, 2026-08-24). Collect only name, email, grade, locale. No tracking or behavioural fingerprinting of minors.

**FERPA:** Student progress, quiz scores, and lesson-view history are educational records. Teacher/admin endpoints must be scoped to the student's institution. Default to not sharing directory information.

---

## Accessibility Standards

- UI must target **WCAG 2.1 Level AA**.
- Minimum colour contrast: 4.5:1 normal text, 3:1 large text.
- All interactive elements must have accessible labels (`aria-label` on web).
- Audio content must have text alternatives.

---

## Data & Privacy Rules

- **No real student PII in dev or test.** Use synthetic data.
- **Data minimisation:** name, email, grade, locale only.
- **Retention:** Progress records retained for account lifetime, then anonymised after deletion (30-day GDPR schedule).
- **AI-generated content is never the student's output.**

---

## Technical Preferences

- **Primary languages:** Python (backend / pipeline) · TypeScript/React (web) · Kotlin (Android).
- **Cloud:** Architecture must remain cloud-agnostic. Abstract storage behind an interface.
- **Content moderation:** AlexJS (pipeline phase). Azure AI Content Safety deferred.
- **Async:** Kotlin Coroutines for Android; no blocking calls on main thread.
- **Dependencies:** Review for CVEs before inclusion. After `npm install`, also run `docker compose exec web npm install`.
