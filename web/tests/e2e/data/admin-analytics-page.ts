/**
 * Test data for section 4.4 — Analytics (`/admin/analytics`)
 * Covers TC-IDs: ADM-11, ADM-12, ADM-13, ADM-14
 */

import type { SubscriptionAnalytics, StruggleReport } from "@/lib/api/admin";

export const MOCK_SUBSCRIPTION: SubscriptionAnalytics = {
  active_monthly: 320,
  active_annual: 180,
  total_active: 500,
  mrr_usd: "4950.00",
  new_this_month: 42,
  cancelled_this_month: 8,
  churn_rate: 0.016,
};

export const MOCK_STRUGGLE: StruggleReport = {
  generated_at: "2026-03-28T00:00:00Z",
  units: [
    {
      unit_id: "unit-001",
      unit_title: "Algebra Basics",
      grade: 8,
      subject: "Math",
      avg_score: 0.52,
      attempt_count: 340,
      fail_rate: 0.45, // >40% → red
    },
    {
      unit_id: "unit-002",
      unit_title: "Photosynthesis",
      grade: 7,
      subject: "Biology",
      avg_score: 0.78,
      attempt_count: 210,
      fail_rate: 0.15, // <20% → green
    },
  ],
};

export const ANALYTICS_STRINGS = {
  pageHeading: "Platform Analytics",
  // Subscription table
  subSectionHeading: "Subscription Breakdown",
  rowMonthly: "Monthly subscribers",
  rowAnnual: "Annual subscribers",
  rowTotal: "Total active",
  rowMrr: "MRR (CAD)",
  rowNew: "New this month",
  rowCancelled: "Cancelled this month",
  rowChurn: "Churn rate",
  // Struggle report
  struggleSectionHeading: "Struggle Report",
  colUnit: "Unit",
  colGrade: "Grade",
  colSubject: "Subject",
  colAvgScore: "Avg Score",
  colAttempts: "Attempts",
  colFailRate: "Fail Rate",
} as const;
