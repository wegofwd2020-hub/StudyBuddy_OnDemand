/**
 * Test data for section 4.5 — Pipeline List (`/admin/pipeline`)
 * Covers TC-IDs: ADM-15, ADM-16, ADM-17, ADM-18, ADM-19
 */

import type { PipelineJobsResponse } from "@/lib/api/admin";

export const MOCK_JOBS: PipelineJobsResponse = {
  jobs: [
    {
      job_id:        "job-aaa-001",
      curriculum_id: "default-2026-g8",
      grade:         8,
      status:        "running",
      progress_pct:  55,
      built:         7,
      failed:        0,
      total:         12,
      triggered_by:  "adm-001",
      triggered_at:  "2026-03-28T06:00:00Z",
    },
    {
      job_id:        "job-bbb-002",
      curriculum_id: "default-2026-g9",
      grade:         9,
      status:        "done",
      progress_pct:  100,
      built:         12,
      failed:        0,
      total:         12,
      triggered_by:  "adm-001",
      triggered_at:  "2026-03-27T06:00:00Z",
    },
    {
      job_id:        "job-ccc-003",
      curriculum_id: "default-2026-g7",
      grade:         7,
      status:        "failed",
      progress_pct:  100,
      built:         10,
      failed:        2,
      total:         12,
      triggered_by:  "adm-001",
      triggered_at:  "2026-03-26T06:00:00Z",
    },
    {
      job_id:        "job-ddd-004",
      curriculum_id: "default-2026-g6",
      grade:         6,
      status:        "queued",
      progress_pct:  0,
      built:         0,
      failed:        0,
      total:         12,
      triggered_by:  "adm-001",
      triggered_at:  "2026-03-28T07:00:00Z",
    },
  ],
};

export const PIPELINE_LIST_STRINGS = {
  pageHeading:    "Pipeline Jobs",
  triggerJobLink: "Trigger job",
  // Table column headers
  colJobId:       "Job ID",
  colCurriculum:  "Curriculum",
  colStatus:      "Status",
  colProgress:    "Progress",
  colTriggered:   "Triggered",
  // Status values
  statusRunning:  "running",
  statusDone:     "done",
  statusFailed:   "failed",
  statusQueued:   "queued",
} as const;
