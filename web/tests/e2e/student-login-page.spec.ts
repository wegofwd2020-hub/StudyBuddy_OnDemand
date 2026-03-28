/**
 * E2E tests for section 1.3 — Student Login Page (`/login`)
 * Covers TC-IDs: PUB-17, PUB-18
 *
 * Run with:
 *   npx playwright test student-login-page
 */

import { test, expect } from "@playwright/test";
import {
  PAGE,
  SIGN_IN_LINK,
  SIGN_UP_LINK,
  SUPPORTING_LINKS,
} from "./data/student-login-page";

// ---------------------------------------------------------------------------
// Page load
// ---------------------------------------------------------------------------

test("page loads at /login with correct heading and subtitle", async ({ page }) => {
  await page.goto(PAGE.url);

  await expect(page.getByText(PAGE.title)).toBeVisible();
  await expect(page.getByText(PAGE.subtitle)).toBeVisible();
});

// ---------------------------------------------------------------------------
// PUB-17 — Sign-in button (Auth0 link) is visible with correct href
// ---------------------------------------------------------------------------

test("PUB-17 — sign-in link renders and points to Auth0 endpoint", async ({ page }) => {
  await page.goto(PAGE.url);

  const link = page.getByRole("link", { name: SIGN_IN_LINK.text });
  await expect(link).toBeVisible();

  // Verify href — do NOT click; clicking would trigger Auth0 external redirect
  const href = await link.getAttribute("href");
  expect(href).toBe(SIGN_IN_LINK.href);
});

// ---------------------------------------------------------------------------
// PUB-18 — "Sign up free" link navigates to /signup
// ---------------------------------------------------------------------------

test("PUB-18 — 'Sign up free' link is visible and navigates to /signup", async ({ page }) => {
  await page.goto(PAGE.url);

  const link = page.getByRole("link", { name: SIGN_UP_LINK.text });
  await expect(link).toBeVisible();

  await link.click();
  await expect(page).toHaveURL(new RegExp(SIGN_UP_LINK.href));
});

// ---------------------------------------------------------------------------
// Supporting links — forgot password + school sign in
// ---------------------------------------------------------------------------

for (const { text, href } of SUPPORTING_LINKS) {
  test(`supporting link "${text}" is visible and points to ${href}`, async ({ page }) => {
    await page.goto(PAGE.url);

    const link = page.getByRole("link", { name: text });
    await expect(link).toBeVisible();

    const resolvedHref = await link.getAttribute("href");
    expect(resolvedHref).toBe(href);
  });
}
