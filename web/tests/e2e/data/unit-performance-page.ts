/**
 * Test data for section 3.8 — Reports Unit Performance (`/school/reports/units`)
 * Covers TC-IDs: SCH-14
 */

import type { CurriculumHealthReport } from "@/lib/api/reports";

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id: "school-001",
  role: "teacher" as const,
};

export const MOCK_HEALTH: CurriculumHealthReport = {
  school_id: "school-001",
  total_units: 3,
  healthy_count: 2,
  watch_count: 0,
  struggling_count: 1,
  no_activity_count: 0,
  units: [
    {
      unit_id: "G8-MATH-001",
      unit_name: "Linear Equations",
      subject: "mathematics",
      health_tier: "struggling",
      first_attempt_pass_rate_pct: 38.0,
      avg_attempts_to_pass: 3.5,
      avg_score_pct: 52.0,
      feedback_count: 8,
      avg_rating: 2.8,
      recommended_action: "Review lesson content.",
    },
    {
      unit_id: "G8-SCI-001",
      unit_name: "Cell Biology",
      subject: "science",
      health_tier: "healthy",
      first_attempt_pass_rate_pct: 88.0,
      avg_attempts_to_pass: 1.2,
      avg_score_pct: 85.0,
      feedback_count: 3,
      avg_rating: 4.5,
      recommended_action: "No action required.",
    },
    {
      unit_id: "G8-SCI-002",
      unit_name: "Chemical Reactions",
      subject: "science",
      health_tier: "healthy",
      first_attempt_pass_rate_pct: 72.0,
      avg_attempts_to_pass: 1.8,
      avg_score_pct: 74.0,
      feedback_count: 5,
      avg_rating: 3.9,
      recommended_action: "No action required.",
    },
  ],
};

export const MOCK_HEALTH_NO_ACTIVITY: CurriculumHealthReport = {
  school_id: "school-001",
  total_units: 1,
  healthy_count: 0,
  watch_count: 0,
  struggling_count: 0,
  no_activity_count: 1,
  units: [
    {
      unit_id: "G8-PHY-001",
      unit_name: "Newton's Laws",
      subject: "physics",
      health_tier: "no_activity",
      first_attempt_pass_rate_pct: 0.0,
      avg_attempts_to_pass: 0.0,
      avg_score_pct: 0.0,
      feedback_count: 0,
      avg_rating: null,
      recommended_action: "Assign to students.",
    },
  ],
};

export const UNIT_PERF_STRINGS = {
  pageHeading: "Unit Performance",
  chartCard: "First-attempt pass rate by unit",
  allUnitsCard: "All units",
  // Table headers
  colUnit: "Unit",
  colSubject: "Subject",
  colPassRate: "Pass rate",
  colAvgScore: "Avg score",
  colAvgAttempts: "Avg attempts",
  colFeedback: "Feedback",
  // Legend
  legendHealthy: "Healthy",
  legendWatch: "Watch",
  legendStruggling: "Struggling",
  // Empty state
  noActivity: "No unit activity recorded yet.",
} as const;
