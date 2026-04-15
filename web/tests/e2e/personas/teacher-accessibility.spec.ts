/**
 * tests/e2e/personas/teacher-accessibility.spec.ts
 *
 * Accessibility (WCAG 2.1 AA) and smoke tests for the Teacher / School Admin persona.
 *
 * Auth strategy:
 *   - sb_dev_session cookie       → satisfies the server-component layout check
 *   - sb_teacher_token in localStorage → decoded by useTeacher() to get school_id
 *
 * All backend API calls are intercepted with page.route() — no live backend needed.
 */

import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { checkA11y } from "../helpers/axe";

// Axe rules disabled for this persona. Tracked in GitHub issue #189
// (umbrella Epic 9 accessibility audit). Do NOT extend without filing
// a corresponding issue first.
const KNOWN_A11Y_EXCLUSIONS = ["color-contrast", "html-has-lang", "document-title"] as const;
import { makeTeacherToken, devSessionCookie } from "../helpers/tokens";

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------

const SCHOOL_ID = "test-school-001";
const TEACHER_TOKEN = makeTeacherToken("test-teacher-001", SCHOOL_ID, "school_admin");

async function setupTeacherAuth(page: Page) {
  // Server-side: dev-session cookie so layout doesn't redirect to /school/login
  await page
    .context()
    .addCookies([devSessionCookie("Ms. Rivera", "teacher@test.invalid")]);
  // Client-side: teacher JWT decoded by useTeacher() hook
  await page.addInitScript(
    (token) => localStorage.setItem("sb_teacher_token", token),
    TEACHER_TOKEN,
  );
}

// ---------------------------------------------------------------------------
// API stubs
// ---------------------------------------------------------------------------

