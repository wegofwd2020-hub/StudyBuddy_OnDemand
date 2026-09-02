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

/**
 * What population a report's figures cover. Reported by the server from the
 * same filter that scoped the query, so a caption can never describe a
 * population the numbers do not (#640).
 *
 * `kind: "grades"` with an EMPTY list is a real state — a teacher with no grade
 * assignments legitimately sees nothing — and must not be read as "school".
 */
export interface ReportScope {
  kind: "school" | "grades";
  grades: number[];
}

export interface OverviewReport {
  scope: ReportScope;
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
  /** Feedback naming no unit — cannot appear per-unit, so it is reported here
   *  and shown in the export, letting the dashboard tile be reconciled against
   *  the sum of the per-unit counts instead of merely compared to it. */
  general_feedback_count?: number;
  /** Grades this caller may filter to — NOT the grades present in `units`.
   *  Populating a picker from its own filtered result collapses it to the one
   *  option selected, so the server reports the permission scope here while
   *  everything else in the response reports the selection. */
  available_grades?: number[];
  /** Echoed by the server. Render the control from this rather than from local
   *  state, so a rejected or in-flight request cannot leave the chip claiming a
   *  grade the table below it does not show. */
  selected_grade?: number | null;
  units: CurriculumHealthUnit[];
}

export async function getCurriculumHealth(
  schoolId: string,
  grade?: number | null,
): Promise<CurriculumHealthReport> {
  const res = await schoolApi.get<CurriculumHealthReport>(
    `/reports/school/${schoolId}/curriculum-health`,
    // Omitted entirely when unset — the endpoint's default is all grades, and
    // sending `grade=null` would make that an explicit (and rejected) choice.
    grade == null ? undefined : { params: { grade } },
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
  /** Total seconds on this unit's content — sums to `total_time_spent_s`. */
  total_duration_s: number;
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
  unit_id: string | null;
  unit_name: string | null;
  category: string;
  rating: number | null;
  /** Null for a thumbs vote, which carries `helpful` instead (migration 0062). */
  message: string | null;
  helpful: boolean | null;
  content_type: string | null;
  submitted_at: string;
  reviewed: boolean;
}

export interface FeedbackPagination {
  page: number;
  page_size: number;
  /** Rows matching the CURRENT filters — the header counts are unfiltered. */
  total: number;
}

export interface FeedbackReport {
  school_id: string;
  total_feedback_count: number;
  unreviewed_count: number;
  avg_rating_overall: number | null;
  items: FeedbackReportItem[];
  pagination: FeedbackPagination;
}

export interface FeedbackReportParams {
  page?: number;
  pageSize?: number;
  unitId?: string;
  category?: string;
  reviewed?: boolean;
}

export async function getFeedbackReport(
  schoolId: string,
  params: FeedbackReportParams = {},
): Promise<FeedbackReport> {
  const query: Record<string, unknown> = {
    page: params.page ?? 1,
    page_size: params.pageSize ?? 25,
  };
  if (params.unitId) query.unit_id = params.unitId;
  if (params.category) query.category = params.category;
  if (params.reviewed !== undefined) query.reviewed = params.reviewed;

  const res = await schoolApi.get<FeedbackReport>(
    `/reports/school/${schoolId}/feedback`,
    {
      params: query,
    },
  );
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
  /**
   * Grade the alert's unit belongs to (#647). The list is now scoped to the
   * caller's grades; showing the grade is what makes that visible — a scoped
   * list is otherwise indistinguishable from an unscoped one.
   *
   * null only reaches a school_admin: an alert whose unit cannot be resolved
   * to a grade is withheld from grade-restricted teachers.
   */
  grade: number | null;
  /**
   * The alert's unit by name, e.g. "Weather and Climate" (reported 2026-08-31).
   * The inbox previously showed only `unit_id: G5-TECH-004`, a code that appears
   * nowhere on the Subjects page, so the alert named something the teacher could
   * not go and look at.
   *
   * null when the unit is not in curriculum_units — the page falls back to the
   * raw id rather than showing nothing.
   *
   * NOTE: this interface is hand-written and does NOT derive from
   * lib/api/types.gen.ts, so regenerating the contract does not update it.
   * Adding a field to the API means editing both. That split is what broke the
   * demo build for this field: the generated type had it, this one did not, and
   * the page imports THIS one.
   */
  unit_title?: string | null;
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

/** Load the school's saved alert thresholds (or server defaults if never saved).
 *  The threshold fields are read back for the settings form (#526). */
export async function getAlertSettings(schoolId: string): Promise<AlertSettings> {
  const res = await schoolApi.get<
    AlertSettings & { school_id: string; updated_at: string | null }
  >(`/reports/school/${schoolId}/alerts/settings`);
  const {
    pass_rate_threshold,
    feedback_count_threshold,
    inactive_days_threshold,
    score_drop_threshold,
    new_feedback_immediate,
  } = res.data;
  return {
    pass_rate_threshold,
    feedback_count_threshold,
    inactive_days_threshold,
    score_drop_threshold,
    new_feedback_immediate,
  };
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

// ── At-Risk Student Action Queue (#79) ───────────────────────────────────────

export interface AtRiskReason {
  inactive: boolean;
  low_pass_rate: boolean;
}

export interface AtRiskStudent {
  student_id: string;
  student_name: string;
  grade: number;
  last_active: string | null;
  inactive_days: number | null;
  pass_rate_pct: number | null;
  units_completed: number;
  total_units: number;
  risk_reasons: AtRiskReason;
  is_seen: boolean;
  seen_at: string | null;
}

export interface AtRiskListResponse {
  school_id: string;
  inactive_days_threshold: number;
  pass_rate_threshold: number;
  students: AtRiskStudent[];
  total: number;
}

export interface MarkSeenResponse {
  school_id: string;
  student_id: string;
  seen: boolean;
  seen_at: string | null;
}

export interface SendReminderResponse {
  school_id: string;
  student_id: string;
  queued: boolean;
}

export async function getAtRiskStudents(schoolId: string): Promise<AtRiskListResponse> {
  const res = await schoolApi.get<AtRiskListResponse>(
    `/reports/school/${schoolId}/at-risk`,
  );
  return res.data;
}

export async function markAtRiskSeen(
  schoolId: string,
  studentId: string,
  seen: boolean,
): Promise<MarkSeenResponse> {
  const res = await schoolApi.post<MarkSeenResponse>(
    `/reports/school/${schoolId}/at-risk/${studentId}/seen`,
    null,
    { params: { seen } },
  );
  return res.data;
}

export async function sendAtRiskReminder(
  schoolId: string,
  studentId: string,
): Promise<SendReminderResponse> {
  const res = await schoolApi.post<SendReminderResponse>(
    `/reports/school/${schoolId}/at-risk/${studentId}/reminder`,
  );
  return res.data;
}

/**
 * Which grades the caller may see (#647 follow-up).
 *
 * Scope is a property of the caller, not of any one report, so it is fetched
 * once and reused. Pages use it to explain an EMPTY list rather than assert
 * something false about the school — grade-scoping alerts and classrooms made
 * "No active alerts — all clear." and "No active classrooms yet." into false
 * reassurance for a teacher with no assignments.
 */
export async function getMyGradeScope(schoolId: string): Promise<ReportScope> {
  const res = await schoolApi.get<ReportScope>(`/schools/${schoolId}/my-grade-scope`);
  return res.data;
}
