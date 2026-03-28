/**
 * Test data for section 3.4 — Student Detail (`/school/student/[student_id]`)
 * Covers TC-IDs: SCH-08
 *
 * Auth note: requires a real Auth0 session for E2E.
 * Unit tests mock useTeacher(), useParams(), and useQuery directly.
 *
 * Backend API route for E2E page.route() interception:
 *   GET /api/v1/reports/school/{school_id}/student/{student_id} → MOCK_STUDENT_REPORT
 */

import type { StudentReport } from "@/lib/api/reports";

// ---------------------------------------------------------------------------
// Mock teacher claims
// ---------------------------------------------------------------------------

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id:  "school-001",
  role: "teacher" as const,
};

export const MOCK_STUDENT_ID = "stu-001";

// ---------------------------------------------------------------------------
// Mock student report — full data (SCH-08)
// ---------------------------------------------------------------------------

export const MOCK_STUDENT_REPORT: StudentReport = {
  school_id:                   "school-001",
  student_id:                  "stu-001",
  student_name:                "Alice Chen",
  grade:                       8,
  last_active:                 "2026-03-27T10:00:00Z",
  units_completed:             6,
  units_in_progress:           2,
  first_attempt_pass_rate_pct: 83.0,
  overall_avg_score_pct:       84.0,
  total_time_spent_s:          7200,  // 2h 0m
  strongest_subject:           "Science",
  needs_attention_subject:     "Mathematics",
  per_unit: [
    {
      unit_id:       "G8-SCI-001",
      unit_name:     "Cell Biology",
      subject:       "science",
      lesson_viewed: true,
      quiz_attempts: 2,
      best_score:    90.0,
      passed:        true,
      avg_duration_s: 1200,
    },
    {
      unit_id:       "G8-MATH-001",
      unit_name:     "Linear Equations",
      subject:       "mathematics",
      lesson_viewed: true,
      quiz_attempts: 3,
      best_score:    55.0,
      passed:        false,
      avg_duration_s: 900,
    },
    {
      unit_id:       "G8-SCI-002",
      unit_name:     "Chemical Reactions",
      subject:       "science",
      lesson_viewed: false,
      quiz_attempts: 0,
      best_score:    null,
      passed:        false,
      avg_duration_s: 0,
    },
  ],
};

// ---------------------------------------------------------------------------
// Expected UI strings
// ---------------------------------------------------------------------------

export const STUDENT_DETAIL_STRINGS = {
  backBtn:          "← Class",
  unitProgressCard: "Unit progress",
  // KPI labels
  unitsCompleted:   "Units completed",
  inProgress:       "In progress",
  passRate:         "Pass rate",
  timeSpent:        "Time spent",
  // Subject tags
  strongestPrefix:  "Strongest:",
  attentionPrefix:  "Needs attention:",
  // Table headers
  colUnit:          "Unit",
  colSubject:       "Subject",
  colLesson:        "Lesson",
  colAttempts:      "Attempts",
  colBestScore:     "Best score",
  colTime:          "Time",
  // Time formatting
  twoHours:         "2h 0m",
} as const;

// ---------------------------------------------------------------------------
// Href helper
// ---------------------------------------------------------------------------

export const BACK_HREF = "/school/class/all";
