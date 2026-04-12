# StudyBuddy OnDemand — CLAUDE.md

Backend-powered STEM tutoring platform for Grades 5–12. Students get instant
pre-generated AI content (lessons, quizzes, audio) without needing an Anthropic
API key. Schools and teachers can upload custom curricula. Subscription-based.

---

## Project Status

**Phases 1–11 complete. Phase A (local auth) shipped. Phase B (Classrooms) in progress.**

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

**Active branch:** `main` (next: Phase C — Curriculum Catalog)

**Recently shipped (beyond Phase 11):**
- Content review unit viewer — Lesson / Tutorial / Quiz / Experiment renderers
- Inline reviewer annotations scoped per section, question, and step
- Side-by-side version diff with word-level highlighting
- Pipeline improvements: `max_tokens=8192`, `subject_name` column, `payload_bytes` tracking
- Demo teacher account request / verify / login flow
- Admin pipeline jobs table: sortable, filterable, horizontal scroll
- School-as-primary-entity model: `student_teacher_assignments` (migration 0024), per-student grade+teacher assignment, bulk reassign, grade self-change guard
- **Phase A local auth**: third auth track for school-provisioned users — email+password login, `first_login` forced reset, school self-registration, teacher/student provisioning UI, `LocalAuthGuard` portal gate, JWT refresh interceptor (migrations 0030–0037)
- **Phase B Classrooms (partial)**: `classrooms`, `classroom_packages`, `classroom_students` tables (migration 0038); classroom CRUD + package/student assignment endpoints; Classrooms nav + list/detail pages in school portal; 21 tests

**Open tasks:**
- Phase B — Phase C (Curriculum Catalog), Phase D (Curriculum Builder), Phase E (Pipeline Billing) — see `docs/REGISTRATION_DESIGN_ANALYSIS.md`
- Multi-provider LLM pipeline — see `docs/DESIGN_EXPLORATION_MULTI_PROVIDER_LLM.md` (design exploration, not scheduled)

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
| [SCALABILITY.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/SCALABILITY.md) | Capacity planning, multi-region, load testing, academic year transitions, API versioning |
| [GLOSSARY.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/GLOSSARY.md) | Acronym and term definitions for all abbreviations used across the project |

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
                            observability.py  ← Prometheus metrics, GET /metrics, GET /health, correlation ID middleware
                            events.py         ← emit_event() structured log + metric counter · write_audit_log() Celery dispatch
    tests/               ← pytest; ALL external calls mocked; no live DB in CI
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
- **Manual run:** `docker compose exec api alembic upgrade head`
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
- **COPPA:** students under 13 require parental consent before account activation.
  Block content access until `account_status = 'active'`.
- **Rate limiting on all public endpoints.** Auth: 10 req/min per IP.
  Content: 100 req/min per student JWT. Feedback: 5 submissions/student/hour.

---

## Pipeline Rules

- **Pin the Claude model ID** in `pipeline/config.py` (`CLAUDE_MODEL = "claude-sonnet-4-6"`).
  Never use an implicit "latest". Upgrading models is a deliberate act.
- **`max_tokens` must be `8192`.** Grade 12 tutorials exceed 4096 tokens and will be silently
  truncated, producing invalid JSON. Always set `max_tokens=8192` in `_call_claude()`.
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

Web     : No component tests currently. TypeScript type-check via `npm run typecheck`.

Mobile  : pytest for logic only (SyncManager, LocalCache, ProgressQueue, i18n loader)
           No Kivy widget tests in CI

Pipeline: pytest with mocked Anthropic SDK + mocked TTS provider SDK
           Test schema validation logic and idempotency checks
```

**Never** hit a live database, live Redis, or any external API in CI.

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

# Apply pending migrations manually
docker compose exec api alembic upgrade head

# Check logs for a specific service
docker compose logs celery-pipeline --since 10m -f

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
16. `max_tokens=4096` in pipeline — Grade 12 tutorials exceed this; always use `8192`.
17. Reading `localStorage` during SSR in Next.js — initialise as `null`, populate in `useEffect`.
18. Missing migration after pull — API throws `UndefinedColumnError`; run `alembic upgrade head`.
19. Rebuilding a Docker image without restarting the container — old image stays running; always `up -d` after `build`.
20. `unit_name NOT NULL` in `curriculum_units` — include `unit_name` in pipeline INSERT or the row silently fails.
21. Roster upload uses `{students: [{email, grade?, teacher_id?}]}`, NOT `{student_emails: [...]}` — the old flat list format was removed in migration 0024.
22. Grade self-change blocked for school-enrolled students — `PATCH /student/profile` returns 403 on `grade` if `students.school_id IS NOT NULL`. Grade is set exclusively via `PUT /schools/{school_id}/students/{student_id}/assignment`.
23. **`login_local_user` must stamp `app.current_school_id='bypass'` before querying** — the RLS policy (migration 0028) hides all teacher/student rows when this is not set. Always acquire a pool connection and call `set_config` before the SELECT. Never use `pool.fetchrow()` directly on RLS-protected tables in an unauthenticated context.
24. **`first_login=true` must block navigation at the portal layout level** — not just on the login page. A user who navigates directly to `/school/dashboard` after receiving a token with `first_login=true` must still be redirected to `/school/change-password?required=1`. Check the decoded JWT in the layout `useEffect`, not only in the login handler.

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

- Require verifiable parental consent before collecting any data from under-13 students.
  Block content access until `account_status = 'active'`.
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
