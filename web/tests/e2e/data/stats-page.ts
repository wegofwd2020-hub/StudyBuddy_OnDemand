/**
 * Test data for section 2.9 — Stats Page (`/stats`)
 * Covers TC-IDs: STU-31
 *
 * Auth note: /stats requires a real Auth0 session for E2E.
 * Unit tests mock useStudentStats() directly via vi.mock.
 *
 * Backend API route for E2E page.route() interception:
 *   GET /api/v1/analytics/student/stats?period=30d → MOCK_STUDENT_STATS
 */

import type { StudentStats } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Mock stats — active streak, all KPIs populated, 3-subject breakdown (STU-31)
// ---------------------------------------------------------------------------

export const MOCK_STUDENT_STATS: StudentStats = {
  streak_days: 5,
  lessons_viewed: 12,
  quizzes_completed: 8,
  pass_rate: 0.75,
  avg_score: 0.82,
  audio_sessions: 4,
  session_dates: ["2026-03-28", "2026-03-27", "2026-03-26", "2026-03-25", "2026-03-24"],
  subject_breakdown: [
    { subject: "Science", lessons: 6, pass_rate: 0.83 },
    { subject: "Mathematics", lessons: 4, pass_rate: 0.75 },
    { subject: "English", lessons: 2, pass_rate: 0.5 },
  ],
};

// ---------------------------------------------------------------------------
// Mock stats — no streak, no subject breakdown (edge cases)
// ---------------------------------------------------------------------------

export const MOCK_STUDENT_STATS_ZERO: StudentStats = {
  streak_days: 0,
  lessons_viewed: 0,
  quizzes_completed: 0,
  pass_rate: 0,
  avg_score: 0,
  audio_sessions: 0,
  session_dates: [],
  subject_breakdown: [],
};

// ---------------------------------------------------------------------------
// Expected UI strings
// (keys match useTranslations("stats_screen") — mock returns key as-is)
// ---------------------------------------------------------------------------

export const STATS_STRINGS = {
  title: "title",
  lessonsViewed: "lessons_viewed",
  quizzesCompleted: "quizzes_completed",
  passRate: "pass_rate",
  avgScore: "avg_score",
  audioPlayed: "audio_played",
  subjectBreakdown: "Subject Breakdown",
} as const;

// ---------------------------------------------------------------------------
// Period selector labels
// ---------------------------------------------------------------------------

export const PERIOD_LABELS = ["Last 7 days", "Last 30 days", "All time"] as const;
