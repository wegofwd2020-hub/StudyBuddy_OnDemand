/**
 * Test data for section 2.1 — Student Portal Auth Redirects
 * Covers TC-IDs: STU-01, STU-02, STU-03
 *
 * All student routes sit under app/(student)/layout.tsx which calls
 * auth0.getSession(). In the test environment getSession() returns null
 * (no real Auth0 cookie) → layout calls redirect("/login").
 *
 * Expected behaviour: every route below redirects to /login with no 500.
 */

export const REDIRECT_TARGET = "/login";

/**
 * TC-IDs mapped to routes.
 * Dynamic segments use a representative unit_id so the route resolves.
 */
export const STUDENT_PROTECTED_ROUTES: ReadonlyArray<{
  tcId: string;
  path: string;
  description: string;
}> = [
  // --- Listed in section 2.1 ---
  {
    tcId: "STU-01",
    path: "/dashboard",
    description: "Student dashboard",
  },
  {
    tcId: "STU-02",
    path: "/subjects",
    description: "Subjects list",
  },
  {
    tcId: "STU-03",
    path: "/lesson/unit-001",
    description: "Lesson page (dynamic route)",
  },
  // --- Additional student routes protected by the same layout guard ---
  {
    tcId: "STU-AUX-01",
    path: "/curriculum",
    description: "Curriculum map",
  },
  {
    tcId: "STU-AUX-02",
    path: "/quiz/unit-001",
    description: "Quiz page (dynamic route)",
  },
  {
    tcId: "STU-AUX-03",
    path: "/progress",
    description: "Progress page",
  },
  {
    tcId: "STU-AUX-04",
    path: "/stats",
    description: "Stats page",
  },
  {
    tcId: "STU-AUX-05",
    path: "/account/settings",
    description: "Account settings",
  },
];
