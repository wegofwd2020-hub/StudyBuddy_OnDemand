/**
 * E2E test for /school/login — now a redirect to /signin.
 *
 * /school/login used to be the local-auth form; it was folded into the unified
 * /signin page in the universal-login refactor. The page is kept alive as a
 * redirect so existing emails / bookmarks continue to work.
 *
 * Run with:
 *   npx playwright test school-login-page
 */

import { test, expect } from "@playwright/test";

test("/school/login redirects to /signin", async ({ page }) => {
  await page.goto("/school/login");
  await expect(page).toHaveURL(/\/signin$/);
});
