/**
 * Test data for section 3.14 — Curriculum Upload (`/school/curriculum`)
 * Covers TC-IDs: SCH-24, SCH-25, SCH-26, SCH-27, SCH-28, SCH-29
 */

import type { UploadError } from "@/lib/api/curriculum-admin";

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id: "school-001",
  role: "teacher" as const,
};

// Successful upload response
export const MOCK_UPLOAD_SUCCESS = {
  curriculum_id: "curr-abc-123",
  unit_count: 12,
  errors: [] as UploadError[],
};

// Upload with per-row errors (SCH-27)
export const MOCK_UPLOAD_ERRORS = {
  curriculum_id: null,
  unit_count: 0,
  errors: [
    { row: 2, field: "subject", message: "Invalid subject value 'maths'." },
    { row: 5, field: "unit_name", message: "unit_name is required." },
  ] as UploadError[],
};

// File-level error where row = 0 (SCH-28)
export const MOCK_UPLOAD_FILE_ERROR = {
  curriculum_id: null,
  unit_count: 0,
  errors: [
    { row: 0, field: "file", message: "Missing required header columns." },
  ] as UploadError[],
};

// Pipeline trigger response
export const MOCK_PIPELINE_RESPONSE = {
  job_id: "job-xyz-789",
  status: "queued",
};

export const CURRICULUM_STRINGS = {
  pageHeading: "Curriculum Management",
  // Step headings
  step1Heading: "Step 1 — Download the template",
  step2Heading: "Step 2 — Upload your curriculum",
  // Buttons
  downloadTemplateBtn: "Download XLSX template",
  uploadBtn: "Upload & generate content",
  uploadingBtn: "Uploading…",
  // Labels
  gradeLabel: "Grade",
  yearLabel: "Academic year",
  // Success message
  successMsg: /Uploaded \d+ units?\. Redirecting/,
  // Error table headers
  errorRowHeader: "Row",
  errorFieldHeader: "Field",
  errorMessageHeader: "Error",
  // Row 0 displayed as dash (SCH-28)
  rowDash: "—",
} as const;
