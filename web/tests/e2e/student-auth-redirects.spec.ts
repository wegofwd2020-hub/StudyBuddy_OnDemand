/**
 * E2E tests for section 2.1 — Student Portal Auth Redirects
 * Covers TC-IDs: STU-01, STU-02, STU-03 (+ auxiliary student routes)
 *
 * Precondition: no Auth0 session (test env uses fake env vars; getSession()
 * returns null → server-side layout calls redirect("/login")).
 *
 * Run with:
 *   npx playwright test student-auth-redirects
 */

import { test, expect } from "@playwright/test";
import { REDIRECT_TARGET, STUDENT_PROTECTED_ROUTES } from "./data/student-auth-redirects";

for (const { tcId, path, description } of STUDENT_PROTECTED_ROUTES) {
  test(`${tcId} — unauthenticated "${description}" (${path}) redirects to ${REDIRECT_TARGET}`, async ({
    page,
  }) => {
    const response = await page.goto(path);

    // Must land on /login — not a 500
    await expect(page).toHaveURL(new RegExp(REDIRECT_TARGET));
    expect(response?.status()).not.toBe(500);
  });
}
