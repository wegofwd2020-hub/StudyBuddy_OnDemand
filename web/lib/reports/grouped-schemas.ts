/**
 * Grouped report response schemas (EH-004: Grade/STEAM hierarchy)
 *
 * All reports are grouped by Grade > Subject > Items hierarchy.
 * Mirrors the design from #776 (groupByGradeThenSubject utility).
 */

export interface GroupedItem<T> {
  grade: number;
  subject: string;
  items: T[];
}

export interface GroupedReport<T> {
  groups: GroupedItem<T>[];
  totalItems: number;
  selectedGrade?: number | null;
  selectedSubject?: string | null;
}

// ── Feedback Report (grouped) ──

export interface FeedbackRow {
  feedback_id: string;
  student_id: string;
  student_name: string;
  message: string;
  content_type: string;
  helpful?: boolean;
  created_at: string;
}

export interface GroupedFeedbackReport extends GroupedReport<FeedbackRow> {
  filters: {
    availableGrades: number[];
    availableSubjects: string[];
  };
}

// ── Unit Report (grouped) ──

export interface UnitRow {
  unit_id: string;
  unit_name: string;
  health_tier: "healthy" | "watch" | "struggling" | "no_activity";
  first_attempt_pass_rate_pct: number;
  feedback_count: number;
}

export interface GroupedUnitReport extends GroupedReport<UnitRow> {
  filters: {
    availableGrades: number[];
    availableSubjects: string[];
  };
}

// ── CSV Export (grouped) ──

export interface CSVGroupedRow {
  grade: number;
  subject: string;
  [key: string]: unknown;
}

// ── Query params for grouped endpoints ──

export interface GroupedReportParams {
  grade?: number | null;
  subject?: string | null;
}
