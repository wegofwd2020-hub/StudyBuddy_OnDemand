/**
 * E2E tests for section 1.2 — Pricing Page (`/pricing`)
 * Covers TC-IDs: PUB-11 through PUB-16
 *
 * Run with:
 *   npx playwright test pricing-page
 */

import { test, expect } from "@playwright/test";
import { PLAN_PRICES, PLAN_CTAS, FAQ_ITEMS, MOST_POPULAR_BADGE } from "./data/pricing-page";

// ---------------------------------------------------------------------------
// PUB-11 — Three plan cards render with correct prices
// ---------------------------------------------------------------------------

test("PUB-11 — all three plan cards render with correct prices", async ({ page }) => {
  await page.goto("/pricing");

  for (const { plan, price } of PLAN_PRICES) {
    // Plan name heading is visible
    await expect(page.getByRole("heading", { name: plan })).toBeVisible();
    // Price value is visible somewhere on the page
    await expect(page.getByText(price).first()).toBeVisible();
  }
});

// ---------------------------------------------------------------------------
// PUB-12 — Free plan CTA → /signup
// ---------------------------------------------------------------------------

test("PUB-12 — 'Start free' on Free plan navigates to /signup", async ({ page }) => {
  await page.goto("/pricing");

  const { label, href } = PLAN_CTAS[0];
  // Scope to #plans to avoid matching the nav "Start free" button
  const cta = page.locator("#plans").getByRole("link", { name: label });
  await expect(cta).toBeVisible();

  await cta.click();
  await expect(page).toHaveURL(new RegExp(href));
});

// ---------------------------------------------------------------------------
// PUB-13 — Student plan CTA → /signup
// ---------------------------------------------------------------------------

test("PUB-13 — 'Subscribe now' on Student plan navigates to /signup", async ({ page }) => {
  await page.goto("/pricing");

  const { label, href } = PLAN_CTAS[1];
  const cta = page.getByRole("link", { name: label });
  await expect(cta).toBeVisible();

  await cta.click();
  await expect(page).toHaveURL(new RegExp(href));
});

// ---------------------------------------------------------------------------
// PUB-14 — School plan CTA → /contact
// ---------------------------------------------------------------------------

test("PUB-14 — 'Contact sales' on School plan navigates to /contact", async ({ page }) => {
  await page.goto("/pricing");

  const { label, href } = PLAN_CTAS[2];
  const cta = page.getByRole("link", { name: label });
  await expect(cta).toBeVisible();

  await cta.click();
  await expect(page).toHaveURL(new RegExp(href));
});

// ---------------------------------------------------------------------------
// PUB-15 — FAQ accordion opens and closes
// ---------------------------------------------------------------------------

test("PUB-15 — FAQ accordion expands on click and collapses on second click", async ({
  page,
}) => {
  await page.goto("/pricing");

  // Scroll FAQ into view first
  await page.getByRole("heading", { name: "Frequently asked questions" }).scrollIntoViewIfNeeded();

  // Test each FAQ item independently
  for (const { question, answer } of FAQ_ITEMS) {
    const trigger = page.getByRole("button", { name: question });
    await expect(trigger).toBeVisible();

    // --- Open ---
    await trigger.click();
    // Answer panel should now be visible
    await expect(page.getByText(answer)).toBeVisible();

    // --- Close ---
    await trigger.click();
    // Answer panel should collapse (hidden / zero height)
    await expect(page.getByText(answer)).toBeHidden();
  }
});

// ---------------------------------------------------------------------------
// PUB-16 — Student plan "Most popular" badge is visible
// ---------------------------------------------------------------------------

test("PUB-16 — Student plan card shows 'Most popular' badge", async ({ page }) => {
  await page.goto("/pricing");

  const badge = page.getByText(MOST_POPULAR_BADGE.text);
  await expect(badge).toBeVisible();

  // Verify the badge is inside the Student plan card (CardTitle is a <div>, not a heading;
  // locate the card by data-slot and filter by both plan name and badge text)
  const studentCard = page
    .locator('[data-slot="card"]')
    .filter({ hasText: MOST_POPULAR_BADGE.plan })
    .filter({ hasText: MOST_POPULAR_BADGE.text });
  await expect(studentCard).toBeVisible();
});
