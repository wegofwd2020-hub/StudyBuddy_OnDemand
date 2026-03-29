/**
 * Test data for section 3.7 — Reports At-Risk (`/school/reports/at-risk`)
 * Covers TC-IDs: SCH-12, SCH-13
 */

import type { CurriculumHealthReport } from "@/lib/api/reports";

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id: "school-001",
  role: "teacher" as const,
};

export const MOCK_CURRICULUM_HEALTH: CurriculumHealthReport = {
  school_id: "school-001",
  total_units: 5,
  healthy_count: 2,
  watch_count: 1,
  struggling_count: 1,
  no_activity_count: 1,
  units: [
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
      unit_id: "G8-MATH-001",
      unit_name: "Linear Equations",
      subject: "mathematics",
      health_tier: "struggling",
      first_attempt_pass_rate_pct: 38.0,
      avg_attempts_to_pass: 3.5,
      avg_score_pct: 52.0,
      feedback_count: 8,
      avg_rating: 2.8,
      recommended_action: "Review lesson content and add practice exercises.",
    },
    {
      unit_id: "G8-SCI-002",
      unit_name: "Chemical Reactions",
      subject: "science",
      health_tier: "watch",
      first_attempt_pass_rate_pct: 58.0,
      avg_attempts_to_pass: 2.0,
      avg_score_pct: 65.0,
      feedback_count: 4,
      avg_rating: 3.2,
      recommended_action: "Monitor closely over the next two weeks.",
    },
    {
      unit_id: "G8-MATH-002",
      unit_name: "Quadratic Equations",
      subject: "mathematics",
      health_tier: "healthy",
      first_attempt_pass_rate_pct: 75.0,
      avg_attempts_to_pass: 1.5,
      avg_score_pct: 78.0,
      feedback_count: 2,
      avg_rating: 4.0,
      recommended_action: "No action required.",
    },
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
      recommended_action: "Assign to students — no one has started this unit.",
    },
  ],
};

// All units healthy — no struggling or watch units (SCH-13)
export const MOCK_CURRICULUM_ALL_HEALTHY: CurriculumHealthReport = {
  school_id: "school-001",
  total_units: 2,
  healthy_count: 2,
  watch_count: 0,
  struggling_count: 0,
  no_activity_count: 0,
  units: [
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
      unit_id: "G8-MATH-002",
      unit_name: "Quadratic Equations",
      subject: "mathematics",
      health_tier: "healthy",
      first_attempt_pass_rate_pct: 75.0,
      avg_attempts_to_pass: 1.5,
      avg_score_pct: 78.0,
      feedback_count: 2,
      avg_rating: 4.0,
      recommended_action: "No action required.",
    },
  ],
};

export const AT_RISK_STRINGS = {
  pageHeading: "At-Risk Report",
  // Tier badges
  healthy: "Healthy",
  watch: "Watch",
  struggling: "Struggling",
  noActivity: "No activity",
  // Section headings
  strugglingCard: /Struggling units/,
  watchCard: /Units to watch/,
  // Table headers (struggling table)
  colUnit: "Unit",
  colSubject: "Subject",
  colPassRate: "Pass rate",
  colAvgAttempts: "Avg attempts",
  colAction: "Recommended action",
  // Empty state (SCH-13)
  allHealthy: "No at-risk units — all units are healthy.",
} as const;
