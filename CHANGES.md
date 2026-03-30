# StudyBuddy OnDemand — Implementation Log

## Implementation Log

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
