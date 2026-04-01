/**
 * Test data for section 4.5 — Pipeline List (`/admin/pipeline`)
 * Covers TC-IDs: ADM-15, ADM-16, ADM-17, ADM-18, ADM-19
 */

import type { PipelineJobsResponse } from "@/lib/api/admin";

export const MOCK_JOBS: PipelineJobsResponse = {
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
      status: "done",
      progress_pct: 100,
      built: 12,
      failed: 0,
      total: 12,
      triggered_by_email: "admin@example.com",
      triggered_at: "2026-03-27T06:00:00Z",
      started_at: "2026-03-27T06:00:05Z",
      completed_at: "2026-03-27T06:14:00Z",
      error: null,
      payload_bytes: 409600,
    },
    {
      job_id: "job-ccc-003",
      curriculum_id: "default-2026-g7",
      grade: 7,
      langs: "en",
      force: false,
      status: "failed",
      progress_pct: 100,
      built: 10,
      failed: 2,
      total: 12,
      triggered_by_email: "admin@example.com",
      triggered_at: "2026-03-26T06:00:00Z",
      started_at: "2026-03-26T06:00:05Z",
      completed_at: "2026-03-26T06:12:00Z",
      error: "Unit G7-SCI-011 failed schema validation",
      payload_bytes: 204800,
    },
    {
      job_id: "job-ddd-004",
      curriculum_id: "default-2026-g6",
      grade: 6,
      langs: "en",
      force: false,
      status: "queued",
      progress_pct: 0,
      built: 0,
      failed: 0,
      total: 12,
      triggered_by_email: "admin@example.com",
      triggered_at: "2026-03-28T07:00:00Z",
      started_at: null,
      completed_at: null,
      error: null,
      payload_bytes: null,
    },
  ],
};

export const PIPELINE_LIST_STRINGS = {
  pageHeading: "Pipeline Jobs",
  triggerJobLink: "Trigger job",
  // Table column headers
  colJobId: "Job",
  colCurriculum: "Curriculum",
  colStatus: "Status",
  colProgress: "Progress",
  colTriggered: "Triggered",
  // Status values
  statusRunning: "running",
  statusDone: "done",
  statusFailed: "failed",
  statusQueued: "queued",
} as const;
