import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

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
        "**/e2e/pricing-page.spec.ts",
        "**/e2e/public.spec.ts",
        "**/e2e/static-pages.spec.ts",
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
      testMatch: "**/e2e/personas/teacher-accessibility.spec.ts",
      use: { ...devices["Desktop Chrome"] },
    },

    // ── Persona: Super Admin ──────────────────────────────────────────────
    {
      name: "persona-admin",
      testMatch: "**/e2e/personas/admin-accessibility.spec.ts",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    // Fake Auth0 env vars so auth0.getSession() initialises without crashing.
    // With no real session cookie present it returns null → layout redirects as expected.
    // Dev-session cookie is used instead in persona tests.
    env: {
      AUTH0_SECRET: "test-auth0-secret-for-e2e-testing-only-placeholder",
      AUTH0_BASE_URL: "http://localhost:3000",
      AUTH0_ISSUER_BASE_URL: "https://test.auth0.example.com",
      AUTH0_CLIENT_ID: "test_client_id",
      AUTH0_CLIENT_SECRET: "test_client_secret",
      NEXT_PUBLIC_API_URL: "http://localhost:8000/api/v1",
    },
  },
});
