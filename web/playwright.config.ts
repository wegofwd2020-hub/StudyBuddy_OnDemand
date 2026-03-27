import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    // Fake Auth0 env vars so auth0.getSession() initialises without crashing.
    // With no real session cookie present it returns null → layout redirects as expected.
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
