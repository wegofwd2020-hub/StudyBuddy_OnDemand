import { test, expect } from "@playwright/test";

/**
 * Verify that unauthenticated access to protected routes redirects correctly.
 *
 * Student / school portals use Auth0 server-side session (getSession() returns
 * null with fake env vars → layout calls redirect()).
 *
 * Admin portal uses a client-side localStorage check in a "use client" layout,
 * so it redirects via useEffect on the client after initial render.
 */

test.describe("Student portal auth redirects", () => {
  test("/dashboard redirects to /login when no session", async ({ page }) => {
    const res = await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
    // Must not be a 500 — auth0.getSession() returns null gracefully
    expect(res?.status()).not.toBe(500);
  });

  test("/subjects redirects to /login when no session", async ({ page }) => {
    await page.goto("/subjects");
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("School portal auth redirects", () => {
  test("/school/dashboard redirects to /school/login when no session", async ({
    page,
  }) => {
    await page.goto("/school/dashboard");
    await expect(page).toHaveURL(/\/school\/login/);
  });

  test("/school/reports/overview redirects to /school/login when no session", async ({
    page,
  }) => {
    await page.goto("/school/reports/overview");
    await expect(page).toHaveURL(/\/school\/login/);
  });
});

test.describe("Admin portal auth redirects", () => {
  test("/admin/dashboard redirects to /admin/login when no token", async ({ page }) => {
    // Ensure localStorage is clean (no sb_admin_token)
    await page.addInitScript(() => localStorage.removeItem("sb_admin_token"));
    await page.goto("/admin/dashboard");
    await expect(page).toHaveURL(/\/admin\/login/);
  });

  test("/admin/analytics redirects to /admin/login when no token", async ({ page }) => {
    await page.addInitScript(() => localStorage.removeItem("sb_admin_token"));
    await page.goto("/admin/analytics");
    await expect(page).toHaveURL(/\/admin\/login/);
  });
});
