/**
 * Test data for section 3.6 — Reports Trends (`/school/reports/trends`)
 * Covers TC-IDs: SCH-11
 */

import type { TrendsReport } from "@/lib/api/reports";

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id:  "school-001",
  role: "teacher" as const,
};

export const MOCK_TRENDS: TrendsReport = {
  school_id: "school-001",
  period:    "4w",
  weeks: [
    { week_start: "2026-03-01", active_students: 72, lessons_viewed: 88, quiz_attempts: 52, avg_score_pct: 78.5, first_attempt_pass_rate_pct: 70.0 },
    { week_start: "2026-03-08", active_students: 80, lessons_viewed: 95, quiz_attempts: 60, avg_score_pct: 81.2, first_attempt_pass_rate_pct: 73.5 },
    { week_start: "2026-03-15", active_students: 85, lessons_viewed: 110, quiz_attempts: 65, avg_score_pct: 82.0, first_attempt_pass_rate_pct: 75.0 },
    { week_start: "2026-03-22", active_students: 90, lessons_viewed: 120, quiz_attempts: 70, avg_score_pct: 84.0, first_attempt_pass_rate_pct: 78.0 },
  ],
};

export const MOCK_TRENDS_EMPTY: TrendsReport = {
  school_id: "school-001",
  period:    "4w",
  weeks:     [],
};

export const TRENDS_STRINGS = {
  pageHeading:       "Trends Report",
  period4w:          "4 weeks",
  period12w:         "12 weeks",
  periodTerm:        "This term",
  // Chart card headings
  lessonViewsCard:   "Lesson views & active students",
  passRateCard:      "Pass rate & average score (%)",
  weeklyBreakdown:   "Weekly breakdown",
  // Table headers
  colWeek:           "Week",
  colActive:         "Active",
  colLessons:        "Lessons",
  colQuizzes:        "Quizzes",
  colAvgScore:       "Avg score",
  colPassRate:       "Pass rate",
  // Empty state
  noData:            "No trend data for this period.",
} as const;
