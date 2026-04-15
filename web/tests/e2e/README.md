# End-to-End Testing with Playwright

Runbook for running and writing Playwright tests for the StudyBuddy web
app. Last refreshed 2026-04-15.

**TL;DR — to run the suite:**

```bash
cd web
npx playwright test                     # full suite, headless
npx playwright test --ui                # interactive mode (recommended while debugging)
npx playwright test --project=chromium  # just the public / auth / smoke tests
```

---

## 1. One-time setup

### 1.1 Prerequisites

- Node 20+ on the **host** (not inside the Docker `web` container — see §6).
- The backend, frontend, and database containers running via `./dev_start.sh`.
  Playwright tests hit `http://localhost:3000` with mocked API responses, so
  no real backend state is required, but the Next.js dev server must be up.

### 1.2 Install npm dependencies on the host

```bash
cd web
npm install
```

This installs `@playwright/test`, `@axe-core/playwright`, and everything
else from `package.json` into your **host** `node_modules` (distinct from
the container's `node_modules`).

### 1.3 Install Playwright browser binaries

```bash
npx playwright install chromium
```

Downloads Chromium Headless Shell (~112 MB) to `~/.cache/ms-playwright/`.
Only chromium is wired today — Firefox and WebKit targets are not in the
Playwright config.

To update browsers later (e.g. when Playwright is upgraded), re-run
`npx playwright install chromium`.

---

## 2. Running tests

### 2.1 Full suite

```bash
cd web
npx playwright test
```

Runs all **four** Playwright projects in parallel:

| Project | Files | What it covers |
|---|---|---|
| `chromium` | `landing-page.spec.ts`, `login-pages.spec.ts`, `auth-redirects.spec.ts`, `admin-portal.spec.ts`, `public.spec.ts`, `pricing-page.spec.ts`, `static-pages.spec.ts`, `student_flow.spec.ts` | Public pages, login flows, auth-redirect rules, admin portal smoke |
| `persona-student` | `personas/student-accessibility.spec.ts` | Student-role pages with mocked APIs + axe WCAG 2.1 AA checks |
| `persona-teacher` | `personas/teacher-accessibility.spec.ts`, `personas/school-admin-curriculum-flow.spec.ts` | Teacher / school-admin pages with mocked APIs + axe; new school-admin curriculum-submission flow (#188) |
| `persona-admin` | `personas/admin-accessibility.spec.ts` | Super-admin / product-admin / developer / tester pages; role-based nav differences |

Expected outcome: **120 passing, ~8 `fixme`'d, 0 failing**. Run time: ~2 min.

### 2.2 Run one project

```bash
npx playwright test --project=chromium
npx playwright test --project=persona-student
npx playwright test --project=persona-teacher
npx playwright test --project=persona-admin
```

### 2.3 Run one spec file

```bash
npx playwright test tests/e2e/landing-page.spec.ts
npx playwright test tests/e2e/personas/school-admin-curriculum-flow.spec.ts
```

### 2.4 Run one test by title

```bash
npx playwright test -g "landing page loads and shows hero CTA"
```

### 2.5 Interactive UI mode (recommended while debugging)

```bash
npx playwright test --ui
```

Opens a Chromium-based test runner with:
- Time-travel: hover any step to see the DOM snapshot at that moment.
- Pick-locator: click an element in the snapshot to auto-generate a
  Playwright locator expression.
- Watch mode: re-runs the test on file save.
- Filter by project, status, file.

### 2.6 Record a new spec from the browser

```bash
npx playwright codegen http://localhost:3000
```

Opens a real browser + a second window with generated spec code. Every
click, fill, and navigation appends to the generated code. Copy into a
new `*.spec.ts` file as a starting point, then edit to add assertions.

### 2.7 Show the HTML report of the last run

```bash
npx playwright show-report
```

Opens `playwright-report/index.html` with per-test results, screenshots
of failures, videos (if enabled), and trace links.

---

## 3. Understanding a failure

Playwright fails loudly — the terminal output shows:

- The assertion that failed.
- A screenshot at the moment of failure (saved under
  `test-results/<test>/test-failed-1.png`).
- The full call log leading up to the failure.
- If `trace: "on-first-retry"` was triggered, a trace zip for time-travel
  replay (open with `npx playwright show-trace test-results/.../trace.zip`).

### 3.1 Common failure patterns

| Symptom | Likely cause | Fix |
|---|---|---|
| `Error: element(s) not found` with a selector that worked yesterday | UI copy changed | Update the selector in the spec (prefer roles + accessible names over raw text) |
| `Error: strict mode violation: getByRole(...) resolved to N elements` | Multiple elements match (e.g. duplicate sidebar + footer links) | Add `.first()` or narrow with a parent locator |
| `Error: browserType.launch: Executable doesn't exist` | Browser binary missing | `npx playwright install chromium` |
| `Error: spawn ... ENOENT` + `__memset_chk: symbol not found` | Running Playwright inside the Alpine container | Run on host instead — see §6 |
| `Timeout: 5000ms` waiting for a network request | Mock route doesn't match the real URL pattern | Run with `--trace=on` and inspect the network panel; tighten the route glob |
| Color-contrast / html-has-lang / document-title axe failures | Known debt tracked in issue #189 | Do NOT add more rules to `KNOWN_A11Y_EXCLUSIONS` — fix the app |

### 3.2 Debugging with trace

Re-run the failing test with trace always on:

```bash
npx playwright test tests/e2e/personas/school-admin-curriculum-flow.spec.ts --trace=on
npx playwright show-trace test-results/.../trace.zip
```

The trace viewer shows every action, network request, console message,
and DOM snapshot. Use it to figure out why a selector didn't match or
why a route wasn't intercepted.

---

## 4. Writing new tests

### 4.1 Where tests live

```
web/tests/e2e/
├── landing-page.spec.ts              ← public page specs (chromium project)
├── login-pages.spec.ts
├── ... (more public / auth specs)
├── personas/
│   ├── student-accessibility.spec.ts ← persona-student project
│   ├── teacher-accessibility.spec.ts ← persona-teacher project
│   ├── admin-accessibility.spec.ts   ← persona-admin project
│   └── school-admin-curriculum-flow.spec.ts ← also persona-teacher
├── data/                             ← test data constants (strings, IDs, fixtures)
└── helpers/                          ← shared auth, token, axe helpers
```

### 4.2 Pick the right project

| If your test needs... | Put it here |
|---|---|
| A logged-out public page | New `*.spec.ts` under `tests/e2e/`; extend the `chromium` `testMatch` glob in `playwright.config.ts` |
| A logged-in student | `personas/*.spec.ts`; use the `persona-student` project; reuse `setupStudentAuth()` from `student-accessibility.spec.ts` |
| A logged-in teacher / school_admin | `personas/*.spec.ts`; use the `persona-teacher` project; reuse `setupTeacherAuth()` |
| A logged-in super-admin / product-admin / developer | `personas/*.spec.ts`; use the `persona-admin` project; reuse `setupAdminAuth()` + `SUPER_TOKEN` / `PRODUCT_TOKEN` / `DEV_TOKEN` |

### 4.3 Auth setup for persona tests

The three personas use different JWT-signing tracks but the pattern is
the same: write a mock JWT to `localStorage` under the right key, and
(for teacher / student) add a dev-session cookie so the server-side
layout doesn't redirect to login.

```typescript
import { makeStudentToken, devSessionCookie } from "../helpers/tokens";

async function setupAuth(page: Page) {
  await page.context().addCookies([devSessionCookie("Test Student", "test@invalid")]);
  await page.addInitScript(
    (token) => localStorage.setItem("sb_token", token),
    makeStudentToken(),
  );
}
```

`helpers/tokens.ts` exports:
- `makeStudentToken()` → stored as `sb_token`
- `makeTeacherToken(teacherId, schoolId, role)` → stored as `sb_teacher_token`
- `makeAdminToken(role)` → stored as `sb_admin_token`
- `devSessionCookie(name, email)` → cookie descriptor for student / teacher tracks

These JWTs are signed with `alg: "none"` — **for tests only**, they're
not valid against any real backend. Every API call in persona tests
must be intercepted by `page.route(...)`.

### 4.4 Mock all API calls

Persona tests never hit the real backend. Every endpoint the page
fetches must be stubbed with `page.route()`:

```typescript
await page.route("**/api/v1/curriculum/tree**", (route) =>
  route.fulfill({ status: 200, json: { subjects: [...] } }),
);
```

Always include a **catch-all** at the end so unexpected calls don't
hang the test on a timeout:

```typescript
await page.route("**/api/v1/**", (route) =>
  route.fulfill({ status: 200, json: {} }),
);
```

### 4.5 Prefer role-based locators

Order of preference:

1. `page.getByRole("button", { name: /sign in/i })` — matches the
   accessible name. Survives CSS refactors.
2. `page.getByLabel(/email/i)` — form inputs by their label.
3. `page.getByText(/stable heading text/i)` — prose assertion.
4. `page.locator('a[href="/admin/feedback"]')` — href/attribute match.
   Use for nav links where DOM presence is the signal, not visibility
   (scrollable sidebars fail `toBeVisible()` for items past the fold).
5. `page.locator("#specific-id")` or CSS selector — last resort.

### 4.6 Accessibility assertions

Import from `helpers/axe`:

```typescript
import { checkA11y } from "../helpers/axe";

test("page has no critical WCAG violations", async ({ page }) => {
  await page.goto("/some/page");
  await page.waitForLoadState("networkidle");
  await checkA11y(page, "My Page", KNOWN_A11Y_EXCLUSIONS);
});
```

The third argument is an optional list of axe rule IDs to disable.
Default is `[]` — do not add to the known-exclusion list in persona
specs without filing a GitHub issue first (currently tracked in #189).

---

## 5. The `KNOWN_A11Y_EXCLUSIONS` technical debt

The three persona specs disable three axe rules:

```typescript
const KNOWN_A11Y_EXCLUSIONS = [
  "color-contrast",
  "html-has-lang",
  "document-title",
] as const;
```

Each is tracked in GitHub issue **#189** with root-cause hypothesis +
fix approach. Do NOT add more rules without:

1. Filing a tracking issue.
2. Linking it in the comment block above the constant.
3. Documenting why the rule can't be fixed immediately.

The long-term goal is for this array to be `[]`.

---

## 6. Why Playwright runs on the host, not in Docker

The `web` container uses `node:20-alpine`, which ships with **musl libc**.
Playwright's Chromium binary is compiled against **glibc** and fails to
spawn inside Alpine with:

```
Error relocating chrome-headless-shell: __memset_chk: symbol not found
```

Options we rejected:
- Switching the container base to Debian / Ubuntu — larger image, no
  other benefit given the host has Node installed already.
- Using Playwright's official `mcr.microsoft.com/playwright` Docker image
  — doubles the container footprint just for tests; not worth the
  complexity for a local-dev tool.

The host-based approach works reliably and matches how most developers
run Playwright in practice. The only onboarding step is `npx playwright
install chromium` after cloning.

---

## 7. The `fixme` register

Some tests are marked `test.fixme(...)` — they don't run, but the spec
skeleton stays visible as a to-do list.

| Spec | Test | Reason |
|---|---|---|
| `landing-page.spec.ts` | PUB-03 — primary CTA | Hero CTAs changed to `<DemoRequestModal />`; needs rewrite to assert modal behaviour |
| `landing-page.spec.ts` | PUB-04 — secondary CTA | Same UX change; "See how it works" became a text link to `/tour` |
| `school-admin-curriculum-flow.spec.ts` | (6 tests) | Wizard happy-path skeleton; each fixme carries notes on what the per-step field fills need |

To unfixme a test, change `test.fixme(...)` back to `test(...)` and make
it pass.

---

## 8. CI integration (not yet wired)

The suite is intended to run on every PR via GitHub Actions but is not
yet wired. When it is:

- CI will set `CI=true` which enables `forbidOnly`, 2 retries per test,
  and 1 worker (serial) to avoid noisy-neighbour flake.
- CI needs to download Chromium — add
  `npx playwright install --with-deps chromium` to the workflow.
- The Next.js dev server is started automatically via
  `playwright.config.ts` `webServer` block — it reuses an existing
  server in dev but starts fresh in CI.

File a separate issue when wiring CI; until then, running the suite
locally before pushing is the expected discipline.

---

## 9. Useful links

- Playwright docs: https://playwright.dev/docs/intro
- Locators guide: https://playwright.dev/docs/locators
- Trace viewer: https://playwright.dev/docs/trace-viewer
- Axe rule reference: https://dequeuniversity.com/rules/axe/latest
- Related issues:
  [#188](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/188)
  (school-admin test case),
  [#189](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/189)
  (a11y rule exclusions).
