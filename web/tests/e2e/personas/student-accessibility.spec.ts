/**
 * tests/e2e/personas/student-accessibility.spec.ts
 *
 * Accessibility (WCAG 2.1 AA) and smoke tests for the Student persona.
 *
 * Auth strategy:
 *   - sb_dev_session cookie  → satisfies the server-component layout check
 *   - sb_token in localStorage → satisfies the Axios API-client Bearer header
 *
 * All backend API calls are intercepted with page.route() — no live backend needed.
 */

import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { checkA11y } from "../helpers/axe";
import { makeStudentToken, devSessionCookie } from "../helpers/tokens";

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------

const STUDENT_TOKEN = makeStudentToken();

async function setupStudentAuth(page: Page) {
  // Server-side: dev-session cookie so layout doesn't redirect to /login
  await page
    .context()
    .addCookies([devSessionCookie("Alex Student", "alex@test.invalid")]);
  // Client-side: student JWT so Axios attaches Authorization header
  await page.addInitScript(
    (token) => localStorage.setItem("sb_token", token),
    STUDENT_TOKEN,
  );
}

// ---------------------------------------------------------------------------
// API stubs — minimal valid responses for each page
// ---------------------------------------------------------------------------

async function stubStudentApis(page: Page) {
  // Subscription status (TrialBanner in every student page)
  await page.route("**/api/v1/subscription/status**", (route) =>
    route.fulfill({ status: 200, json: { status: "active", plan: "student" } }),
  );

  // Student stats (dashboard + stats page)
  await page.route("**/api/v1/analytics/student/stats**", (route) =>
    route.fulfill({
      status: 200,
      json: {
        streak_days: 5,
        session_dates: [],
        lessons_viewed: 12,
        quizzes_completed: 8,
        pass_rate: 0.75,
        avg_score: 82,
        audio_sessions: 3,
        period: "30d",
      },
    }),
  );

  // Progress history (dashboard recent activity)
  await page.route("**/api/v1/progress/history**", (route) =>
    route.fulfill({
      status: 200,
      json: {
        sessions: [
          {
            session_id: "sess-001",
            unit_id: "G8-MATH-001",
            unit_title: "Algebra: Linear Equations",
            subject: "Mathematics",
            started_at: new Date().toISOString(),
            score: 85,
            passed: true,
          },
        ],
      },
    }),
  );

  // Curriculum tree (subjects + curriculum map pages)
  await page.route("**/api/v1/curriculum/tree**", (route) =>
    route.fulfill({
      status: 200,
      json: {
        curriculum_id: "default-2026-g8",
        grade: 8,
        subjects: [
          {
            subject: "Mathematics",
            units: [
              {
                unit_id: "G8-MATH-001",
                title: "Algebra: Linear Equations",
                has_lab: false,
                sequence: 1,
              },
            ],
          },
          {
            subject: "Science",
            units: [
              {
                unit_id: "G8-SCI-001",
                title: "Cell Biology",
                has_lab: true,
                sequence: 1,
              },
            ],
          },
        ],
      },
    }),
  );

  // Progress map (curriculum page)
  await page.route("**/api/v1/student/progress**", (route) =>
    route.fulfill({
      status: 200,
      json: {
        curriculum_id: "default-2026-g8",
        pending_count: 3,
        needs_retry_count: 1,
        subjects: [
          {
            subject: "Mathematics",
            units: [
              {
                unit_id: "G8-MATH-001",
                title: "Algebra: Linear Equations",
                status: "completed",
                best_score: 85,
                attempts: 1,
              },
            ],
          },
        ],
      },
    }),
  );

  // Auth settings (settings page)
  await page.route("**/api/v1/auth/settings**", (route) =>
    route.fulfill({
      status: 200,
      json: {
        display_name: "Alex Student",
        locale: "en",
        notifications: {
          streak_reminders: true,
          weekly_summary: true,
          quiz_nudges: false,
        },
      },
    }),
  );

  // Catch-all for any remaining API calls — return empty 200
  await page.route("**/api/v1/**", (route) => route.fulfill({ status: 200, json: {} }));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe("Student persona — smoke & accessibility", () => {
  test.beforeEach(async ({ page }) => {
    await setupStudentAuth(page);
    await stubStudentApis(page);
  });

  // ── Dashboard ─────────────────────────────────────────────────────────────

  test("dashboard loads and shows title", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
  });

  test("dashboard — no critical WCAG violations", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Student — Dashboard");
  });

  // ── Subjects ──────────────────────────────────────────────────────────────

  test("subjects page loads and lists subjects", async ({ page }) => {
    await page.goto("/subjects");
    await expect(page.getByText(/mathematics/i)).toBeVisible();
  });

  test("subjects — no critical WCAG violations", async ({ page }) => {
    await page.goto("/subjects");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Student — Subjects");
  });

  // ── Curriculum map ────────────────────────────────────────────────────────

  test("curriculum map loads", async ({ page }) => {
    await page.goto("/curriculum");
    await expect(page.getByRole("heading", { name: /curriculum/i })).toBeVisible();
  });

  test("curriculum map — no critical WCAG violations", async ({ page }) => {
    await page.goto("/curriculum");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Student — Curriculum Map");
  });

  // ── Stats ─────────────────────────────────────────────────────────────────

  test("stats page loads and shows lessons viewed", async ({ page }) => {
    await page.goto("/stats");
    await expect(page.getByText(/lessons viewed/i)).toBeVisible();
  });

  test("stats — no critical WCAG violations", async ({ page }) => {
    await page.goto("/stats");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Student — Stats");
  });

  // ── Account settings ──────────────────────────────────────────────────────

  test("settings page loads", async ({ page }) => {
    await page.goto("/account/settings");
    await expect(page.getByRole("heading", { name: /settings/i })).toBeVisible();
  });

  test("settings — no critical WCAG violations", async ({ page }) => {
    await page.goto("/account/settings");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Student — Account Settings");
  });

  // ── Navigation ────────────────────────────────────────────────────────────

  test("student nav is present and has accessible links", async ({ page }) => {
    await page.goto("/dashboard");
    // Sidebar should have labelled navigation links
    const nav = page.getByRole("navigation");
    await expect(nav).toBeVisible();
    await expect(nav.getByRole("link", { name: /dashboard/i })).toBeVisible();
  });

  // ── Paywall page ──────────────────────────────────────────────────────────

  test("paywall page — no critical WCAG violations", async ({ page }) => {
    await page.goto("/paywall");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Student — Paywall");
  });
});
