/**
 * E2E tests for the unified /signin page.
 *
 * Covers the three auth tracks dispatched by POST /auth/universal-login:
 *   - local (school-provisioned student/teacher/school_admin)
 *   - demo_student
 *   - demo_teacher
 *
 * Backend behaviour is asserted in tests/test_auth_universal_login.py. These
 * tests verify only the client wiring: form rendering, the correct
 * localStorage / cookie writes per track, and the post-login redirect target.
 * The backend is mocked via page.route.
 *
 * Run with:
 *   npx playwright test signin-page
 */

import { test, expect, type Page, type Route } from "@playwright/test";

interface MockResponse {
  token: string;
  auth_track: "local" | "demo_student" | "demo_teacher";
  role: "student" | "teacher" | "school_admin";
  user_id: string;
  name: string;
  refresh_token: string | null;
  first_login: boolean | null;
  demo_expires_at: string | null;
}

function makeJwt(role: string, firstLogin: boolean): string {
  // Minimal decodable JWT (alg=none) — the schoolPortal LocalAuthGuard reads
  // the `first_login` claim, so it needs to round-trip atob/JSON.parse.
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({
      role,
      first_login: firstLogin,
      // Far-future exp so the guard treats the token as live.
      exp: 9_999_999_999,
    }),
  );
  return `${header}.${payload}.sig`;
}

async function mockUniversalLogin(page: Page, response: MockResponse) {
  await page.route("**/api/v1/auth/universal-login", (route: Route) =>
    route.fulfill({ status: 200, json: response }),
  );
}

async function mockUniversalLoginError(page: Page, status: number) {
  await page.route("**/api/v1/auth/universal-login", (route: Route) =>
    route.fulfill({
      status,
      json: { error: "unauthenticated", detail: "Invalid email or password." },
    }),
  );
}

// ---------------------------------------------------------------------------
// Page load
// ---------------------------------------------------------------------------

