# Phase W7 — Playwright E2E Integration Tests — PRE

**Started:** 2026-03-27
**Branch:** main
**Preceding build:** 99 unit tests passing, 56 routes, 8 existing Playwright E2E tests (public pages only)

---

## Scope

Expand the Playwright E2E test suite to cover all three portals:
admin console (fully), public login pages (fully), and auth redirect behaviour
(student + school portals). All tests run against the Next.js dev server
started automatically by the Playwright `webServer` config.

---

## Auth Strategy Per Portal

| Portal | Auth mechanism | E2E approach |
|---|---|---|
| Admin | Client-side `localStorage.getItem("sb_admin_token")` | `page.addInitScript` injects a mock JWT; `page.route()` mocks backend API responses |
| Student | Server-side `auth0.getSession()` in layout | Fake Auth0 env vars injected into dev server; no real session → `getSession()` returns null → redirect tested |
| School | Same as student | Same approach |
| Public | No auth | Direct navigation; assert visible elements |

**Auth0 env vars** — injected into the dev server process via `webServer.env` in
`playwright.config.ts`. Using fake but correctly-shaped values means
`auth0.getSession()` gracefully returns `null` (no valid session cookie), which
triggers the expected redirects.

**Mock admin JWT** — a helper function builds a valid base64-encoded JWT payload
at test time (`makeAdminJwt(role)`). No real signing; the admin layout only
checks presence and decodes the payload, it does not verify the signature
client-side.

---

## Spec Files to Add

| File | Tests | Coverage |
|---|---|---|
| `tests/e2e/admin-portal.spec.ts` | 11 | Login form, error state, success + token stored, redirect when no token, dashboard load with API mocks, analytics, health, pipeline, content review, RBAC nav diff (developer vs super_admin) |
| `tests/e2e/auth-redirects.spec.ts` | 6 | `/dashboard` → `/login`; `/subjects` → `/login`; `/school/dashboard` → `/school/login`; `/school/reports/overview` → `/school/login`; `/admin/dashboard` (no token) → `/admin/login`; `/admin/analytics` (no token) → `/admin/login` |
| `tests/e2e/login-pages.spec.ts` | 4 | School login renders Sign In button; school login links to student login; admin login has email/password fields; admin login shows error on bad credentials |

**Existing spec untouched:** `tests/e2e/public.spec.ts` (8 tests)

**Total Playwright tests after W7:** 8 + 11 + 6 + 4 = **29**
**Vitest unit tests:** 99 (unchanged)

---

## Playwright Config Changes

- Remove `Mobile Chrome` project (requires additional browser install not needed here)
- Add `webServer.env` with fake Auth0 credentials for redirect tests
- Keep `reuseExistingServer: !process.env.CI` (dev convenience)

---

## Exit Criteria

- [ ] 29 Playwright tests passing (chromium only)
- [ ] Admin portal: login flow, protected redirects, dashboard, health, pipeline, review
- [ ] Auth redirects: student/school/admin unauthenticated access all redirect correctly
- [ ] Login pages: correct structure verified
- [ ] Typecheck clean
- [ ] Production build still passes (no regressions)