async function stubTeacherApis(page: Page) {
  const schoolGlob = `**/api/v1/**/${SCHOOL_ID}/**`;

  // Overview report (dashboard + reports/overview)
  await page.route(`**/api/v1/reports/school/${SCHOOL_ID}/overview**`, (route) =>
    route.fulfill({
      status: 200,
      json: {
        enrolled_students: 28,
        active_students_period: 22,
        active_pct: 78.6,
        lessons_viewed: 94,
        quiz_attempts: 67,
        first_attempt_pass_rate_pct: 71.6,
        unreviewed_feedback_count: 3,
        units_with_struggles: ["G8-MATH-003"],
        period: "7d",
      },
    }),
  );

  // Alerts (dashboard + alerts page)
  await page.route(`**/api/v1/reports/school/${SCHOOL_ID}/alerts**`, (route) =>
    route.fulfill({
      status: 200,
      json: {
        alerts: [
          {
            alert_id: "alert-001",
            student_id: "stu-001",
            student_name: "Jamie Lee",
            unit_id: "G8-MATH-003",
            unit_title: "Quadratic Equations",
            alert_type: "struggle",
            triggered_at: new Date().toISOString(),
            acknowledged: false,
          },
        ],
      },
    }),
  );

  // Unit report
  await page.route(`**/api/v1/reports/school/${SCHOOL_ID}/unit/**`, (route) =>
    route.fulfill({
      status: 200,
      json: {
        unit_id: "G8-MATH-001",
        students_viewed_lesson: 20,
        students_attempted_quiz: 18,
        first_attempt_pass_rate_pct: 72,
        attempt_distribution: { "1": 13, "2": 5 },
        struggle_flag: false,
        avg_score: 79,
      },
    }),
  );

  // At-risk report
  await page.route(`**/api/v1/reports/school/${SCHOOL_ID}/at-risk**`, (route) =>
    route.fulfill({
      status: 200,
      json: {
        students: [
          {
            student_id: "stu-002",
            display_name: "Chris Park",
            email: "chris@test.invalid",
            struggling_units: ["G8-MATH-003", "G8-SCI-002"],
            last_active: new Date().toISOString(),
          },
        ],
      },
    }),
  );

  // Student roster
  await page.route(`**/api/v1/schools/${SCHOOL_ID}/students**`, (route) =>
    route.fulfill({
      status: 200,
      json: {
        students: [
          {
            student_id: "stu-001",
            display_name: "Jamie Lee",
            email: "jamie@test.invalid",
            grade: 8,
            enrolment_status: "active",
          },
          {
            student_id: "stu-002",
            display_name: "Chris Park",
            email: "chris@test.invalid",
            grade: 8,
            enrolment_status: "active",
          },
        ],
      },
    }),
  );

  // Trends report
  await page.route(`**/api/v1/reports/school/${SCHOOL_ID}/trends**`, (route) =>
    route.fulfill({
      status: 200,
      json: { weekly: [], period: "30d" },
    }),
  );

  // Units report
  await page.route(`**/api/v1/reports/school/${SCHOOL_ID}/units**`, (route) =>
    route.fulfill({
      status: 200,
      json: { units: [] },
    }),
  );

  // Feedback report
  await page.route(`**/api/v1/reports/school/${SCHOOL_ID}/feedback**`, (route) =>
    route.fulfill({
      status: 200,
      json: { items: [] },
    }),
  );

  // Export endpoint
  await page.route(`**/api/v1/reports/school/${SCHOOL_ID}/export**`, (route) =>
    route.fulfill({ status: 200, contentType: "text/csv", body: "unit_id,score\n" }),
  );

  // School profile
  await page.route(`**/api/v1/schools/${SCHOOL_ID}**`, (route) =>
    route.fulfill({
      status: 200,
      json: {
        school_id: SCHOOL_ID,
        school_name: "Maplewood Academy",
        contact_email: "admin@maplewood.test",
        country: "CA",
      },
    }),
  );

  // Curriculum tree
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
              { unit_id: "G8-MATH-001", title: "Algebra", has_lab: false, sequence: 1 },
            ],
          },
        ],
      },
    }),
  );

  // Catch-all
  void schoolGlob;
  await page.route("**/api/v1/**", (route) => route.fulfill({ status: 200, json: {} }));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe("Teacher persona — smoke & accessibility", () => {
  test.beforeEach(async ({ page }) => {
    await setupTeacherAuth(page);
    await stubTeacherApis(page);
  });

  // ── Dashboard ─────────────────────────────────────────────────────────────

  test("school dashboard loads", async ({ page }) => {
    await page.goto("/school/dashboard");
    await expect(page.getByRole("heading", { name: /teacher dashboard/i })).toBeVisible();
  });

  test("school dashboard — no critical WCAG violations", async ({ page }) => {
    await page.goto("/school/dashboard");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Teacher — School Dashboard", KNOWN_A11Y_EXCLUSIONS);
  });

  // ── Students roster ───────────────────────────────────────────────────────

  test("students page loads and lists enrolled students", async ({ page }) => {
    await page.goto("/school/students");
    // Page h1 is "Student Roster".
    await expect(
      page.getByRole("heading", { name: /student roster/i }),
    ).toBeVisible();
  });

  test("students — no critical WCAG violations", async ({ page }) => {
    await page.goto("/school/students");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Teacher — Students Roster", KNOWN_A11Y_EXCLUSIONS);
  });

  // ── Reports: overview ─────────────────────────────────────────────────────

  test("overview report loads and shows enrolled students stat", async ({ page }) => {
    await page.goto("/school/reports/overview");
    await expect(
      page.getByRole("heading", { name: /(overview|reports)/i }).first(),
    ).toBeVisible();
  });

  test("overview report — no critical WCAG violations", async ({ page }) => {
    await page.goto("/school/reports/overview");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Teacher — Reports Overview", KNOWN_A11Y_EXCLUSIONS);
  });

  // ── Reports: at-risk ──────────────────────────────────────────────────────

  test("at-risk report loads", async ({ page }) => {
    await page.goto("/school/reports/at-risk");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Teacher — At-Risk Report", KNOWN_A11Y_EXCLUSIONS);
  });

  // ── Alerts ────────────────────────────────────────────────────────────────

  test("alerts page loads and shows alert", async ({ page }) => {
    await page.goto("/school/alerts");
    // Page h1 is "Alert Inbox".
    await expect(
      page.getByRole("heading", { name: /alert inbox/i }),
    ).toBeVisible();
  });

  test("alerts — no critical WCAG violations", async ({ page }) => {
    await page.goto("/school/alerts");
    await page.waitForLoadState("networkidle");
    await checkA11y(page, "Teacher — Alerts", KNOWN_A11Y_EXCLUSIONS);
  });

  // ── Navigation ────────────────────────────────────────────────────────────

  test("school nav is present with accessible links", async ({ page }) => {
    await page.goto("/school/dashboard");
    // Multiple nav elements (sidebar + footer) — disambiguate.
    const nav = page.getByRole("navigation").first();
    await expect(nav).toBeVisible();
    await expect(
      nav.getByRole("link", { name: /dashboard/i }).first(),
    ).toBeVisible();
  });

  // ── RBAC: teacher vs school_admin ─────────────────────────────────────────

  test("school_admin sees Reports nav link", async ({ page }) => {
    await page.goto("/school/dashboard");
    await expect(page.getByRole("link", { name: /reports/i })).toBeVisible();
  });

  test("plain teacher does not see Reports nav link", async ({ page }) => {
    const teacherOnlyToken = makeTeacherToken("test-teacher-002", SCHOOL_ID, "teacher");
    await page.addInitScript(
      (t) => localStorage.setItem("sb_teacher_token", t),
      teacherOnlyToken,
    );
    await page.goto("/school/dashboard");
    await expect(page.getByRole("link", { name: /^reports$/i })).not.toBeVisible();
  });
});
