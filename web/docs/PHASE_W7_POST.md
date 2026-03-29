# Phase W7 — Playwright E2E Integration Tests — POST

**Completed:** 2026-03-27
**Vitest unit tests:** 99 passing (unchanged)
**Playwright E2E tests:** 34 passing (+26 new; 8 updated)
**Build:** Clean (56 routes, 0 type errors)

---

## Deliverables

### Spec files added / updated

| File                               | Tests       | Coverage                                                                                                                                                               |
| ---------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/e2e/public.spec.ts`         | 8 (updated) | Fixed selectors: exact text matching + `.first()` for desktop/mobile nav duplication                                                                                   |
| `tests/e2e/admin-portal.spec.ts`   | 13          | Admin login success + error; unauthenticated redirect; dashboard, analytics, health, pipeline, content-review page structure; RBAC nav diff (super_admin vs developer) |
| `tests/e2e/auth-redirects.spec.ts` | 6           | `/dashboard` → `/login`; `/subjects` → `/login`; `/school/dashboard` → `/school/login`; `/school/reports/overview` → `/school/login`; admin routes → `/admin/login`    |
| `tests/e2e/login-pages.spec.ts`    | 7           | School login renders + links; admin login fields + error state + success flow with token storage                                                                       |

### Playwright config updated

| Change                          | Reason                                                                                                                                                                         |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Removed `Mobile Chrome` project | Additional browser install not available in this environment                                                                                                                   |
| Added `webServer.env`           | Injects fake Auth0 credentials so `auth0.getSession()` initialises without crashing; with no valid session cookie present it returns `null`, triggering the expected redirects |

### Bug fixed

**`app/page.tsx` removed** — The Next.js project template scaffold left a `app/page.tsx`
(the "To get started, edit the page.tsx file" default page) that was shadowing
`app/(public)/page.tsx` at the `/` route. Next.js prioritises the non-grouped page,
so the real StudyBuddy landing page was never served at `/` in development.
Deleting `app/page.tsx` restores correct routing.

---

## Key Implementation Details

### Mock JWT for admin portal tests

```ts
function makeAdminJwt(role: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString(
    "base64url",
  );
  const payload = Buffer.from(
    JSON.stringify({ admin_id: "test-admin", role, exp: 9999999999 }),
  ).toString("base64url");
  return `${header}.${payload}.sig`;
}
```

The `useAdmin` hook decodes the payload with `atob()` — no signature verification
client-side — so unsigned test tokens work correctly.

### Injecting tokens with `addInitScript`

```ts
await page.addInitScript((t) => localStorage.setItem("sb_admin_token", t), token);
```

`addInitScript` fires before any page scripts run, so the token is present when the
admin layout's `useEffect` checks `localStorage`.

### API mocking with `page.route()`

All backend calls (`**/api/v1/admin/**`) are intercepted and fulfilled with stub
JSON. This means E2E tests require no running backend — only the Next.js dev server.

### 401 → login loop avoidance

The admin-client axios interceptor redirects to `/admin/login` on any 401 response.
For the "error state" test on the login page itself, mocking with `status: 422` instead
of `401` ensures the redirect loop doesn't fire and the error message is displayed.

### Desktop + mobile nav duplication

`PublicNav` renders both a desktop and a mobile nav. Any locator targeting nav links
by name (e.g. "Pricing", "Sign in") will find 2 elements and fail Playwright's strict
mode. Fixed by calling `.first()` on the locator before asserting visibility.

### Auth0 redirect tests

Student and school portal layouts call `auth0.getSession()` server-side. With the
fake Auth0 env vars injected via `webServer.env`, the client initialises without
crashing; with no real session cookie, `getSession()` returns `null` and the layout
calls `redirect("/login")` or `redirect("/school/login")` as expected.

---

## Exit Criteria Met

- ✅ 34 Playwright E2E tests passing (chromium)
- ✅ Admin portal: login, error, success, redirect, dashboard, analytics, health, pipeline, content review, RBAC
- ✅ Auth redirects: student/school/admin unauthenticated access all redirect correctly
- ✅ Login pages: school + admin structure verified
- ✅ Vitest unit tests: 99 passing (no regressions)
- ✅ Typecheck clean
- ✅ 56-route production build

---

## Phase W8 Preview

Candidates for W8:

- Playwright E2E tests for school portal authenticated flows (requires an Auth0 test tenant or session cookie injection)
- Accessibility audit (axe-playwright, WCAG 2.1 AA checks on all three portals)
- Bundle analysis and performance optimisation (next/bundle-analyzer, dynamic imports for heavy pages)
- Sentry error monitoring integration (`@sentry/nextjs`)
