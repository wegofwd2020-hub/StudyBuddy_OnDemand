/**
 * tests/e2e/personas/admin-accessibility.spec.ts
 *
 * Accessibility (WCAG 2.1 AA) and smoke tests for the Super Admin persona.
 *
 * Auth strategy:
 *   - sb_admin_token in localStorage → decoded by the client-side admin layout
 *
 * All backend API calls are intercepted with page.route() — no live backend needed.
 *
 * Note: smoke functionality tests for the admin portal already exist in
 * admin-portal.spec.ts.  This file focuses on WCAG coverage and extends
 * role coverage to developer and product_admin roles.
 */

import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { checkA11y } from "../helpers/axe";
import { makeAdminToken } from "../helpers/tokens";

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------

const SUPER_TOKEN = makeAdminToken("super_admin");
const DEV_TOKEN = makeAdminToken("developer");
const PRODUCT_TOKEN = makeAdminToken("product_admin");

async function setupAdminAuth(page: Page, token: string) {
  await page.addInitScript((t) => localStorage.setItem("sb_admin_token", t), token);
}

// ---------------------------------------------------------------------------
// API stubs (same shape as admin-portal.spec.ts — kept self-contained)
// ---------------------------------------------------------------------------

async function stubAdminApis(page: Page) {
  await page.route("**/api/v1/admin/analytics/subscriptions**", (route) =>
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

  await page.route("**/api/v1/admin/pipeline/status**", (route) =>
    route.fulfill({ status: 200, json: { jobs: [] } }),
  );

  await page.route("**/api/v1/admin/analytics/struggle**", (route) =>
    route.fulfill({
      status: 200,
      json: { units: [], generated_at: new Date().toISOString() },
    }),
  );

  await page.route("**/api/v1/admin/content-review/queue**", (route) =>
    route.fulfill({ status: 200, json: { items: [], total: 0 } }),
  );

  await page.route("**/api/v1/admin/feedback**", (route) =>
    route.fulfill({
      status: 200,
      json: {
        items: [
          {
            feedback_id: "fb-001",
            student_id: "stu-001",
            category: "content",
            message: "The algebra lesson was really clear.",
            submitted_at: new Date().toISOString(),
            reviewed: false,
          },
        ],
        total: 1,
      },
    }),
  );

  await page.route("**/api/v1/admin/audit**", (route) =>
    route.fulfill({
      status: 200,
      json: { entries: [], total: 0 },
    }),
  );

  await page.route("**/api/v1/health**", (route) =>
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

  await page.route("**/api/v1/admin/analytics/platform**", (route) =>
    route.fulfill({
      status: 200,
      json: {
        total_students: 1240,
        active_last_30d: 870,
        lessons_served: 18500,
        quizzes_completed: 9200,
        avg_pass_rate: 0.74,
      },
    }),
  );

  // Catch-all
  await page.route("**/api/v1/**", (route) => route.fulfill({ status: 200, json: {} }));
}

// ---------------------------------------------------------------------------
// Tests: Super Admin — accessibility sweep
// ---------------------------------------------------------------------------

test.describe("Admin persona (super_admin) — accessibility", () => {
  test.beforeEach(async ({ page }) => {
    await setupAdminAuth(page, SUPER_TOKEN);
    await stubAdminApis(page);
  });

  test("dashboard — no critical WCAG violations", async ({ page }) => {
    await page.goto("/admin/dashboard");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Admin — Dashboard");
  });

  test("analytics — no critical WCAG violations", async ({ page }) => {
    await page.goto("/admin/analytics");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Admin — Analytics");
  });

  test("health — no critical WCAG violations", async ({ page }) => {
    await page.goto("/admin/health");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Admin — System Health");
  });

  test("pipeline — no critical WCAG violations", async ({ page }) => {
    await page.goto("/admin/pipeline");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Admin — Pipeline");
  });

  test("content review queue — no critical WCAG violations", async ({ page }) => {
    await page.goto("/admin/content-review");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Admin — Content Review");
  });

  test("feedback — no critical WCAG violations", async ({ page }) => {
    await page.goto("/admin/feedback");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Admin — Feedback");
  });

  test("audit log — no critical WCAG violations", async ({ page }) => {
    await page.goto("/admin/audit");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Admin — Audit Log");
  });
});

// ---------------------------------------------------------------------------
// Tests: Role differences
// ---------------------------------------------------------------------------

test.describe("Admin persona — role-based nav differences", () => {
  test("super_admin sees all nav items including Feedback and Audit", async ({
    page,
  }) => {
    await setupAdminAuth(page, SUPER_TOKEN);
    await stubAdminApis(page);
    await page.goto("/admin/dashboard");
    await expect(page.getByRole("link", { name: /feedback/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /audit/i })).toBeVisible();
  });

  test("developer sees Pipeline and Health but not Feedback", async ({ page }) => {
    await setupAdminAuth(page, DEV_TOKEN);
    await stubAdminApis(page);
    await page.goto("/admin/dashboard");
    await expect(page.getByRole("link", { name: /pipeline/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /^Feedback$/i })).not.toBeVisible();
  });

  test("product_admin sees Analytics and Content Review", async ({ page }) => {
    await setupAdminAuth(page, PRODUCT_TOKEN);
    await stubAdminApis(page);
    await page.goto("/admin/dashboard");
    await expect(page.getByRole("link", { name: /analytics/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /content review/i })).toBeVisible();
  });

  test("all three roles — no critical WCAG violations on dashboard", async ({ page }) => {
    for (const [label, token] of [
      ["super_admin", SUPER_TOKEN],
      ["developer", DEV_TOKEN],
      ["product_admin", PRODUCT_TOKEN],
    ] as const) {
      await page.addInitScript((t) => localStorage.setItem("sb_admin_token", t), token);
      await stubAdminApis(page);
      await page.goto("/admin/dashboard");
      await page.waitForLoadState("networkidle");
      await checkA11y(page, `Admin — Dashboard (${label})`);
      // Reset for next iteration
      await page.evaluate(() => localStorage.clear());
    }
  });
});