test("/signin renders the unified sign-in form", async ({ page }) => {
  await page.goto("/signin");
  await expect(page.getByText(/sign in to studybuddy/i)).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Email" })).toBeVisible();
  // The form has both a "Password" input and a "Show password" toggle button,
  // so use the exact textbox role to disambiguate.
  await expect(page.getByRole("textbox", { name: "Password" })).toBeVisible();
  await expect(page.getByRole("button", { name: /^sign in$/i })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Local-auth track — teacher / school_admin
// ---------------------------------------------------------------------------

test("local school_admin sign-in stores teacher token and routes to /school/dashboard", async ({
  page,
}) => {
  const token = makeJwt("school_admin", false);
  await mockUniversalLogin(page, {
    token,
    auth_track: "local",
    role: "school_admin",
    user_id: "teacher-uuid-1",
    name: "Ms. Rivera",
    refresh_token: "refresh-abc",
    first_login: false,
    demo_expires_at: null,
  });

  await page.goto("/signin");
  await page.getByRole("textbox", { name: "Email" }).fill("admin@school.test");
  await page.getByRole("textbox", { name: "Password" }).fill("Password123!");
  await page.getByRole("button", { name: /^sign in$/i }).click();

  // The school portal layout will try to render after navigation; intercept
  // any downstream API calls and let them 404 — we only care that the URL
  // ends up at /school/dashboard.
  await page.waitForURL(/\/school\/dashboard/);

  const stored = await page.evaluate(() => ({
    teacherToken: localStorage.getItem("sb_teacher_token"),
    refresh: localStorage.getItem("sb_teacher_refresh_token"),
    studentToken: localStorage.getItem("sb_token"),
    cookies: document.cookie,
  }));
  expect(stored.teacherToken).toBe(token);
  expect(stored.refresh).toBe("refresh-abc");
  expect(stored.studentToken).toBeNull();
  expect(stored.cookies).toContain("sb_local_teacher_session=");
});

test("local first_login=true routes to /school/change-password", async ({ page }) => {
  const token = makeJwt("teacher", true);
  await mockUniversalLogin(page, {
    token,
    auth_track: "local",
    role: "teacher",
    user_id: "teacher-uuid-2",
    name: "Mr. Patel",
    refresh_token: "refresh-xyz",
    first_login: true,
    demo_expires_at: null,
  });

  await page.goto("/signin");
  await page.getByRole("textbox", { name: "Email" }).fill("teacher@school.test");
  await page.getByRole("textbox", { name: "Password" }).fill("DefaultPwd123!");
  await page.getByRole("button", { name: /^sign in$/i }).click();

  await page.waitForURL(/\/school\/change-password\?required=1/);
});

// ---------------------------------------------------------------------------
// Local-auth track — student
// ---------------------------------------------------------------------------

test("local student sign-in stores student token and routes to /dashboard", async ({
  page,
}) => {
  const token = makeJwt("student", false);
  await mockUniversalLogin(page, {
    token,
    auth_track: "local",
    role: "student",
    user_id: "student-uuid-1",
    name: "Aanya P.",
    refresh_token: "refresh-stu",
    first_login: false,
    demo_expires_at: null,
  });

  await page.goto("/signin");
  await page.getByRole("textbox", { name: "Email" }).fill("student@school.test");
  await page.getByRole("textbox", { name: "Password" }).fill("Password123!");
  await page.getByRole("button", { name: /^sign in$/i }).click();

  await page.waitForURL(/\/dashboard/);

  const stored = await page.evaluate(() => ({
    studentToken: localStorage.getItem("sb_token"),
    teacherToken: localStorage.getItem("sb_teacher_token"),
    cookies: document.cookie,
  }));
  expect(stored.studentToken).toBe(token);
  expect(stored.teacherToken).toBeNull();
  expect(stored.cookies).toContain("sb_local_student_session=");
});

// ---------------------------------------------------------------------------
// Demo tracks
// ---------------------------------------------------------------------------

test("demo_student sign-in stores student token + dev session cookie", async ({
  page,
}) => {
  const token = makeJwt("demo_student", false);
  await mockUniversalLogin(page, {
    token,
    auth_track: "demo_student",
    role: "student",
    user_id: "demo-student-1",
    name: "demo",
    refresh_token: null,
    first_login: null,
    demo_expires_at: "2026-06-01T00:00:00Z",
  });

  await page.goto("/signin");
  await page.getByRole("textbox", { name: "Email" }).fill("demo-student@example.com");
  await page.getByRole("textbox", { name: "Password" }).fill("DemoPwd123!");
  await page.getByRole("button", { name: /^sign in$/i }).click();

  await page.waitForURL(/\/dashboard/);

  const stored = await page.evaluate(() => ({
    studentToken: localStorage.getItem("sb_token"),
    cookies: document.cookie,
  }));
  expect(stored.studentToken).toBe(token);
  expect(stored.cookies).toContain("sb_dev_session=");
});

test("demo_teacher sign-in stores teacher token + teacher session cookie", async ({
  page,
}) => {
  const token = makeJwt("school_admin", false);
  await mockUniversalLogin(page, {
    token,
    auth_track: "demo_teacher",
    role: "school_admin",
    user_id: "demo-teacher-1",
    name: "Demo Teacher",
    refresh_token: null,
    first_login: null,
    demo_expires_at: "2026-06-01T00:00:00Z",
  });

  await page.goto("/signin");
  await page.getByRole("textbox", { name: "Email" }).fill("demo-teacher@example.com");
  await page.getByRole("textbox", { name: "Password" }).fill("DemoPwd123!");
  await page.getByRole("button", { name: /^sign in$/i }).click();

  await page.waitForURL(/\/school\/dashboard/);

  const stored = await page.evaluate(() => ({
    teacherToken: localStorage.getItem("sb_teacher_token"),
    cookies: document.cookie,
  }));
  expect(stored.teacherToken).toBe(token);
  expect(stored.cookies).toContain("sb_teacher_session=");
});

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

test("invalid credentials show a 401 error message", async ({ page }) => {
  await mockUniversalLoginError(page, 401);

  await page.goto("/signin");
  await page.getByRole("textbox", { name: "Email" }).fill("wrong@example.com");
  await page.getByRole("textbox", { name: "Password" }).fill("nope");
  await page.getByRole("button", { name: /^sign in$/i }).click();

  await expect(page.getByText(/incorrect email or password/i)).toBeVisible();
});

test("rate-limit response shows a 429 error message", async ({ page }) => {
  await mockUniversalLoginError(page, 429);

  await page.goto("/signin");
  await page.getByRole("textbox", { name: "Email" }).fill("rl@example.com");
  await page.getByRole("textbox", { name: "Password" }).fill("Password123!");
  await page.getByRole("button", { name: /^sign in$/i }).click();

  await expect(page.getByText(/too many sign-in attempts/i)).toBeVisible();
});
