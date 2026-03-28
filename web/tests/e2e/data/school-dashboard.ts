/**
 * Test data for section 3.2 — School Dashboard (`/school/dashboard`)
 * Covers TC-IDs: SCH-03, SCH-04, SCH-05
 *
 * Auth note: requires a real Auth0 session for E2E.
 * Unit tests mock useTeacher(), useQuery (overview + alerts) directly.
 *
 * Backend API routes for E2E page.route() interception:
 *   GET /api/v1/reports/school/{school_id}/overview?period=7d → MOCK_OVERVIEW
 *   GET /api/v1/reports/school/{school_id}/alerts             → MOCK_ALERTS_WITH_UNREAD
 */

import type { OverviewReport, AlertListResponse } from "@/lib/api/reports";

// ---------------------------------------------------------------------------
// Mock teacher JWT claims (used by useTeacher)
// ---------------------------------------------------------------------------

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id:  "school-001",
  role: "teacher" as const,
};

// ---------------------------------------------------------------------------
// Mock overview report — healthy school (SCH-03)
// ---------------------------------------------------------------------------

export const MOCK_OVERVIEW: OverviewReport = {
  school_id:                    "school-001",
  period:                       "7d",
  enrolled_students:            120,
  active_students_period:       85,
  active_pct:                   70.8,
  lessons_viewed:               340,
  quiz_attempts:                210,
  first_attempt_pass_rate_pct:  72.0,
  audio_play_rate_pct:          45.0,
  units_with_struggles:         ["G8-MATH-002", "G8-SCI-003"],
  units_no_activity:            [],
  unreviewed_feedback_count:    3,
};

// ---------------------------------------------------------------------------
// Mock overview — no struggles (edge case)
// ---------------------------------------------------------------------------

export const MOCK_OVERVIEW_NO_STRUGGLES: OverviewReport = {
  ...MOCK_OVERVIEW,
  units_with_struggles:        [],
  unreviewed_feedback_count:   0,
};

// ---------------------------------------------------------------------------
// Mock alerts — 2 unread (SCH-05)
// ---------------------------------------------------------------------------

export const MOCK_ALERTS_WITH_UNREAD: AlertListResponse = {
  alerts: [
    {
      alert_id:     "alert-001",
      alert_type:   "low_pass_rate",
      school_id:    "school-001",
      details:      { unit_id: "G8-MATH-002", pass_rate: 38 },
      triggered_at: "2026-03-27T08:00:00Z",
      acknowledged: false,
    },
    {
      alert_id:     "alert-002",
      alert_type:   "low_pass_rate",
      school_id:    "school-001",
      details:      { unit_id: "G8-SCI-003", pass_rate: 42 },
      triggered_at: "2026-03-26T08:00:00Z",
      acknowledged: false,
    },
    {
      alert_id:     "alert-003",
      alert_type:   "inactive_students",
      school_id:    "school-001",
      details:      { inactive_count: 5 },
      triggered_at: "2026-03-25T08:00:00Z",
      acknowledged: true,
    },
  ],
};

export const MOCK_ALERTS_EMPTY: AlertListResponse = { alerts: [] };

// ---------------------------------------------------------------------------
// Expected UI strings
// ---------------------------------------------------------------------------

export const DASHBOARD_STRINGS = {
  pageHeading:          "Teacher Dashboard",
  viewFullReport:       "View full report",
  viewAtRiskReport:     "View at-risk report",
  unitsNeedingAttention:"Units needing attention",
  // KPI card titles (uppercase in page, but matched case-insensitively)
  enrolledStudents:     "Enrolled students",
  activeThisWeek:       "Active this week",
  lessonsViewed:        "Lessons viewed",
  passRate:             "Pass rate (1st attempt)",
  quizAttempts:         "Quiz attempts",
  unreviewedFeedback:   "Unreviewed feedback",
  // Quick-nav links
  classOverview:        "Class overview",
  trendsReport:         "Trends report",
  unitPerformance:      "Unit performance",
  studentFeedback:      "Student feedback",
  exportCsv:            "Export CSV",
  alertInbox:           "Alert inbox",
} as const;

// ---------------------------------------------------------------------------
// Expected hrefs
// ---------------------------------------------------------------------------

export const DASHBOARD_HREFS = {
  overview:   "/school/reports/overview",
  alerts:     "/school/alerts",
  atRisk:     "/school/reports/at-risk",
} as const;
