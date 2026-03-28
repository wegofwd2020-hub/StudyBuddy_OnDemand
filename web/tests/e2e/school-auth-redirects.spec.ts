/**
 * E2E tests for section 3.1 — School Portal Auth Redirects
 * Covers TC-IDs: SCH-01, SCH-02 (+ auxiliary school routes)
 *
 * Precondition: no Auth0 session (test env uses fake env vars; getSession()
 * returns null → server-side layout calls redirect("/school/login")).
 *
 * Run with:
 *   npx playwright test school-auth-redirects
 */

import { test, expect } from "@playwright/test";
import { REDIRECT_TARGET, SCHOOL_PROTECTED_ROUTES } from "./data/school-auth-redirects";

for (const { tcId, path, description } of SCHOOL_PROTECTED_ROUTES) {
  test(`${tcId} — unauthenticated "${description}" (${path}) redirects to ${REDIRECT_TARGET}`, async ({
    page,
  }) => {
    const response = await page.goto(path);

    // Must land on /school/login — not a 500
    await expect(page).toHaveURL(new RegExp(REDIRECT_TARGET));
    expect(response?.status()).not.toBe(500);
  });
}
