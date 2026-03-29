/**
 * E2E tests for section 1.5 — Static Pages
 * Covers TC-IDs: PUB-22 through PUB-28
 *
 * Run with:
 *   npx playwright test static-pages
 */

import { test, expect } from "@playwright/test";
import {
  TERMS,
  PRIVACY,
  CONTACT,
  SIGNUP,
  NOT_FOUND,
  CONSENT,
  RESET_PASSWORD,
} from "./data/static-pages";

// ---------------------------------------------------------------------------
// PUB-22 — Terms of Service
// ---------------------------------------------------------------------------

test.describe("PUB-22 — Terms of Service (/terms)", () => {
  test("H1 heading and all section headings render", async ({ page }) => {
    await page.goto(TERMS.url);

    await expect(
      page.getByRole("heading", { name: TERMS.heading, level: 1 }),
    ).toBeVisible();

    for (const section of TERMS.sectionHeadings) {
      await expect(page.getByRole("heading", { name: section })).toBeVisible();
    }
  });

  test("legal contact email link is present", async ({ page }) => {
    await page.goto(TERMS.url);
    await expect(page.getByRole("link", { name: TERMS.contactEmail })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// PUB-23 — Privacy Policy
// ---------------------------------------------------------------------------

test.describe("PUB-23 — Privacy Policy (/privacy)", () => {
  test("H1 heading and all section headings render", async ({ page }) => {
    await page.goto(PRIVACY.url);

    await expect(
      page.getByRole("heading", { name: PRIVACY.heading, level: 1 }),
    ).toBeVisible();

    for (const section of PRIVACY.sectionHeadings) {
      await expect(page.getByRole("heading", { name: section })).toBeVisible();
    }
  });
});

// ---------------------------------------------------------------------------
// PUB-24 — Contact Page
// ---------------------------------------------------------------------------

test.describe("PUB-24 — Contact Page (/contact)", () => {
  test("heading and all form fields render", async ({ page }) => {
    await page.goto(CONTACT.url);

    await expect(
      page.getByRole("heading", { name: CONTACT.heading, level: 1 }),
    ).toBeVisible();

    for (const field of CONTACT.fields) {
      if (field.type === "textarea") {
        await expect(page.locator(`textarea#${field.id}`)).toBeVisible();
      } else {
        await expect(page.locator(`input#${field.id}`)).toBeVisible();
      }
    }

    await expect(page.getByRole("button", { name: CONTACT.submitButton })).toBeVisible();
  });

  test("form submits successfully and shows confirmation", async ({ page }) => {
    await page.goto(CONTACT.url);

    const { name, email, subject, message } = CONTACT.validPayload;
    await page.locator("input#name").fill(name);
    await page.locator("input#email").fill(email);
    await page.locator("input#subject").fill(subject);
    await page.locator("textarea#message").fill(message);

    await page.getByRole("button", { name: CONTACT.submitButton }).click();

    await expect(page.getByText(CONTACT.successText)).toBeVisible({ timeout: 3000 });
  });
});

// ---------------------------------------------------------------------------
// PUB-25 — Signup Page
// ---------------------------------------------------------------------------

test.describe("PUB-25 — Signup Page (/signup)", () => {
  test("heading, subtitle, and perks list render", async ({ page }) => {
    await page.goto(SIGNUP.url);

    await expect(page.getByText(SIGNUP.title)).toBeVisible();
    await expect(page.getByText(SIGNUP.subtitle)).toBeVisible();

    for (const perk of SIGNUP.perks) {
      await expect(page.getByText(perk)).toBeVisible();
    }
  });

  test("CTA link is visible and points to Auth0 signup endpoint", async ({ page }) => {
    await page.goto(SIGNUP.url);

    const cta = page.getByRole("link", { name: SIGNUP.ctaText });
    await expect(cta).toBeVisible();

    // Do NOT click — triggers Auth0 external redirect
    const href = await cta.getAttribute("href");
    expect(href).toBe(SIGNUP.ctaHref);
  });

  test("'Sign in' link navigates to /login", async ({ page }) => {
    await page.goto(SIGNUP.url);

    // Scope to main content to avoid matching the nav "Sign in" button
    const link = page
      .locator("#main-content")
      .getByRole("link", { name: SIGNUP.signInLink.text });
    await expect(link).toBeVisible();
    await link.click();
    await expect(page).toHaveURL(new RegExp(SIGNUP.signInLink.href));
  });
});

// ---------------------------------------------------------------------------
// PUB-26 — 404 Page
// ---------------------------------------------------------------------------

test("PUB-26 — unknown route returns 404 and shows 'Page not found'", async ({
  page,
}) => {
  const response = await page.goto(NOT_FOUND.url);

  expect(response?.status()).toBe(NOT_FOUND.expectedStatus);
  await expect(page.getByText(NOT_FOUND.headingText)).toBeVisible();
});

// ---------------------------------------------------------------------------
// PUB-27 — COPPA Consent Page
// ---------------------------------------------------------------------------

test.describe("PUB-27 — COPPA Consent Page (/consent)", () => {
  test("heading, form fields, checkbox, and submit button render", async ({ page }) => {
    await page.goto(CONSENT.url);

    await expect(page.getByText(CONSENT.heading)).toBeVisible();

    for (const field of CONSENT.fields) {
      await expect(page.locator(`input#${field.id}`)).toBeVisible();
    }

    await expect(page.locator(`input#${CONSENT.checkboxId}`)).toBeVisible();
    await expect(page.getByText(CONSENT.checkboxLabel)).toBeVisible();
    await expect(page.getByRole("button", { name: CONSENT.submitButton })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// PUB-28 — Reset Password Page
// ---------------------------------------------------------------------------

test.describe("PUB-28 — Reset Password Page (/reset-password)", () => {
  test("default mode (no token) shows email form", async ({ page }) => {
    await page.goto(RESET_PASSWORD.url);

    await expect(page.getByText(RESET_PASSWORD.defaultHeading)).toBeVisible();
    await expect(page.getByText(RESET_PASSWORD.defaultSubtitle)).toBeVisible();
    await expect(page.locator(`input#${RESET_PASSWORD.emailFieldId}`)).toBeVisible();
    await expect(
      page.getByRole("button", { name: RESET_PASSWORD.submitButton }),
    ).toBeVisible();
  });

  test("token mode (?token=xxx) shows set-new-password form", async ({ page }) => {
    await page.goto(RESET_PASSWORD.tokenUrl);

    // "Set new password" appears in both the card title and the submit button — target the card title
    await expect(
      page.locator('[data-slot="card-title"]', { hasText: RESET_PASSWORD.tokenHeading }),
    ).toBeVisible();
    await expect(page.locator("input#password")).toBeVisible();
    await expect(page.locator("input#confirm")).toBeVisible();
    await expect(
      page.getByRole("button", { name: RESET_PASSWORD.tokenSubmitButton }),
    ).toBeVisible();
  });
});
