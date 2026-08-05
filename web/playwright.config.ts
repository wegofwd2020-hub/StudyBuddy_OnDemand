import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  // QUIZ_SUITE forces a single worker: the quiz-suite project's specs share a
  // live backend/content-store fixture (no route mocks), and
  // quiz-failure.spec.ts's mid-quiz test intentionally deletes and restores
  // the SAME unit's real quiz files that quiz-journey.spec.ts grades against
  // (both files match testMatch "**/e2e/quiz-suite/*.spec.ts"). Under
  // fullyParallel with >1 worker those can race — verified: an earlier
  // version of this fix (which restored via a full DB reseed rather than
  // this worker change) hit a real cross-file "Incorrect email or password"
  // failure. Forcing one worker makes execution order deterministic so the
  // destructive test's own cleanup always completes before the next test
  // starts, whichever file it's in. Scoped to QUIZ_SUITE only — no effect on
  // the rest of the suite.
  workers: process.env.QUIZ_SUITE ? 1 : process.env.CI ? 1 : undefined,

  reporter: [["html", { open: "never" }], ["list"]],

  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    // ── Existing tests (auth redirects, public pages, admin smoke) ─────────
    {
      name: "chromium",
      testMatch: [
        "**/e2e/auth-redirects.spec.ts",
        "**/e2e/student-auth-redirects.spec.ts",
        "**/e2e/school-auth-redirects.spec.ts",
        "**/e2e/admin-portal.spec.ts",
        "**/e2e/landing-page.spec.ts",
        "**/e2e/login-pages.spec.ts",
        "**/e2e/student-login-page.spec.ts",
        "**/e2e/school-login-page.spec.ts",
        "**/e2e/signin-page.spec.ts",
        "**/e2e/pricing-page.spec.ts",
        "**/e2e/public.spec.ts",
        "**/e2e/static-pages.spec.ts",
        "**/e2e/student_flow.spec.ts",
      ],
      use: { ...devices["Desktop Chrome"] },
    },

    // ── Persona: Student ──────────────────────────────────────────────────
    {
      name: "persona-student",
      testMatch: "**/e2e/personas/student-accessibility.spec.ts",
      use: { ...devices["Desktop Chrome"] },
    },

    // ── Persona: Teacher / School Admin ───────────────────────────────────
    {
      name: "persona-teacher",
      testMatch: [
        "**/e2e/personas/teacher-accessibility.spec.ts",
        "**/e2e/personas/school-admin-curriculum-flow.spec.ts",
      ],
      use: { ...devices["Desktop Chrome"] },
    },

    // ── Persona: Super Admin ──────────────────────────────────────────────
    {
      name: "persona-admin",
      testMatch: "**/e2e/personas/admin-accessibility.spec.ts",
      use: { ...devices["Desktop Chrome"] },
    },

    // ── Quiz suite (live stack, NO route mocks) ───────────────────────────
    // Env-gated so `npx playwright test` never runs it: it needs a seeded
    // fixture and a live backend. scripts/quiz_suite.sh sets QUIZ_SUITE=1.
    ...(process.env.QUIZ_SUITE
      ? [
          {
            name: "quiz-suite",
            testMatch: "**/e2e/quiz-suite/*.spec.ts",
            use: { ...devices["Desktop Chrome"] },
          },
        ]
      : []),
  ],

  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    // Fake Auth0 env vars so the @auth0/nextjs-auth0 v4 Auth0Client initialises
    // without crashing. With no real session cookie present getSession() returns
    // null → layout redirects as expected; persona tests use the dev-session
    // cookie instead. v4 renamed these: AUTH0_DOMAIN (not AUTH0_ISSUER_BASE_URL)
    // and APP_BASE_URL (not AUTH0_BASE_URL); a missing AUTH0_DOMAIN aborts boot
    // (same fix as CI's e2e.yml, #535) so local `npx playwright test` never
    // started the dev server.
    env: {
      AUTH0_SECRET: "test-auth0-secret-for-e2e-testing-only-placeholder",
      AUTH0_DOMAIN: "test.auth0.com",
      APP_BASE_URL: "http://localhost:3000",
      AUTH0_CLIENT_ID: "test_client_id",
      AUTH0_CLIENT_SECRET: "test_client_secret",
      NEXT_PUBLIC_API_URL: "http://localhost:8000/api/v1",
    },
  },
});
