/**
 * Test data for section 4.3 — Admin Dashboard (`/admin/dashboard`)
 * Covers TC-IDs: ADM-07, ADM-08, ADM-09
 */

import type { SubscriptionAnalytics, PipelineJobsResponse } from "@/lib/api/admin";

export const MOCK_ANALYTICS: SubscriptionAnalytics = {
  active_monthly: 320,
  active_annual: 180,
  total_active: 500,
  mrr_usd: "4950.00",
  new_this_month: 42,
  cancelled_this_month: 8,
  churn_rate: 0.016,
};

export const MOCK_PIPELINE_JOBS: PipelineJobsResponse = {
  jobs: [
    {
      job_id: "job-aaa-001",
      curriculum_id: "default-2026-g8",
      grade: 8,
      langs: "en",
      force: false,
      status: "running",
      progress_pct: 55,
      built: 7,
      failed: 0,
      total: 12,
      triggered_by_email: "admin@example.com",
      triggered_at: "2026-03-28T06:00:00Z",
      started_at: "2026-03-28T06:00:05Z",
      completed_at: null,
      error: null,
      payload_bytes: null,
    },
    {
      job_id: "job-bbb-002",
      curriculum_id: "default-2026-g9",
      grade: 9,
      langs: "en",
      force: false,
      status: "failed",
      progress_pct: 100,
      built: 10,
      failed: 2,
      total: 12,
      triggered_by_email: "admin@example.com",
      triggered_at: "2026-03-27T06:00:00Z",
      started_at: "2026-03-27T06:00:05Z",
      completed_at: "2026-03-27T06:15:00Z",
      error: "Unit G9-MATH-011 failed schema validation",
      payload_bytes: 204800,
    },
  ],
};

export const DASHBOARD_STRINGS = {
  pageHeading: "Platform Dashboard",
  // KPI card labels
  totalActive: "Total Active",
  mrr: "MRR",
  newThisMonth: "New This Month",
  churnRate: "Churn Rate",
  // Pipeline section
  pipelineLabel: "Pipeline",
  totalJobs: "Total Jobs",
  activeJobs: "Active",
  failedJobs: "Failed",
} as const;
