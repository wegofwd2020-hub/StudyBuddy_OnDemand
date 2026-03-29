/**
 * Test data for section 3.11 — Reports Export CSV (`/school/reports/export`)
 * Covers TC-IDs: SCH-17, SCH-18
 */

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id: "school-001",
  role: "teacher" as const,
};

export const EXPORT_STRINGS = {
  pageHeading: "Export CSV",
  // Report option labels
  overviewReport: "Overview Report",
  trendsReport: "Trends Report",
  unitPerformance: "Unit Performance",
  // Button states
  downloadBtn: "Download CSV",
  generatingBtn: "Generating…",
  downloadedBtn: "Downloaded",
  // Error
  exportError: "Export failed. Please try again.",
  // Select card heading
  selectReport: "Select report",
} as const;
