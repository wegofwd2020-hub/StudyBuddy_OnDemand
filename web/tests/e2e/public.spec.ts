import { test, expect } from "@playwright/test";

test.describe("Public pages", () => {
  test("landing page loads and shows hero CTA", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    // Two CTAs exist (desktop + mobile layout) — first is sufficient
    await expect(
      page.getByRole("link", { name: "Start free trial" }).first(),
    ).toBeVisible();
  });

  test("pricing page shows three plan cards", async ({ page }) => {
    await page.goto("/pricing");
    await expect(page.getByText("$0")).toBeVisible();
    await expect(page.getByText("$9.99")).toBeVisible();
    await expect(page.getByText("$299+")).toBeVisible();
  });

  test("login page shows sign-in button", async ({ page }) => {
    await page.goto("/login");
    // The main CTA on the student login page is the Auth0 sign-in link
    await expect(
      page.getByRole("link", { name: "Sign in with school account" }),
    ).toBeVisible();
  });

  test("terms page renders heading", async ({ page }) => {
    await page.goto("/terms");
    await expect(page.getByRole("heading", { name: /terms of service/i })).toBeVisible();
  });

  test("privacy page renders heading", async ({ page }) => {
    await page.goto("/privacy");
    await expect(page.getByRole("heading", { name: /privacy policy/i })).toBeVisible();
  });

  test("contact page shows form", async ({ page }) => {
    await page.goto("/contact");
    await expect(page.getByRole("button", { name: /send message/i })).toBeVisible();
  });

  test("nav links are present on landing page", async ({ page }) => {
    await page.goto("/");
    // Desktop + mobile nav both render — use first() to avoid strict mode violation
    await expect(page.getByRole("link", { name: "Pricing" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Sign in" }).first()).toBeVisible();
  });

  test("404 page for unknown route", async ({ page }) => {
    const res = await page.goto("/this-page-does-not-exist");
    expect(res?.status()).toBe(404);
    await expect(page.getByText("Page not found")).toBeVisible();
  });
});
