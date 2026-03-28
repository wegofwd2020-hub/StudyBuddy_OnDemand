/**
 * Test data for section 2.2 — Student Dashboard (`/dashboard`)
 * Covers TC-IDs: STU-04 through STU-11
 *
 * Auth note: all /dashboard E2E tests require a real Auth0 session.
 * This file provides:
 *   1. Mock API payloads — used in unit tests and for future E2E with auth
 *   2. Quick action definitions — verified in unit tests (STU-05/06/07)
 *   3. UI strings — used in unit + E2E assertions
 *
 * Backend API routes intercepted by page.route() when running E2E with auth:
 *   GET /api/v1/progress/history?limit=5  → MOCK_PROGRESS_WITH_SESSIONS | MOCK_PROGRESS_EMPTY
 *   GET /api/v1/analytics/student?period=30d → MOCK_STATS
 */

import type { StudentStats, ProgressHistory } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Mock API response — stats with active streak (STU-04)
// ---------------------------------------------------------------------------

const today = new Date().toISOString().slice(0, 10);
const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);

export const MOCK_STATS: StudentStats = {
  streak_days: 3,
  lessons_viewed: 12,
  quizzes_completed: 8,
  pass_rate: 75,
  avg_score: 82,
  audio_sessions: 5,
  session_dates: [today, yesterday],
  subject_breakdown: [
    { subject: "Mathematics", lessons: 6, pass_rate: 80 },
    { subject: "Science", lessons: 6, pass_rate: 70 },
  ],
};

export const MOCK_STATS_NO_STREAK: StudentStats = {
  ...MOCK_STATS,
  streak_days: 0,
  session_dates: [],
};

// ---------------------------------------------------------------------------
// Mock API response — progress history with sessions (STU-08)
// ---------------------------------------------------------------------------

export const MOCK_PROGRESS_WITH_SESSIONS: ProgressHistory = {
  sessions: [
    {
      session_id: "sess-001",
      unit_id: "unit-001",
      unit_title: "Algebra: Linear Equations",
      subject: "Mathematics",
      started_at: new Date(Date.now() - 3600000).toISOString(),
      ended_at: new Date().toISOString(),
      score: 8,
      total: 10,
      passed: true,
      attempt_number: 1,
    },
    {
      session_id: "sess-002",
      unit_id: "unit-002",
      unit_title: "Cell Biology",
      subject: "Science",
      started_at: new Date(Date.now() - 86400000).toISOString(),
      ended_at: new Date(Date.now() - 82800000).toISOString(),
      score: 4,
      total: 10,
      passed: false,
      attempt_number: 1,
    },
  ],
  unit_progress: [],
};

// ---------------------------------------------------------------------------
// Mock API response — empty history (STU-09)
// ---------------------------------------------------------------------------

export const MOCK_PROGRESS_EMPTY: ProgressHistory = {
  sessions: [],
  unit_progress: [],
};

// ---------------------------------------------------------------------------
// STU-05 / STU-06 / STU-07 — Quick action buttons
// ---------------------------------------------------------------------------

export const QUICK_ACTIONS: ReadonlyArray<{ label: string; href: string }> = [
  { label: "Browse Subjects", href: "/subjects"    }, // STU-05
  { label: "Curriculum Map",  href: "/curriculum"  }, // STU-06
  { label: "View Progress",   href: "/progress"    }, // STU-07
];

// ---------------------------------------------------------------------------
// UI strings (sourced from i18n/en.json)
// ---------------------------------------------------------------------------

export const DASHBOARD_STRINGS = {
  title:          "Dashboard",
  noActivity:     "No recent activity",
  continueBtn:    "Continue Learning",
  recentHeading:  "Recent Activity",
  offlineAlert:   "No internet connection. Your progress will sync when you're back online.",
} as const;

// ---------------------------------------------------------------------------
// Backend API URL patterns for E2E page.route() interception
// ---------------------------------------------------------------------------

export const API_ROUTES = {
  progressHistory: "**/api/v1/progress/history*",
  studentStats:    "**/api/v1/analytics/student*",
} as const;
