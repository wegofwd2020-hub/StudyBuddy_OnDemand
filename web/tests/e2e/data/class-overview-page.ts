/**
 * Test data for section 3.3 — Class Overview (`/school/class/[class_id]`)
 * Covers TC-IDs: SCH-06, SCH-07
 *
 * Auth note: requires a real Auth0 session for E2E.
 * Unit tests mock useTeacher() and useQuery (class-metrics) directly.
 *
 * Backend API routes for E2E page.route() interception:
 *   GET /api/v1/analytics/school/{school_id}/class → MOCK_CLASS_METRICS
 */

import type { ClassMetricsResponse } from "@/lib/api/reports";

// ---------------------------------------------------------------------------
// Mock teacher claims
// ---------------------------------------------------------------------------

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id: "school-001",
  role: "teacher" as const,
};

// ---------------------------------------------------------------------------
// Mock class metrics — 4 students, mix of grades and scores (SCH-06)
// ---------------------------------------------------------------------------

export const MOCK_CLASS_METRICS: ClassMetricsResponse = {
  school_id: "school-001",
  grade: null,
  subject: null,
  students: [
    {
      student_id: "stu-001",
      student_name: "Alice Chen",
      grade: 8,
      units_completed: 6,
      total_units: 10,
      avg_score_pct: 84.0,
      last_active: "2026-03-27T10:00:00Z",
    },
    {
      student_id: "stu-002",
      student_name: "Ben Okafor",
      grade: 8,
      units_completed: 3,
      total_units: 10,
      avg_score_pct: 55.0,
      last_active: "2026-03-25T09:00:00Z",
    },
    {
      student_id: "stu-003",
      student_name: "Chloe Martin",
      grade: 7,
      units_completed: 8,
      total_units: 10,
      avg_score_pct: 91.0,
      last_active: "2026-03-28T08:30:00Z",
    },
    {
      student_id: "stu-004",
      student_name: "David Lee",
      grade: 8,
      units_completed: 0,
      total_units: 10,
      avg_score_pct: 0.0,
      last_active: null,
    },
  ],
};

// ---------------------------------------------------------------------------
// Empty class (edge case)
// ---------------------------------------------------------------------------

export const MOCK_CLASS_METRICS_EMPTY: ClassMetricsResponse = {
  school_id: "school-001",
  grade: null,
  subject: null,
  students: [],
};

// ---------------------------------------------------------------------------
// Expected UI strings
// ---------------------------------------------------------------------------

export const CLASS_STRINGS = {
  pageHeading: "Class Overview",
  detailBtn: "Detail",
  noStudents: "No students found.",
  gradeAll: "All",
  // Table column headers
  colStudent: "Student",
  colGrade: "Grade",
  colUnitsDone: "Units done",
  colAvgScore: "Avg score",
  colLastActive: "Last active",
  neverActive: "Never",
} as const;

// ---------------------------------------------------------------------------
// Href helper (SCH-07)
// ---------------------------------------------------------------------------

export function studentDetailHref(studentId: string) {
  return `/school/student/${studentId}`;
}
