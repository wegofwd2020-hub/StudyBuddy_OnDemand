/**
 * Test data for section 3.1 — School Portal Auth Redirects
 * Covers TC-IDs: SCH-01, SCH-02 (+ auxiliary school routes)
 *
 * Precondition: no Auth0 session — (school)/layout.tsx calls redirect("/school/login").
 *
 * All school portal routes are protected by the server-side (school)/layout.tsx.
 * Without a session, every route in the (school) group redirects to /school/login.
 */

export const REDIRECT_TARGET = "/school/login";

export const SCHOOL_PROTECTED_ROUTES: ReadonlyArray<{
  tcId: string;
  path: string;
  description: string;
}> = [
  // TC-IDs from TEST_CASES.md section 3.1
  { tcId: "SCH-01", path: "/school/dashboard",          description: "School dashboard" },
  { tcId: "SCH-02", path: "/school/reports/overview",   description: "Reports overview" },
  // Auxiliary routes — all protected by the same layout
  { tcId: "SCH-AUX-01", path: "/school/class/class-001",        description: "Class overview (dynamic route)" },
  { tcId: "SCH-AUX-02", path: "/school/student/student-001",    description: "Student detail (dynamic route)" },
  { tcId: "SCH-AUX-03", path: "/school/students",               description: "Students list" },
  { tcId: "SCH-AUX-04", path: "/school/teachers",               description: "Teachers list" },
  { tcId: "SCH-AUX-05", path: "/school/curriculum",             description: "School curriculum" },
  { tcId: "SCH-AUX-06", path: "/school/reports/at-risk",        description: "At-risk report" },
  { tcId: "SCH-AUX-07", path: "/school/reports/engagement",     description: "Engagement report" },
  { tcId: "SCH-AUX-08", path: "/school/alerts",                 description: "Alerts page" },
  { tcId: "SCH-AUX-09", path: "/school/settings",               description: "School settings" },
];
