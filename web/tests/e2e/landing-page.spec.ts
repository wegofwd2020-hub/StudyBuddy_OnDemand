/**
 * E2E tests for section 1.1 — Landing Page (`/`)
 * Covers TC-IDs: PUB-01 through PUB-10
 *
 * Run with:
 *   npx playwright test landing-page
 */

import { test, expect } from "@playwright/test";
import {
  BANNER,
  HERO,
  FEATURES,
  TESTIMONIALS,
  FOOTER_CTA,
  NAV_LINKS,
  MOBILE_VIEWPORT,
} from "./data/landing-page";

// ---------------------------------------------------------------------------
// PUB-01 — Home banner displays at top of page
// ---------------------------------------------------------------------------

test("PUB-01 — home banner is visible at the top of the page", async ({ page }) => {
  await page.goto("/");

  const banner = page.getByRole("img", { name: BANNER.alt });
  await expect(banner).toBeVisible();

  // Verify the banner is near the top (within the first 300 px of the document)
  const box = await banner.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.y).toBeLessThan(300);
  // Rendered height should be close to the configured 240 px (allow ±5 px for sub-pixel)
  expect(box!.height).toBeGreaterThan(235);
});

// ---------------------------------------------------------------------------
// PUB-02 — Hero heading is visible
// ---------------------------------------------------------------------------

test("PUB-02 — hero H1 heading is visible above the fold", async ({ page }) => {
  await page.goto("/");

  const heading = page.getByRole("heading", { level: 1, name: HERO.heading });
  await expect(heading).toBeVisible();

  // Confirm it is within the viewport (above the fold)
  const viewportHeight = page.viewportSize()!.height;
  const box = await heading.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.y).toBeLessThan(viewportHeight);
});

// ---------------------------------------------------------------------------
// PUB-03 — Primary CTA navigates to /signup
// ---------------------------------------------------------------------------

test("PUB-03 — primary CTA 'Start free trial' navigates to /signup", async ({ page }) => {
  await page.goto("/");

  // Desktop + mobile nav both render a CTA — first() targets the desktop one
  const cta = page.getByRole("link", { name: HERO.ctaPrimary.text }).first();
  await expect(cta).toBeVisible();
  await cta.click();

  await expect(page).toHaveURL(new RegExp(HERO.ctaPrimary.href));
});

// ---------------------------------------------------------------------------
// PUB-04 — Secondary CTA links to /#features
// ---------------------------------------------------------------------------

test("PUB-04 — secondary CTA 'See how it works' points to /#features", async ({ page }) => {
  await page.goto("/");

  const cta = page.getByRole("link", { name: HERO.ctaSecondary.text }).first();
  await expect(cta).toBeVisible();

  // Verify the href attribute — clicking a hash link keeps us on the same page
  const href = await cta.getAttribute("href");
  expect(href).toBe(HERO.ctaSecondary.href);

  await cta.click();

  // After click the URL should contain the #features fragment
  await expect(page).toHaveURL(/\/#features$/);

  // The features section should now be in the DOM
  await expect(page.locator("#features")).toBeAttached();
});

// ---------------------------------------------------------------------------
// PUB-05 — Features grid renders all 6 cards
// ---------------------------------------------------------------------------

test("PUB-05 — features grid renders all 6 feature cards", async ({ page }) => {
  await page.goto("/");

  for (const feature of FEATURES) {
    await expect(
      page.getByRole("heading", { name: feature.title }),
    ).toBeVisible();
    await expect(page.getByText(feature.description)).toBeVisible();
  }
});

// ---------------------------------------------------------------------------
// PUB-06 — Testimonials section renders all 3 cards
// ---------------------------------------------------------------------------

test("PUB-06 — social proof section renders all 3 testimonials", async ({ page }) => {
  await page.goto("/");

  for (const item of TESTIMONIALS) {
    // Quote appears inside a <p> as an italic string
    await expect(page.getByText(item.quote)).toBeVisible();
    // Author line is prefixed with an em dash
    await expect(page.getByText(`— ${item.author}`)).toBeVisible();
  }
});

// ---------------------------------------------------------------------------
// PUB-07 — Footer / bottom CTA navigates to /signup
// ---------------------------------------------------------------------------

test("PUB-07 — bottom CTA 'Start your free trial' navigates to /signup", async ({ page }) => {
  await page.goto("/");

  // Scroll to the bottom section first so the element is in the viewport
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

  const cta = page.getByRole("link", { name: FOOTER_CTA.buttonText });
  await expect(cta).toBeVisible();
  await cta.click();

  await expect(page).toHaveURL(new RegExp(FOOTER_CTA.href));
});

// ---------------------------------------------------------------------------
// PUB-08 / PUB-09 — Desktop nav links
// ---------------------------------------------------------------------------

for (const { text, href } of NAV_LINKS) {
  test(`PUB-08/09 — desktop nav link "${text}" navigates to ${href}`, async ({ page }) => {
    await page.goto("/");

    // Desktop nav is hidden on mobile; run at default (desktop) viewport.
    // Both desktop and mobile nav render the same link — first() = desktop.
    const link = page.getByRole("link", { name: text }).first();
    await expect(link).toBeVisible();

    const resolvedHref = await link.getAttribute("href");
    expect(resolvedHref).toBe(href);
  });
}

// ---------------------------------------------------------------------------
// PUB-10 — Mobile nav: hamburger button visible, opens menu
// ---------------------------------------------------------------------------

test("PUB-10 — hamburger menu is visible and opens mobile nav at 375 px viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: MOBILE_VIEWPORT.width, height: MOBILE_VIEWPORT.height });
  await page.goto("/");

  // Desktop nav links should be hidden at this breakpoint
  const desktopPricingLink = page.locator("nav.hidden.md\\:flex a", { hasText: "Pricing" });
  await expect(desktopPricingLink).toBeHidden();

  // Hamburger button should be visible
  const hamburger = page.getByRole("button", { name: MOBILE_VIEWPORT.hamburgerLabel });
  await expect(hamburger).toBeVisible();

  // After clicking, mobile menu expands with nav links
  await hamburger.click();
  await expect(page.getByRole("link", { name: "Pricing" }).last()).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in" }).last()).toBeVisible();
});
