/**
 * Test data for section 4.7 — Pipeline Job Detail (`/admin/pipeline/[job_id]`)
 * Covers TC-IDs: ADM-26, ADM-27, ADM-28, ADM-29, ADM-30
 */

import type { PipelineJobStatus } from "@/lib/api/curriculum-admin";

export const MOCK_JOB_ID = "job-xyz-789";

export const MOCK_JOB_RUNNING: PipelineJobStatus = {
  job_id:       MOCK_JOB_ID,
  status:       "running",
  built:        5,
  failed:       0,
  total:        12,
  progress_pct: 41.7,
};

export const MOCK_JOB_DONE: PipelineJobStatus = {
  job_id:       MOCK_JOB_ID,
  status:       "done",
  built:        12,
  failed:       0,
  total:        12,
  progress_pct: 100,
};

export const MOCK_JOB_FAILED: PipelineJobStatus = {
  job_id:       MOCK_JOB_ID,
  status:       "failed",
  built:        8,
  failed:       4,
  total:        12,
  progress_pct: 100,
};

export const PIPELINE_JOB_STRINGS = {
  pageHeading: "Pipeline Job",
  backLink:    "Back to pipeline",
  // Stat box labels
  statBuilt:   "Built",
  statTotal:   "Total",
  statFailed:  "Failed",
  // Failure warning
  failureWarning: /units? failed to generate/,
} as const;
