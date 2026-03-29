/**
 * Test data for section 3.9 — Reports Engagement (`/school/reports/engagement`)
 * Covers TC-IDs: SCH-15
 */

import type { OverviewReport, CurriculumHealthReport } from "@/lib/api/reports";

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id: "school-001",
  role: "teacher" as const,
};

export const MOCK_OVERVIEW_30D: OverviewReport = {
  school_id: "school-001",
  period: "30d",
  enrolled_students: 120,
  active_students_period: 85,
  active_pct: 70.8,
  lessons_viewed: 340,
  quiz_attempts: 210,
  first_attempt_pass_rate_pct: 72.0,
  audio_play_rate_pct: 45.0,
  units_with_struggles: [],
  units_no_activity: [],
  unreviewed_feedback_count: 3,
};

// 100% active — no inactive students card
export const MOCK_OVERVIEW_FULL_ACTIVE: OverviewReport = {
  ...MOCK_OVERVIEW_30D,
  active_students_period: 120,
  active_pct: 100.0,
};

export const MOCK_HEALTH_WITH_NO_ACTIVITY: CurriculumHealthReport = {
  school_id: "school-001",
  total_units: 2,
  healthy_count: 1,
  watch_count: 0,
  struggling_count: 0,
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

export const MOCK_HEALTH_ALL_ACTIVE: CurriculumHealthReport = {
  ...MOCK_HEALTH_WITH_NO_ACTIVITY,
  no_activity_count: 0,
  units: MOCK_HEALTH_WITH_NO_ACTIVITY.units.filter(
    (u) => u.health_tier !== "no_activity",
  ),
};

export const ENGAGEMENT_STRINGS = {
  pageHeading: "Engagement Report",
  period30d: "Last 30 days",
  // KPI cards
  activeStudents: "Active students",
  activityRate: "Activity rate",
  audioEngagement: "Audio engagement",
  // Inactive card
  inactiveStudents: "Inactive students",
  // Zero activity units card
  zeroActivityCard: "Units with zero activity",
} as const;
