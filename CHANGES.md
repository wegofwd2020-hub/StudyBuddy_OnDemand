# StudyBuddy OnDemand — Implementation Log

## Implementation Log

---

### ADR-001 + Demo Teacher Flow + Content Review Improvements (2026-04-05)

**Branch:** `feat/demo-teacher-flow`  
**Tag:** `adr-001-complete`  
**Tests:** 215 backend tests passing

#### ADR-001 — School-as-Primary-Entity Architecture

Three decisions shipped together under `security(adr-001)`:

**Decision 1 — Student-teacher assignment model (migration 0024)**

| File | Change |
|---|---|
| `backend/alembic/versions/0024_student_teacher_assignments.py` | New `student_teacher_assignments` table; adds `grade` + `teacher_id` columns to `school_enrolments` |
| `backend/src/school/router.py` | `PUT /schools/{id}/students/{student_id}/assignment` — per-student grade + teacher assignment; bulk reassign endpoint |
| `backend/src/school/service.py` | Grade self-change guard: returns 403 on `PATCH /student/profile` if student has `school_id` |
| `backend/tests/test_school_roster.py` | Migrated roster tests to `{students: [...]}` format (old `{student_emails: [...]}` removed in 0024) |

**Decision 2 — School-only billing (migrations 0025–0027)**

| Migration | Description |
|---|---|
| 0025 | Schema corrections: `schools.contact_email UNIQUE` + `teachers.school_id CHECK` |
| 0026 | Drop `private_teachers`, `teacher_subscriptions`, `student_teacher_access`; tighten `curricula.owner_type` CHECK |
| 0027 | Drop `subscriptions` table; Stripe webhook now school-only |

- `backend/src/school/subscription_service.py` — Full rewrite for school-level billing: `activate_school_subscription`, `cancel_school_subscription_db`, `handle_school_payment_failed`, `_bulk_update_enrolled_student_entitlements`
- `backend/src/private_teacher/` — Module removed entirely (no routes remain)

**Decision 3 — PostgreSQL Row-Level Security (migration 0028)**

| File | Change |
|---|---|
| `backend/alembic/versions/0028_rls.py` | `ENABLE/FORCE ROW LEVEL SECURITY` + `tenant_isolation` policy on 7 tables; `app.current_school_id` session variable |
| `backend/src/core/db.py` | `get_db()` stamps `app.current_school_id` from `request.state.rls_school_id` before yielding; resets in `finally` |
| `backend/src/auth/dependencies.py` | `get_current_teacher()` sets `request.state.rls_school_id = payload["school_id"]` |
| `backend/tests/conftest.py` | `db_conn` fixture sets `app.current_school_id = 'bypass'` (transaction-local) |
| `backend/tests/test_rls.py` | 6 new isolation tests using deterministic school UUIDs `a0000000-...001` / `b0000000-...001` |

**Redis key namespace (centralised in `cache_keys.py`)**

| File | Change |
|---|---|
| `backend/src/core/cache_keys.py` | New module: `ent_key`, `cur_key`, `school_ent_key`, `school_scan_pattern`, `content_key`, `csv_key`, `quiz_set_key` |
| `backend/src/content/service.py` | Switched to `cache_keys` helpers; `get_entitlement()` now queries `school_subscriptions` as source of truth for school-enrolled students (no extra `students` table lookup); `_get_school_sub()` private helper with 300 s Redis cache |
| `backend/src/curriculum/resolver.py` | `invalidate_resolver_cache_for_school()` uses `SCAN school:{school_id}:*` instead of per-student DB lookup |
| `backend/src/auth/tasks.py` | Grade-promotion scan covers `school:*:ent:*`, `school:*:cur:*`, `ent:*`, `cur:*` |

Key prefixes now in use:

| Key | Scope |
|---|---|
| `school:{school_id}:ent:{student_id}` | Entitlement for school-enrolled student |
| `school:{school_id}:cur:{student_id}` | Curriculum resolver for school-enrolled student |
| `school:{school_id}:ent` | Whole-school entitlement summary (TTL 300 s) |
| `ent:{student_id}` | Solo student entitlement (legacy path) |
| `cur:{student_id}` | Solo student curriculum resolver (legacy path) |

---

#### Demo Teacher Flow

**Scope:** Allow a prospective teacher to request a demo account, receive credentials by email, and explore the full school portal with read-only data from MilfordWaterford.

