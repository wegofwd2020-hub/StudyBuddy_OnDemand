/**
 * Test data for section 3.7 — Reports At-Risk (`/school/reports/at-risk`)
 * Covers TC-IDs: SCH-12, SCH-13
 *
 * The at-risk report was redesigned from a per-unit "curriculum health"
 * breakdown into a per-student "At-Risk Students" list: students who are
 * inactive and/or have a low pass rate, split into "Needs attention" (unseen)
 * and "Reviewed" (marked seen) sections with Remind / Mark-seen actions.
 */

import type { AtRiskListResponse } from "@/lib/api/reports";

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id: "school-001",
  role: "teacher" as const,
};

// Two unseen (one inactive, one low-pass-rate) + one already reviewed.
export const MOCK_AT_RISK: AtRiskListResponse = {
  school_id: "school-001",
  inactive_days_threshold: 14,
  pass_rate_threshold: 50,
  total: 3,
  students: [
    {
      student_id: "stu-001",
      student_name: "Ava Thompson",
      grade: 8,
      last_active: "2026-04-25T10:00:00Z",
      inactive_days: 27,
      pass_rate_pct: 72,
      units_completed: 4,
      total_units: 10,
      risk_reasons: { inactive: true, low_pass_rate: false },
      is_seen: false,
      seen_at: null,
    },
    {
      student_id: "stu-002",
      student_name: "Ben Carter",
      grade: 7,
      last_active: "2026-05-20T10:00:00Z",
      inactive_days: null,
      pass_rate_pct: 34,
      units_completed: 6,
      total_units: 10,
      risk_reasons: { inactive: false, low_pass_rate: true },
      is_seen: false,
      seen_at: null,
    },
    {
      student_id: "stu-003",
      student_name: "Chloe Diaz",
      grade: 9,
      last_active: null,
      inactive_days: null,
      pass_rate_pct: null,
      units_completed: 0,
      total_units: 10,
      risk_reasons: { inactive: true, low_pass_rate: true },
      is_seen: true,
      seen_at: "2026-05-18T10:00:00Z",
    },
  ],
};

// No at-risk students — empty state (SCH-13)
export const MOCK_AT_RISK_NONE: AtRiskListResponse = {
  school_id: "school-001",
  inactive_days_threshold: 14,
  pass_rate_threshold: 50,
  total: 0,
  students: [],
};

export const AT_RISK_STRINGS = {
  pageHeading: "At-Risk Students",
  needsAttention: /Needs attention/,
  reviewed: /Reviewed/,
  remindBtn: "Remind",
  markSeenBtn: "Mark seen",
  unmarkBtn: "Unmark",
  // Empty state (SCH-13)
  noStudents: "No at-risk students",
} as const;
