/**
 * Test data for section 3.5 — Reports Overview (`/school/reports/overview`)
 * Covers TC-IDs: SCH-09, SCH-10
 *
 * Auth note: requires a real Auth0 session for E2E.
 * Unit tests mock useTeacher(), usePathname(), and useQuery directly.
 *
 * Backend API route for E2E page.route() interception:
 *   GET /api/v1/reports/school/{school_id}/overview?period=7d → MOCK_OVERVIEW_REPORT
 */

import type { OverviewReport } from "@/lib/api/reports";

// ---------------------------------------------------------------------------
// Mock teacher claims
// ---------------------------------------------------------------------------

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id:  "school-001",
  role: "teacher" as const,
};

// ---------------------------------------------------------------------------
// Mock overview report — healthy school (SCH-09)
// ---------------------------------------------------------------------------

export const MOCK_OVERVIEW_REPORT: OverviewReport = {
  school_id:                   "school-001",
  period:                      "7d",
  enrolled_students:           120,
  active_students_period:      85,
  active_pct:                  70.8,
  lessons_viewed:              340,
  quiz_attempts:               210,
  first_attempt_pass_rate_pct: 72.0,
  audio_play_rate_pct:         45.0,
  units_with_struggles:        ["G8-MATH-002", "G8-SCI-003"],
  units_no_activity:           [],
  unreviewed_feedback_count:   3,
};

// ---------------------------------------------------------------------------
// Mock overview report — no struggles, no inactive units
// ---------------------------------------------------------------------------

export const MOCK_OVERVIEW_HEALTHY: OverviewReport = {
  ...MOCK_OVERVIEW_REPORT,
  units_with_struggles: [],
  units_no_activity:    [],
};

// ---------------------------------------------------------------------------
// Mock overview report — low pass rate (below 60% → red highlight)
// ---------------------------------------------------------------------------

export const MOCK_OVERVIEW_LOW_PASS: OverviewReport = {
  ...MOCK_OVERVIEW_REPORT,
  first_attempt_pass_rate_pct: 45.0,
};

// ---------------------------------------------------------------------------
// Expected UI strings — Overview report page (SCH-09)
// ---------------------------------------------------------------------------

export const OVERVIEW_STRINGS = {
  pageHeading:        "Overview Report",
  // Period toggle labels
  period7d:           "Last 7 days",
  period30d:          "Last 30 days",
  periodTerm:         "This term",
  // KPI card labels
  enrolled:           "Enrolled",
  active:             "Active",
  lessonsViewed:      "Lessons viewed",
  quizAttempts:       "Quiz attempts",
  passRate:           "1st-attempt pass rate",
  audioPlayRate:      "Audio play rate",
  // Unit sections
  unitsWithStruggles: "Units with struggles",
  noStruggles:        "None — all units healthy.",
  unitsNoActivity:    "Units with no activity",
  allUnitsActive:     "All units have activity.",
} as const;

// ---------------------------------------------------------------------------
// Expected UI strings — Reports sub-nav (SCH-10)
// ---------------------------------------------------------------------------

export const REPORT_SUBNAV_LABELS = [
  "Overview",
  "Trends",
  "At-Risk",
  "Unit Performance",
  "Engagement",
  "Feedback",
  "Export CSV",
] as const;

export const REPORT_SUBNAV_HREFS = {
  overview:    "/school/reports/overview",
  trends:      "/school/reports/trends",
  atRisk:      "/school/reports/at-risk",
  units:       "/school/reports/units",
  engagement:  "/school/reports/engagement",
  feedback:    "/school/reports/feedback",
  exportCsv:   "/school/reports/export",
} as const;