| File | Change |
|---|---|
| `backend/alembic/versions/0012_demo_teacher_accounts.py` | `demo_teacher_requests` + `demo_teacher_accounts` tables |
| `backend/src/demo/teacher_router.py` | Request / verify / login / logout for demo teachers |
| `backend/src/demo/teacher_service.py` | Business logic; token generation; email dispatch via Celery |
| `backend/scripts/seed_demo_milfordwaterford.py` | Seeds MilfordWaterford school + teachers Sam Houston (Gr 8) + Linda Ronstad (Gr 12) + 4 students; idempotent |
| `web/app/(public)/demo-teacher/page.tsx` | Public demo teacher request page |
| `web/app/(school)/school/...` | Full school portal with grade-filtered curriculum, roster, reports, alerts |
| `web/components/demo/DemoTeacherRequestModal.tsx` | Modal launched from landing page |
| `web/components/demo/DemoTeacherGate.tsx` | Blocks write actions (demo teachers are read-only) |
| `web/app/(admin)/admin/demo-teacher-accounts/page.tsx` | Admin management: approve / reject / extend / revoke demo teacher accounts |

**Demo teacher credentials (MilfordWaterford):**

| Name | Email | Password | Grade |
|---|---|---|---|
| Sam Houston | sam.houston@milfordwaterford.edu | MWTeacher-Sam-2026! | 8 |
| Linda Ronstad | linda.ronstad@milfordwaterford.edu | MWTeacher-Linda-2026! | 12 |

Login at: `http://localhost:3000/school/login`

---

#### Content Review Improvements

