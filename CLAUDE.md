# StudyBuddy OnDemand — CLAUDE.md

Backend-powered STEM tutoring platform for Grades 5–12. Students get instant
pre-generated AI content (lessons, quizzes, audio) without needing an Anthropic
API key. Schools and teachers can upload custom curricula. Subscription-based.

---

## Project Status

**Current phase: Phase 3 — Progress Tracking (in progress)**

| Phase | Status |
|---|---|
| 1 — Backend Foundation | ✅ Complete (38 tests) |
| 2 — Content Pipeline + English Delivery | ✅ Complete (52 tests) |
| 3 — Progress Tracking | 🔄 Next |
| 4–11 | ⏳ Pending |

Build in phase order; do not skip ahead.

Predecessor project (UI + prompt reference):
`https://github.com/wegofwd2020-hub/studybuddy_free`

---

## Document Map

Before writing any code, read these in order:

| Doc | Read when |
|---|---|
| `ARCHITECTURE.md` | First — system design, data models, API contracts, all phases |
| `BACKEND_ARCHITECTURE.md` | Before touching backend — caching, hot path, SLOs, deployment |
| `REQUIREMENTS.md` | Check requirement ID + status before implementing a feature |
| `AGENTS.md` | Conventions, layer rules, 35 pitfalls, phase-by-phase checklists |
| `CHANGES.md` | Design decisions log and pending work items |
| `OPERATIONS.md` | Runbooks, incident response, disaster recovery, deployment procedures |
| `SCALABILITY.md` | Capacity planning, multi-region, load testing, academic year transitions, API versioning |
| `GLOSSARY.md` | Acronym and term definitions for all abbreviations used across the project |

---

## Repository Layout (target state)

```
StudyBuddy_OnDemand/
  backend/
    main.py              ← FastAPI app entry point + lifespan (DB/Redis pools)
    config.py            ← pydantic-settings; all config from env vars; fail-fast if missing
    src/
      auth/              ← register · login · refresh · forgot-password · reset · delete
      curriculum/        ← serve grade/subject/unit tree from DB
      content/           ← lesson · quiz · tutorial · experiment · audio (pre-generated)
      progress/          ← session · answer · session/end · history
      subscription/      ← Stripe checkout · webhook · plan status
      school/            ← registration · teacher invite · enrolment roster
      analytics/         ← lesson-view events · class metrics · student metrics
      feedback/          ← submit · admin list
      admin/             ← pipeline status · regenerate · audit log
      core/              ← cache manager (L1+L2) · entitlement checker · circuit breakers
                            curriculum resolver dependency · Celery dispatcher
                            observability.py  ← Prometheus metrics, GET /metrics, GET /health, correlation ID middleware
                            events.py         ← emit_event() structured log + metric counter · write_audit_log() Celery dispatch
    tests/               ← pytest; ALL external calls mocked; no live DB in CI
    requirements.txt

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

3. Mobile App  (student device)
   Kivy → local SQLite cache + backend REST API
   NEVER calls Anthropic directly. NEVER has Anthropic or Stripe keys.
```

---

## Layer Rules — Dependencies flow downward only

```
mobile/src/ui/            → mobile/src/logic/,  mobile/src/api/
mobile/src/logic/         → mobile/src/api/
mobile/src/api/           → (external: backend REST)

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
- **Pipeline is idempotent.** Check `meta.json` at unit start; skip if
  `content_version` matches and all expected files exist. Use `--force` to override.
- **Validate every Claude response** against a JSON schema before writing to the
  Content Store. On `ValidationError`, retry up to 3×; then mark unit as failed and
  continue. Never write malformed content.
- **Spend cap:** abort if `tokens_used × TOKEN_COST_USD > MAX_PIPELINE_COST_USD`
  (default $50). Log and alert.
- **Pipeline jobs triggered via API are async (Celery).** `POST /curriculum/pipeline/trigger`
  returns `{job_id}` immediately (202). Status polled via
  `GET /curriculum/pipeline/{job_id}/status`.

---

## Key Conventions

### Configuration
- Backend: `pydantic-settings`; all env vars. `config.py` is the single import point.
- Mobile: `config.py` holds `BACKEND_URL`, SQLite path, JWT path. No AI keys. No Stripe keys.
- Pipeline: `ANTHROPIC_API_KEY`, `TTS_API_KEY`, `CONTENT_STORE_PATH`, `CLAUDE_MODEL` from env.

### Authentication
**Two-track auth — do not mix:**
- **Students + Teachers:** authenticate via Auth0 (external). Client sends Auth0 `id_token` to
  `POST /auth/exchange` or `POST /auth/teacher/exchange`. Backend verifies against Auth0 JWKS
  (L1-cached), upserts user, and issues an internal JWT. No password hash stored for these users.
- **Internal team (developer/tester/product_admin/super_admin):** local bcrypt auth via
  `POST /admin/auth/login`. Signed with `ADMIN_JWT_SECRET` (separate from student/teacher secrets).

Internal JWT payloads:
- Student: `{student_id, grade, locale, role: "student", exp}`
- Teacher: `{teacher_id, school_id, role: "teacher|school_admin", exp}`
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
- UI strings only: `mobile/i18n/{lang}.json`. Load at startup; fall back to `en` on missing key.
- Never hardcode user-facing strings in screen files.

---

## Testing

```
Backend : pytest + httpx.AsyncClient
           Mock PostgreSQL: pytest-asyncio + testing.postgresql (no live DB in CI)
           Mock Stripe SDK calls
           Mock Redis: fakeredis or pytest fixture

Mobile  : pytest for logic only (SyncManager, LocalCache, ProgressQueue, i18n loader)
           No Kivy widget tests in CI

Pipeline: pytest with mocked Anthropic SDK + mocked TTS provider SDK
           Test schema validation logic and idempotency checks
```

**Never** hit a live database, live Redis, or any external API in CI.

---

## Running Things

```bash
# Start everything (DB, Redis, migrations, API with hot-reload)
./dev_start.sh

# Run automated test suite (no API key or Auth0 needed)
./dev_start.sh test

# Stop background containers
./dev_start.sh stop

# Wipe DB and start fresh
./dev_start.sh reset

# Backend (production-like)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Celery workers
celery -A tasks worker -Q pipeline --concurrency=2
celery -A tasks worker -Q io,default --concurrency=4
celery -A tasks beat

# Pipeline — seed and build default curriculum (requires ANTHROPIC_API_KEY)
python pipeline/seed_default.py --year 2026
python pipeline/build_grade.py --grade 8 --lang en,fr,es

# Pipeline — regenerate a single unit
python pipeline/build_unit.py --curriculum-id default-2026-g8 --unit G8-MATH-001 --lang en --force
```

---

## Phase Checklist Quick Reference

See `AGENTS.md` for the full per-phase checklist. Build in this order:

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

## Top Pitfalls (full list of 39 in AGENTS.md)

1. Mobile app calling Anthropic directly — it has no API key and must never do this.
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
