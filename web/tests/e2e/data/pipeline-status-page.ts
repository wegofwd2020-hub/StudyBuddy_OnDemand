/**
 * Test data for section 3.15 — Pipeline Status (`/school/curriculum/pipeline/[job_id]`)
 * Covers TC-IDs: SCH-30, SCH-31, SCH-32, SCH-33, SCH-34
 */

import type { PipelineJobStatus } from "@/lib/api/curriculum-admin";

export const MOCK_JOB_ID = "job-xyz-789";

// Running job (SCH-30, SCH-31)
export const MOCK_JOB_RUNNING: PipelineJobStatus = {
  job_id: MOCK_JOB_ID,
  status: "running",
  built: 5,
  failed: 0,
  total: 12,
  progress_pct: 41.7,
};

// Done job (SCH-32)
export const MOCK_JOB_DONE: PipelineJobStatus = {
  job_id: MOCK_JOB_ID,
  status: "done",
  built: 12,
  failed: 0,
  total: 12,
  progress_pct: 100,
};

// Failed job (SCH-33)
export const MOCK_JOB_FAILED: PipelineJobStatus = {
  job_id: MOCK_JOB_ID,
  status: "failed",
  built: 8,
  failed: 4,
  total: 12,
  progress_pct: 100,
};

// Queued job
export const MOCK_JOB_QUEUED: PipelineJobStatus = {
  job_id: MOCK_JOB_ID,
  status: "queued",
  built: 0,
  failed: 0,
  total: 12,
  progress_pct: 0,
};

export const PIPELINE_STRINGS = {
  pageHeading: "Pipeline Status",
  backLink: "← Curriculum",
  // Progress line
  progressPct: (pct: number) => `${pct.toFixed(0)}%`,
  builtSummary: (b: number, f: number, t: number) =>
    `${b} built · ${f} failed · ${t} total`,
  // Done state (SCH-32)
  doneMsg: /Content generation complete/,
  // Failed state (SCH-33)
  failedMsg: /Pipeline failed/,
  // Polling message (while not finished)
  pollingMsg: "Refreshing every 5 seconds…",
  // Status value shown in card
  statusRunning: "running",
  statusDone: "done",
  statusFailed: "failed",
} as const;