**AlexJS warnings — per-content-type breakdown (Issue #55)**

Previously AlexJS ran once over all content concatenated, the total count was stored but silently dropped by Pydantic (field was missing from `UnitContentMetaResponse`), and no per-type breakdown existed.

| File | Change |
|---|---|
| `pipeline/build_unit.py` | `_extract_text_for_alex_by_type()` returns `{content_type: text}`; AlexJS runs once per type; `meta.json` now stores `alex_warnings_by_type: {"lesson": N, ...}` |
| `backend/src/admin/schemas.py` | Added `alex_warnings_count: int = 0` and `alex_warnings_by_type: dict[str, int] = {}` to `UnitContentMetaResponse` (bug fix — fields were missing) |
| `backend/src/admin/service.py` | `get_unit_content_meta()` reads `alex_warnings_by_type` from `meta.json` |
| `web/lib/api/admin.ts` | Added `alex_warnings_by_type?: Record<string, number>` to `UnitContentMeta` |
| `web/app/(admin)/admin/content-review/[version_id]/unit/[unit_id]/page.tsx` | Left-nav items show per-type warning badge (amber <5 warnings, red ≥5) |

**Inline reviewer annotations (Issue #52)**

- `content_annotations` table (migration 0013): stores annotations keyed by `{unit_id}::{content_type}::{section_id}`
- Unit viewer renders per-section `SectionNotes` component — expandable, with add/delete
- Tutorial sections use tab key as section ID; quiz questions use `Q{n}` suffix

**Side-by-side version diff (Issue #53)**

- `GET /admin/content/review/{version_id}/diff?compare_to={version_id}` returns two full versions
- Frontend at `/admin/content-review/{version_id}/diff` renders word-level diff (green = added, red = removed) using `diffWords` from the `diff` package
- Per content type, per field (section heading, question text, step instruction)

**Batch approve (Issue #54)**

- `POST /admin/content/review/batch-approve` with `{curriculum_id, notes}` — approves all pending versions for a curriculum
- Admin detail page shows "Approve All" button when ≥2 pending versions exist

---

#### Admin schemas fixes (pre-existing bugs exposed by import error)

The following schemas were missing from `schemas.py`, causing an `ImportError` that silently blocked the entire test suite:

| Schema | Shape |
|---|---|
| `AssignRequest` / `AssignResponse` | `admin_id: str | None` → `{version_id, assigned_to_admin_id, assigned_to_email, assigned_at}` |
| `BatchApproveRequest` / `BatchApproveResponse` | `{curriculum_id, notes}` → `{approved_count, version_ids}` |
| `AdminUserItem` / `AdminUsersResponse` | `{admin_user_id, email, role}` |
| `SubscriptionAnalyticsResponse` | Updated from individual-billing shape (`active_monthly`, `active_annual`) to school-billing shape (`by_plan`, `total_active`, `mrr_usd: str`) |

---

#### Accessibility + typography (Rules 18 + 13)

- Inter / Merriweather / JetBrains Mono font stack loaded via `@fontsource` — no external CDN
- Dyslexia toggle via Eye icon in portal header or **Alt+D** — persisted in `sb_dyslexic` cookie
- `/healthz` liveness + `/readyz` readiness probes added (Rule 13)

---

#### Pipeline improvements

| Change | Detail |
|---|---|
| `max_tokens=8192` | Always set in `_call_claude()` — Grade 12 tutorials exceeded 4096 and produced truncated JSON |
| `subject_name` column | Added to `content_subject_versions` (migration 0015); pipeline stores human-readable subject name alongside `subject` key |
| `payload_bytes` tracking | Migration 0014; pipeline records output byte count per job |
| Per-unit AlexJS | `_extract_text_for_alex_by_type()` introduced; each content type checked independently |

---

**How to test:**

```bash
# Start all services
./dev_start.sh

# Seed MilfordWaterford demo school (teachers + students)
docker compose exec api python scripts/seed_demo_milfordwaterford.py

# Run backend tests
docker compose exec api python -m pytest -q

# Teacher login
curl -s -X POST http://localhost:8000/api/v1/demo/teacher/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"sam.houston@milfordwaterford.edu","password":"MWTeacher-Sam-2026!"}' \
  | python3 -m json.tool
```

*Last updated: 2026-04-05*

---

### Demo Student System — Issues #32–#40 (2026-03-30)

**Branch:** `feat/demo-32`
**Tests:** 839/839 web tests passing · 56/56 backend demo tests passing (requires live DB)

**Files created:**

*Backend*
- `backend/alembic/versions/0011_demo_accounts.py` — Migration: `demo_requests`, `demo_accounts` tables + indexes
- `backend/src/demo/` — Demo request/verify/login/logout/resend endpoints (`router.py`, `schema.py`, `service.py`)
- `backend/src/admin/demo_accounts.py` — Admin CRUD: list, extend, revoke, resend-verification
- `backend/src/email/` — Gmail SMTP email service (`client.py`, `templates.py`) for verification/credential emails
- `backend/tests/test_demo_infra.py` — 14 schema + index tests
- `backend/tests/test_demo_endpoints.py` — 21 unit tests for public demo endpoints
- `backend/tests/test_admin_demo_accounts.py` — 21 unit tests for admin demo endpoints
- `backend/scripts/seed_demo_test_account.py` — Idempotent seed script: creates `demo-test@studybuddy.dev` / `DemoTest-2026!` with 30-day TTL; `--dry-run` and `--ttl-days N` flags
- `backend/scripts/export_openapi.py` — Dumps OpenAPI JSON for type-gen

*Web*
- `web/app/(public)/demo/login/page.tsx` — Demo login page at `/demo/login`
- `web/app/(public)/demo/verify/[token]/page.tsx` — Email verification landing page at `/demo/verify/[token]`
- `web/app/(admin)/admin/demo-accounts/page.tsx` — Admin demo accounts CRUD page with status filters, email search, pagination, extend/revoke modals, resend action
- `web/components/demo/DemoRequestModal.tsx` — Home page "Try a free demo" dialog (react-hook-form + zod, success state, error codes)
- `web/components/demo/DemoBanner.tsx` — Persistent amber/red banner in student layout showing time remaining + "Sign out" / "Get full access" actions
- `web/components/demo/DemoGate.tsx` — Wrapper that blocks demo students from restricted pages with a friendly sign-up prompt
- `web/lib/api/demo.ts` — Typed API client functions: `requestDemo`, `demoLogin`, `demoLogout`, `verifyDemoEmail`, `resendDemoVerification`
- `web/lib/hooks/useDemoStudent.ts` — Client hook: reads demo JWT from `localStorage`, returns decoded payload or null
- `web/lib/api/types.gen.ts` — Auto-generated TypeScript types from OpenAPI spec
- `web/openapi.json` — OpenAPI spec snapshot (for type gen)
- `web/tests/e2e/data/admin-demo-accounts-page.ts` — Shared test fixtures for ADM-60–ADM-65
- `web/tests/unit/demo-request-modal.test.tsx` — 12 unit tests (DM-01–DM-12)
- `web/tests/unit/demo-banner.test.tsx` — Unit tests for DemoBanner time-remaining logic and urgent state
- `web/tests/unit/demo-login-page.test.tsx` — Unit tests for demo login page form flow
- `web/tests/unit/demo-verify-page.test.tsx` — Unit tests for verification landing page states
- `web/tests/unit/admin-demo-accounts-page.test.tsx` — 27 unit tests (ADM-60–ADM-65): access control, row actions, extend/revoke/resend modals, pagination, empty state

**Files modified:**

- `backend/config.py` — Added `SMTP_*` and demo-related env vars
- `backend/main.py` — Registered demo router; added demo JWT to auth middleware
- `backend/requirements.txt` — Added `aiosmtplib`, `jinja2` for email service
- `backend/src/auth/dependencies.py` — Added `demo_student` role to auth dependency
- `backend/src/auth/tasks.py` — Added Celery task for async demo verification email dispatch
- `backend/tests/helpers/token_factory.py` — Added `demo_student` token factory helper
- `web/app/(public)/page.tsx` — Replaced static CTA with `<DemoRequestModal />`
- `web/app/(student)/layout.tsx` — Added `<DemoBanner />` above `<TrialBanner />`
- `web/app/(student)/account/settings/page.tsx` — Wrapped with `<DemoGate>` (demo users cannot edit settings)
- `web/app/(student)/account/subscription/page.tsx` — Wrapped with `<DemoGate>` (demo users cannot manage subscription)
- `web/app/(admin)/admin/feedback/page.tsx` — Minor layout tweak (carried in this branch)
- `web/components/layout/AdminNav.tsx` — Added "Demo Accounts" nav item (minRole: `product_admin`)
- `web/i18n/en.json` — Added `demo.*` translation namespace
- `web/lib/api/admin.ts` — Added `getDemoAccounts`, `extendDemoAccount`, `revokeDemoAccount`, `adminResendDemoVerification`, `DemoAccountItem`, `DemoAccountListResponse` types
- `web/package.json` / `web/package-lock.json` — Added `react-hook-form`, `@hookform/resolvers`, `zod` dependencies
- `.github/workflows/test.yml` — Enabled pipeline tests (no longer skipped)

**Key decisions made:**

- Demo JWT uses role `demo_student` — routed through the same student auth dependency but distinguished by role to allow gating
- `useDemoStudent()` reads from `localStorage` (key `sb_token`) and decodes the JWT client-side; no extra API call needed
- `DemoGate` renders a placeholder for blocked routes rather than redirecting, keeping the URL intact for user orientation
- `DemoBanner` uses `role="status"` + `aria-label` for screen-reader announcement; urgent state (< 2 hours) switches to red palette and prepends "Urgent:" label
- Admin demo-accounts page guards behind `hasPermission(role, "product_admin")` — `developer` and `tester` see "Access denied"
- Seed script connects to raw PostgreSQL (not PgBouncer) to avoid asyncpg prepared-statement issues in transaction-pooling mode
- Email service uses Gmail SMTP via `aiosmtplib`; template rendering via Jinja2 to keep HTML out of Python strings

**New backend endpoints added:**

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/demo/request` | Public | Submit email to request a 24-hour demo |
| GET | `/api/v1/demo/verify/{token}` | Public | Verify email token, create demo account, send credentials |
| POST | `/api/v1/demo/verify/resend` | Public | Resend verification email for pending request |
| POST | `/api/v1/demo/auth/login` | Public | Authenticate with demo credentials, return JWT |
| POST | `/api/v1/demo/auth/logout` | Demo JWT | Blacklist JTI in Redis |
| GET | `/api/v1/admin/demo-accounts` | Admin JWT (product_admin+) | List demo requests with filter/search/pagination |
| POST | `/api/v1/admin/demo-accounts/{id}/extend` | Admin JWT (product_admin+) | Extend demo expiry by N hours |
| POST | `/api/v1/admin/demo-accounts/{id}/revoke` | Admin JWT (product_admin+) | Immediately revoke demo access |
| POST | `/api/v1/admin/demo-accounts/{request_id}/resend` | Admin JWT (product_admin+) | Admin-triggered resend of verification email |

**How to run:**

```bash
# Start all services
./dev_start.sh

# Seed the persistent demo test account (inside api container)
docker compose exec api python scripts/seed_demo_test_account.py
# Or with custom TTL:
docker compose exec api python scripts/seed_demo_test_account.py --ttl-days 7
# Dry-run to preview:
docker compose exec api python scripts/seed_demo_test_account.py --dry-run
```

**How to test:**

```bash
# Web unit tests (839 passing)
cd web && npm test

# Backend demo tests (requires running DB)
./dev_start.sh test
# Or targeted:
python -m pytest backend/tests/test_demo_infra.py backend/tests/test_demo_endpoints.py backend/tests/test_admin_demo_accounts.py -v

# Manual demo flow:
# 1. Visit http://localhost:3000 → click "Try a free demo"
# 2. Enter email → receive verification email
# 3. Click link → land on /demo/verify/[token] → credentials displayed
# 4. Visit /demo/login → log in → student portal with DemoBanner
# 5. Try /account/settings or /account/subscription → see DemoGate
# 6. Admin: /admin/demo-accounts → list/extend/revoke/resend
```

*Last updated: 2026-03-30*

---
