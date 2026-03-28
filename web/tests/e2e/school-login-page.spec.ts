/**
 * E2E tests for section 1.4 — School Login Page (`/school/login`)
 * Covers TC-IDs: PUB-19, PUB-20, PUB-21
 *
 * Run with:
 *   npx playwright test school-login-page
 */

import { test, expect } from "@playwright/test";
import {
  PAGE,
  SIGN_IN_LINK,
  STUDENT_LOGIN_LINK,
  CONTACT_LINK,
} from "./data/school-login-page";

// ---------------------------------------------------------------------------
// Page load
// ---------------------------------------------------------------------------

test("page loads at /school/login with correct heading and subtitle", async ({ page }) => {
  await page.goto(PAGE.url);

  await expect(page.getByText(PAGE.title)).toBeVisible();
  await expect(page.getByText(PAGE.subtitle)).toBeVisible();
});

// ---------------------------------------------------------------------------
// PUB-19 — School sign-in button is visible with correct href
// ---------------------------------------------------------------------------

test("PUB-19 — school sign-in link renders and points to Auth0 school endpoint", async ({
  page,
}) => {
  await page.goto(PAGE.url);

  const link = page.getByRole("link", { name: SIGN_IN_LINK.text });
  await expect(link).toBeVisible();

  // Verify href — do NOT click; would trigger Auth0 external redirect
  const href = await link.getAttribute("href");
  expect(href).toBe(SIGN_IN_LINK.href);
});

// ---------------------------------------------------------------------------
// PUB-20 — "Student login" link navigates to /login
// ---------------------------------------------------------------------------

test("PUB-20 — 'Student login' link is visible and navigates to /login", async ({ page }) => {
  await page.goto(PAGE.url);

  const link = page.getByRole("link", { name: STUDENT_LOGIN_LINK.text });
  await expect(link).toBeVisible();

  await link.click();
  await expect(page).toHaveURL(new RegExp(STUDENT_LOGIN_LINK.href));
});

// ---------------------------------------------------------------------------
// PUB-21 — "Contact us" link navigates to /contact
// ---------------------------------------------------------------------------

test("PUB-21 — 'Contact us' link is visible and navigates to /contact", async ({ page }) => {
  await page.goto(PAGE.url);

  const link = page.getByRole("link", { name: CONTACT_LINK.text });
  await expect(link).toBeVisible();

  await link.click();
  await expect(page).toHaveURL(new RegExp(CONTACT_LINK.href));
});
