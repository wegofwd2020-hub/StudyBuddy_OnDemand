/**
 * Test data for section 4.7 — Pipeline Job Detail (`/admin/pipeline/[job_id]`)
 * Covers TC-IDs: ADM-26, ADM-27, ADM-28, ADM-29, ADM-30
 */

import type { AdminPipelineJob } from "@/lib/api/admin";

export const MOCK_JOB_ID = "job-xyz-789";

export const MOCK_JOB_RUNNING: AdminPipelineJob = {
  job_id: MOCK_JOB_ID,
  curriculum_id: "default-2026-g8",
  grade: 8,
  langs: "en",
  force: false,
  status: "running",
  built: 5,
  failed: 0,
  total: 12,
  progress_pct: 41.7,
  triggered_by_email: "admin@example.com",
  triggered_at: "2026-03-28T06:00:00Z",
  started_at: "2026-03-28T06:00:05Z",
  completed_at: null,
  error: null,
  payload_bytes: null,
};

export const MOCK_JOB_DONE: AdminPipelineJob = {
  job_id: MOCK_JOB_ID,
  curriculum_id: "default-2026-g8",
  grade: 8,
  langs: "en",
  force: false,
  status: "done",
  built: 12,
  failed: 0,
  total: 12,
  progress_pct: 100,
  triggered_by_email: "admin@example.com",
  triggered_at: "2026-03-27T06:00:00Z",
  started_at: "2026-03-27T06:00:05Z",
  completed_at: "2026-03-27T06:14:00Z",
  error: null,
  payload_bytes: 409600,
};

export const MOCK_JOB_FAILED: AdminPipelineJob = {
  job_id: MOCK_JOB_ID,
  curriculum_id: "default-2026-g8",
  grade: 8,
  langs: "en",
  force: false,
  status: "failed",
  built: 8,
  failed: 4,
  total: 12,
  progress_pct: 100,
  triggered_by_email: "admin@example.com",
  triggered_at: "2026-03-26T06:00:00Z",
  started_at: "2026-03-26T06:00:05Z",
  completed_at: "2026-03-26T06:12:00Z",
  error: "4 units failed to generate",
  payload_bytes: 204800,
};

export const PIPELINE_JOB_STRINGS = {
  pageHeading: "Pipeline Job",
  backLink: "Back to pipeline",
  // Stat box labels
  statBuilt: "Built",
  statTotal: "Total",
  statFailed: "Failed",
  // Failure warning — matches the error message shown in the red error box
  failureWarning: /4 units failed to generate/,
} as const;
