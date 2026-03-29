import { test, expect } from "@playwright/test";

/**
 * Tests for the public login pages: school login and admin login.
 * Neither page requires an active session.
 */

test.describe("School login page", () => {
  test("renders Sign In button", async ({ page }) => {
    await page.goto("/school/login");
    // Exact button text from i18n auth.login_btn
    await expect(
      page.getByRole("link", { name: "Sign in with school account" }),
    ).toBeVisible();
  });

  test("links to student login", async ({ page }) => {
    await page.goto("/school/login");
    await expect(page.getByRole("link", { name: /student login/i })).toBeVisible();
  });

  test("links to contact page", async ({ page }) => {
    await page.goto("/school/login");
    await expect(page.getByRole("link", { name: /contact us/i })).toBeVisible();
  });
});

test.describe("Admin login page", () => {
  test("renders email and password fields", async ({ page }) => {
    await page.goto("/admin/login");
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
  });

  test("shows sign in button", async ({ page }) => {
    await page.goto("/admin/login");
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("shows error on failed login attempt", async ({ page }) => {
    // Use 422 (not 401) — the admin-client interceptor redirects on 401,
    // which would navigate away before the error message is displayed.
    await page.route("**/api/v1/admin/auth/login", (route) =>
      route.fulfill({ status: 422, json: { detail: "Invalid credentials" } }),
    );

    await page.goto("/admin/login");
    await page.getByLabel(/email/i).fill("bad@example.com");
    await page.getByLabel(/password/i).fill("wrongpassword");
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page.getByText(/invalid credentials/i)).toBeVisible();
  });

  test("stores token and redirects to dashboard on success", async ({ page }) => {
    const fakeToken = makeAdminJwt("super_admin");

    await page.route("**/api/v1/admin/auth/login", (route) =>
      route.fulfill({
        status: 200,
        json: { token: fakeToken, admin_id: "test-admin" },
      }),
    );

    // Mock the dashboard analytics calls so the dashboard renders cleanly
    await page.route("**/api/v1/admin/analytics/subscriptions", (route) =>
      route.fulfill({
        status: 200,
        json: {
          active_monthly: 150,
          active_annual: 80,
          total_active: 230,
          mrr_usd: 2485,
          new_this_month: 18,
          cancelled_this_month: 5,
          churn_rate: 0.022,
        },
      }),
    );

    await page.route("**/api/v1/admin/pipeline/status", (route) =>
      route.fulfill({ status: 200, json: { jobs: [] } }),
    );

    await page.goto("/admin/login");
    await page.getByLabel(/email/i).fill("admin@studybuddy.ca");
    await page.getByLabel(/password/i).fill("correct-password");
    await page.getByRole("button", { name: /sign in/i }).click();

    await page.waitForURL("/admin/dashboard");
    const token = await page.evaluate(() => localStorage.getItem("sb_admin_token"));
    expect(token).toBe(fakeToken);
  });
});

// ---------------------------------------------------------------------------
// Helper: build a fake admin JWT with a decodable payload
// ---------------------------------------------------------------------------

function makeAdminJwt(role: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString(
    "base64url",
  );
  const payload = Buffer.from(
    JSON.stringify({ admin_id: "test-admin", role, exp: 9999999999 }),
  ).toString("base64url");
  return `${header}.${payload}.sig`;
}
