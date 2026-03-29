import schoolApi from "./school-client";

// ── Shared ────────────────────────────────────────────────────────────────────

export type ReportPeriod = "7d" | "30d" | "term";
export type TrendsPeriod = "4w" | "12w" | "term";
export type ReportType =
  | "overview"
  | "unit"
  | "student"
  | "curriculum-health"
  | "feedback"
  | "trends";

// ── Overview Report ───────────────────────────────────────────────────────────

export interface OverviewReport {
  school_id: string;
  period: string;
  enrolled_students: number;
  active_students_period: number;
  active_pct: number;
  lessons_viewed: number;
  quiz_attempts: number;
  first_attempt_pass_rate_pct: number;
  audio_play_rate_pct: number;
  units_with_struggles: string[];
  units_no_activity: string[];
  unreviewed_feedback_count: number;
}

export async function getOverviewReport(
  schoolId: string,
  period: ReportPeriod = "7d",
): Promise<OverviewReport> {
  const res = await schoolApi.get<OverviewReport>(
    `/reports/school/${schoolId}/overview`,
    { params: { period } },
  );
  return res.data;
}

// ── Curriculum Health (At-Risk / Unit Performance base) ───────────────────────

export interface CurriculumHealthUnit {
  unit_id: string;
  unit_name: string | null;
  subject: string;
  health_tier: "healthy" | "watch" | "struggling" | "no_activity";
  first_attempt_pass_rate_pct: number;
  avg_attempts_to_pass: number;
  avg_score_pct: number;
  feedback_count: number;
  avg_rating: number | null;
  recommended_action: string;
}

export interface CurriculumHealthReport {
  school_id: string;
  total_units: number;
  healthy_count: number;
  watch_count: number;
  struggling_count: number;
  no_activity_count: number;
  units: CurriculumHealthUnit[];
}

export async function getCurriculumHealth(
  schoolId: string,
): Promise<CurriculumHealthReport> {
  const res = await schoolApi.get<CurriculumHealthReport>(
    `/reports/school/${schoolId}/curriculum-health`,
  );
  return res.data;
}

// ── Trends Report ─────────────────────────────────────────────────────────────

export interface TrendsWeek {
  week_start: string;
  active_students: number;
  lessons_viewed: number;
  quiz_attempts: number;
  avg_score_pct: number;
  first_attempt_pass_rate_pct: number;
}

export interface TrendsReport {
  school_id: string;
  period: string;
  weeks: TrendsWeek[];
}

export async function getTrendsReport(
  schoolId: string,
  period: TrendsPeriod = "4w",
): Promise<TrendsReport> {
  const res = await schoolApi.get<TrendsReport>(`/reports/school/${schoolId}/trends`, {
    params: { period },
  });
  return res.data;
}

// ── Student Report ────────────────────────────────────────────────────────────

export interface PerUnitStudentItem {
  unit_id: string;
  unit_name: string | null;
  subject: string;
  lesson_viewed: boolean;
  quiz_attempts: number;
  best_score: number | null;
  passed: boolean;
  avg_duration_s: number;
}

export interface StudentReport {
  school_id: string;
  student_id: string;
  student_name: string;
  grade: number;
  last_active: string | null;
  units_completed: number;
  units_in_progress: number;
  first_attempt_pass_rate_pct: number;
  overall_avg_score_pct: number;
  total_time_spent_s: number;
  per_unit: PerUnitStudentItem[];
  strongest_subject: string | null;
  needs_attention_subject: string | null;
}

export async function getStudentReport(
  schoolId: string,
  studentId: string,
): Promise<StudentReport> {
  const res = await schoolApi.get<StudentReport>(
    `/reports/school/${schoolId}/student/${studentId}`,
  );
  return res.data;
}

// ── Class Metrics (for Class Overview page) ───────────────────────────────────

export interface ClassStudentRow {
  student_id: string;
  student_name: string;
  grade: number;
  units_completed: number;
  total_units: number;
  avg_score_pct: number;
  last_active: string | null;
}

export interface ClassMetricsResponse {
  school_id: string;
  grade: number | null;
  subject: string | null;
  students: ClassStudentRow[];
}

export async function getClassMetrics(
  schoolId: string,
  grade?: number,
  subject?: string,
): Promise<ClassMetricsResponse> {
  const res = await schoolApi.get<ClassMetricsResponse>(
    `/reports/school/${schoolId}/roster`,
    { params: { grade, subject } },
  );
  return res.data;
}

// ── Feedback Report ───────────────────────────────────────────────────────────

export interface FeedbackReportItem {
  feedback_id: string;
  category: string;
  rating: number | null;
  message: string;
  submitted_at: string;
  reviewed: boolean;
}

export interface FeedbackByUnit {
  unit_id: string;
  unit_name: string | null;
  feedback_count: number;
  category_breakdown: Record<string, number>;
  trending: boolean;
  feedback_items: FeedbackReportItem[];
}

export interface FeedbackReport {
  school_id: string;
  total_feedback_count: number;
  unreviewed_count: number;
  avg_rating_overall: number | null;
  by_unit: FeedbackByUnit[];
}

export async function getFeedbackReport(schoolId: string): Promise<FeedbackReport> {
  const res = await schoolApi.get<FeedbackReport>(`/reports/school/${schoolId}/feedback`);
  return res.data;
}

// ── Export ────────────────────────────────────────────────────────────────────

export interface ExportResponse {
  export_id: string;
  download_url: string;
  status: "queued" | "ready";
}

export async function triggerExport(
  schoolId: string,
  reportType: ReportType,
  filters: Record<string, unknown> = {},
): Promise<ExportResponse> {
  const res = await schoolApi.post<ExportResponse>(`/reports/school/${schoolId}/export`, {
    report_type: reportType,
    filters,
  });
  return res.data;
}

// ── Alerts ────────────────────────────────────────────────────────────────────

export interface AlertItem {
  alert_id: string;
  alert_type: string;
  school_id: string;
  details: Record<string, unknown>;
  triggered_at: string;
  acknowledged: boolean;
}

export interface AlertListResponse {
  alerts: AlertItem[];
}

export async function getAlerts(schoolId: string): Promise<AlertListResponse> {
  const res = await schoolApi.get<AlertListResponse>(
    `/reports/school/${schoolId}/alerts`,
  );
  return res.data;
}

// ── Alert Settings ────────────────────────────────────────────────────────────

export interface AlertSettings {
  pass_rate_threshold: number;
  feedback_count_threshold: number;
  inactive_days_threshold: number;
  score_drop_threshold: number;
  new_feedback_immediate: boolean;
}

export async function updateAlertSettings(
  schoolId: string,
  settings: AlertSettings,
): Promise<void> {
  await schoolApi.put(`/reports/school/${schoolId}/alerts/settings`, settings);
}

// ── Digest Subscription ───────────────────────────────────────────────────────

export interface DigestSubscription {
  subscription_id: string;
  school_id: string;
  email: string;
  timezone: string;
  enabled: boolean;
}

export async function subscribeDigest(
  schoolId: string,
  email: string,
  timezone: string,
  enabled: boolean,
): Promise<DigestSubscription> {
  const res = await schoolApi.post<DigestSubscription>(
    `/reports/school/${schoolId}/digest/subscribe`,
    { email, timezone, enabled },
  );
  return res.data;
}
