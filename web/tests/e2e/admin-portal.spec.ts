import { test, expect } from "@playwright/test";

/**
 * Admin portal E2E tests.
 *
 * Auth strategy: inject a mock JWT into localStorage via page.addInitScript()
 * before navigation. All backend API calls are intercepted with page.route()
 * so no real backend is needed.
 */

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function makeAdminJwt(role: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(
    JSON.stringify({ admin_id: "test-admin", role, exp: 9999999999 }),
  ).toString("base64url");
  return `${header}.${payload}.sig`;
}

const SUPER_TOKEN = makeAdminJwt("super_admin");
const DEV_TOKEN = makeAdminJwt("developer");

// ---------------------------------------------------------------------------
// Shared API stubs
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function stubAdminApis(page: any) {
  await page.route("**/api/v1/admin/analytics/subscriptions", (route: any) =>
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
  await page.route("**/api/v1/admin/pipeline/status", (route: any) =>
    route.fulfill({ status: 200, json: { jobs: [] } }),
  );
  await page.route("**/api/v1/admin/analytics/struggle", (route: any) =>
    route.fulfill({ status: 200, json: { units: [], generated_at: new Date().toISOString() } }),
  );
  await page.route("**/api/v1/admin/content-review/queue**", (route: any) =>
    route.fulfill({ status: 200, json: { items: [], total: 0 } }),
  );
  await page.route("**/api/v1/health", (route: any) =>
    route.fulfill({
      status: 200,
      json: {
        db_status: "ok",
        redis_status: "ok",
        db_pool_size: 20,
        db_pool_available: 18,
        checked_at: new Date().toISOString(),
      },
    }),
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

test.describe("Admin dashboard", () => {
  test.beforeEach(async ({ page }) => {
    const token = SUPER_TOKEN;
    await page.addInitScript((t) => localStorage.setItem("sb_admin_token", t), token);
    await stubAdminApis(page);
  });

  test("loads and shows Platform Dashboard heading", async ({ page }) => {
    await page.goto("/admin/dashboard");
    await expect(page.getByRole("heading", { name: /platform dashboard/i })).toBeVisible();
  });

  test("shows Subscriptions section", async ({ page }) => {
    await page.goto("/admin/dashboard");
    await expect(page.getByText(/subscriptions/i)).toBeVisible();
  });

  test("shows Pipeline section heading", async ({ page }) => {
    await page.goto("/admin/dashboard");
    // Use the h2 section heading specifically — getByText matches multiple elements
    await expect(
      page.getByRole("heading", { name: "Pipeline" }),
    ).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Analytics
// ---------------------------------------------------------------------------

test.describe("Admin analytics", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((t) => localStorage.setItem("sb_admin_token", t), SUPER_TOKEN);
    await stubAdminApis(page);
  });

  test("loads and shows Platform Analytics heading", async ({ page }) => {
    await page.goto("/admin/analytics");
    await expect(page.getByRole("heading", { name: /platform analytics/i })).toBeVisible();
  });

  test("shows Subscription Breakdown section", async ({ page }) => {
    await page.goto("/admin/analytics");
    await expect(page.getByText(/subscription breakdown/i)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

test.describe("Admin health page", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((t) => localStorage.setItem("sb_admin_token", t), SUPER_TOKEN);
    await stubAdminApis(page);
  });

  test("loads and shows System Health heading", async ({ page }) => {
    await page.goto("/admin/health");
    await expect(page.getByRole("heading", { name: /system health/i })).toBeVisible();
  });

  test("shows PostgreSQL and Redis service rows", async ({ page }) => {
    await page.goto("/admin/health");
    await expect(page.getByText("PostgreSQL")).toBeVisible();
    await expect(page.getByText("Redis")).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Pipeline
// ---------------------------------------------------------------------------

test.describe("Admin pipeline page", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((t) => localStorage.setItem("sb_admin_token", t), SUPER_TOKEN);
    await stubAdminApis(page);
  });

  test("loads and shows Pipeline Jobs heading", async ({ page }) => {
    await page.goto("/admin/pipeline");
    await expect(page.getByRole("heading", { name: /pipeline jobs/i })).toBeVisible();
  });

  test("shows Trigger job button", async ({ page }) => {
    await page.goto("/admin/pipeline");
    await expect(page.getByRole("link", { name: /trigger job/i })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Content review
// ---------------------------------------------------------------------------

test.describe("Admin content review", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((t) => localStorage.setItem("sb_admin_token", t), SUPER_TOKEN);
    await stubAdminApis(page);
  });

  test("loads and shows Content Review Queue heading", async ({ page }) => {
    await page.goto("/admin/content-review");
    await expect(page.getByRole("heading", { name: /content review queue/i })).toBeVisible();
  });

  test("shows status filter tabs", async ({ page }) => {
    await page.goto("/admin/content-review");
    await expect(page.getByRole("button", { name: /pending/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /published/i })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// RBAC: nav items differ by role
// ---------------------------------------------------------------------------

test.describe("Admin nav RBAC", () => {
  test("super_admin sees Feedback in sidebar", async ({ page }) => {
    await page.addInitScript((t) => localStorage.setItem("sb_admin_token", t), SUPER_TOKEN);
    await stubAdminApis(page);
    await page.goto("/admin/dashboard");
    await expect(page.getByRole("link", { name: /feedback/i })).toBeVisible();
  });

  test("developer does not see Feedback in sidebar", async ({ page }) => {
    await page.addInitScript((t) => localStorage.setItem("sb_admin_token", t), DEV_TOKEN);
    await stubAdminApis(page);
    await page.goto("/admin/dashboard");
    await expect(page.getByRole("link", { name: /^Feedback$/i })).not.toBeVisible();
  });
});
