import adminApi from "./admin-client";
import api from "./client"; // unauthenticated for /health

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AdminLoginResponse {
  token: string;
  admin_id: string;
}

export async function adminLogin(
  email: string,
  password: string,
): Promise<AdminLoginResponse> {
  const res = await adminApi.post<AdminLoginResponse>("/admin/auth/login", {
    email,
    password,
  });
  return res.data;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface SubscriptionAnalytics {
  active_monthly: number;
  active_annual: number;
  total_active: number;
  mrr_usd: number;
  new_this_month: number;
  cancelled_this_month: number;
  churn_rate: number;
}

export async function getSubscriptionAnalytics(): Promise<SubscriptionAnalytics> {
  const res = await adminApi.get<SubscriptionAnalytics>("/admin/analytics/subscriptions");
  return res.data;
}

export interface StruggleUnit {
  unit_id: string;
  unit_title: string;
  grade: number;
  subject: string;
  avg_score: number;
  attempt_count: number;
  fail_rate: number;
}

export interface StruggleReport {
  units: StruggleUnit[];
  generated_at: string;
}

export async function getStruggleReport(): Promise<StruggleReport> {
  const res = await adminApi.get<StruggleReport>("/admin/analytics/struggle");
  return res.data;
}

// ── Pipeline ──────────────────────────────────────────────────────────────────

export interface AdminPipelineJob {
  job_id: string;
  curriculum_id: string;
  grade: number | null;
  langs: string;
  force: boolean;
  status: "queued" | "running" | "completed" | "failed" | "done";
  progress_pct: number;
  built: number;
  failed: number;
  total: number;
  triggered_by_email: string | null;
  triggered_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  payload_bytes: number | null;
}

export interface PipelineJobsResponse {
  jobs: AdminPipelineJob[];
}

export async function getPipelineJobs(): Promise<PipelineJobsResponse> {
  const res = await adminApi.get<PipelineJobsResponse>("/admin/pipeline/jobs");
  return res.data;
}

export interface AdminPipelineTriggerResponse {
  job_id: string;
  status: string;
  curriculum_id: string;
}

export interface UploadGradeJsonResponse {
  curriculum_id: string;
  grade: number;
  unit_count: number;
  subject_count: number;
}

export async function triggerAdminPipeline(
  grade: number,
  langs: string,
  force: boolean,
  year = 2026,
): Promise<AdminPipelineTriggerResponse> {
  const res = await adminApi.post<AdminPipelineTriggerResponse>(
    "/admin/pipeline/trigger",
    {
      grade,
      langs,
      force,
      year,
    },
  );
  return res.data;
}

export async function uploadGradeJson(
  file: File,
  year = 2026,
): Promise<UploadGradeJsonResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await adminApi.post<UploadGradeJsonResponse>(
    `/admin/pipeline/upload-grade?year=${year}`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return res.data;
}

export async function getAdminPipelineJobStatus(
  jobId: string,
): Promise<AdminPipelineJob> {
  const res = await adminApi.get<AdminPipelineJob>(`/admin/pipeline/${jobId}/status`);
  return res.data;
}

// ── Content Review ─────────────────────────────────────────────────────────────

export interface AdminUser {
  admin_user_id: string;
  email: string;
  role: string;
}

export interface ReviewQueueItem {
  version_id: string;
  curriculum_id: string;
  subject: string;
  subject_name: string | null;
  version_number: number;
  status: "pending" | "approved" | "rejected" | "published" | "blocked";
  alex_warnings_count: number;
  generated_at: string;
  published_at: string | null;
  has_content: boolean;
  assigned_to_admin_id: string | null;
  assigned_to_email: string | null;
  assigned_at: string | null;
}

export interface ReviewQueueResponse {
  items: ReviewQueueItem[];
  total: number;
}

export async function getReviewQueue(
  status?: string,
  curriculumId?: string,
  subject?: string,
  assignedTo?: string,
): Promise<ReviewQueueResponse> {
  const params: Record<string, string> = {};
  if (status) params.status = status;
  if (curriculumId) params.curriculum_id = curriculumId;
  if (subject) params.subject = subject;
  if (assignedTo) params.assigned_to = assignedTo;
  const res = await adminApi.get<ReviewQueueResponse>("/admin/content/review/queue", {
    params,
  });
  return res.data;
}

export interface ReviewUnitItem {
  unit_id: string;
  title: string;
  sort_order: number;
}

export interface ReviewHistoryItem {
  review_id: string;
  action: string;
  notes: string | null;
  reviewed_at: string;
  reviewer_email: string | null;
}

export interface ReviewAnnotationItem {
  annotation_id: string;
  unit_id: string;
  content_type: string;
  annotation_text: string;
  created_at: string;
  reviewer_email: string | null;
}

export interface ReviewItemDetail extends ReviewQueueItem {
  units: ReviewUnitItem[];
  review_history: ReviewHistoryItem[];
  annotations: ReviewAnnotationItem[];
}

export async function getReviewItem(versionId: string): Promise<ReviewItemDetail> {
  const res = await adminApi.get<ReviewItemDetail>(`/admin/content/review/${versionId}`);
  return res.data;
}

export async function addAnnotation(
  versionId: string,
  unitId: string,
  contentType: string,
  annotationText: string,
  markedText?: string,
): Promise<ReviewAnnotationItem> {
  const res = await adminApi.post<ReviewAnnotationItem>(
    `/admin/content/review/${versionId}/annotate`,
    {
      unit_id: unitId,
      content_type: contentType,
      annotation_text: annotationText,
      marked_text: markedText ?? null,
    },
  );
  return res.data;
}

export async function deleteAnnotation(annotationId: string): Promise<void> {
  await adminApi.delete(`/admin/content/review/annotations/${annotationId}`);
}

export async function approveReview(versionId: string, notes?: string): Promise<void> {
  await adminApi.post(`/admin/content/review/${versionId}/approve`, { notes });
}

export interface BatchApproveResult {
  approved_count: number;
  version_ids: string[];
}

export async function batchApproveGrade(
  curriculumId: string,
  notes?: string,
): Promise<BatchApproveResult> {
  const res = await adminApi.post<BatchApproveResult>(
    "/admin/content/review/batch-approve",
    {
      curriculum_id: curriculumId,
      notes,
    },
  );
  return res.data;
}

export async function getAdminUsers(): Promise<AdminUser[]> {
  const res = await adminApi.get<{ users: AdminUser[] }>("/admin/users");
  return res.data.users;
}

export interface AssignResult {
  version_id: string;
  assigned_to_admin_id: string | null;
  assigned_to_email: string | null;
  assigned_at: string | null;
}

export async function assignReview(
  versionId: string,
  adminId: string | null,
): Promise<AssignResult> {
  const res = await adminApi.post<AssignResult>(
    `/admin/content/review/${versionId}/assign`,
    { admin_id: adminId },
  );
  return res.data;
}

export async function rejectReview(versionId: string, notes?: string): Promise<void> {
  await adminApi.post(`/admin/content/review/${versionId}/reject`, {
    notes,
    regenerate: false,
  });
}

export async function publishReview(versionId: string): Promise<void> {
  await adminApi.post(`/admin/content/versions/${versionId}/publish`);
}

export async function rollbackReview(versionId: string): Promise<void> {
  await adminApi.post(`/admin/content/versions/${versionId}/rollback`);
}

export async function blockContent(
  curriculumId: string,
  unitId: string,
  contentType: string,
  reason?: string,
): Promise<void> {
  await adminApi.post(`/admin/content/block`, {
    curriculum_id: curriculumId,
    unit_id: unitId,
    content_type: contentType,
    reason,
  });
}

export async function blockVersionContent(
  versionId: string,
  unitId: string,
  contentType: string,
  reason?: string,
): Promise<void> {
  await adminApi.post(`/admin/content/review/${versionId}/block`, {
    unit_id: unitId,
    content_type: contentType,
    reason,
  });
}

// ── Feedback ──────────────────────────────────────────────────────────────────

export interface AdminFeedbackItem {
  feedback_id: string;
  student_id: string;
  unit_id: string;
  unit_title: string;
  rating: number;
  comment: string | null;
  submitted_at: string;
  resolved: boolean;
}

export interface FeedbackListResponse {
  items: AdminFeedbackItem[];
  total: number;
  page: number;
  page_size: number;
}

export async function getFeedbackList(
  page = 1,
  pageSize = 20,
  resolved?: boolean,
): Promise<FeedbackListResponse> {
  const params: Record<string, unknown> = { page, page_size: pageSize };
  if (resolved !== undefined) params.resolved = resolved;
  const res = await adminApi.get<FeedbackListResponse>("/admin/feedback", {
    params,
  });
  return res.data;
}

export async function resolveFeedback(feedbackId: string): Promise<void> {
  await adminApi.post(`/admin/feedback/${feedbackId}/resolve`);
}

// ── System Health ──────────────────────────────────────────────────────────────

export type ServiceStatus = "ok" | "error";

export interface SystemHealth {
  db_status: ServiceStatus;
  redis_status: ServiceStatus;
  db_pool_size?: number;
  db_pool_available?: number;
  redis_connected_clients?: number;
  checked_at: string;
}

export async function getSystemHealth(): Promise<SystemHealth> {
  // /health is unauthenticated — use the base client
  const res = await api.get<SystemHealth>("/health");
  return res.data;
}

// ── Audit Log ─────────────────────────────────────────────────────────────────

export interface AuditEntry {
  audit_id: string;
  actor_id: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string;
  detail: Record<string, unknown>;
  created_at: string;
}

export interface AuditLogResponse {
  entries: AuditEntry[];
  total: number;
  page: number;
  page_size: number;
}

export async function getAuditLog(
  page = 1,
  pageSize = 50,
  action?: string,
): Promise<AuditLogResponse> {
  const params: Record<string, unknown> = { page, page_size: pageSize };
  if (action) params.action = action;
  const res = await adminApi.get<AuditLogResponse>("/admin/audit", { params });
  return res.data;
}

// ── Demo Accounts ─────────────────────────────────────────────────────────────

export interface DemoAccountItem {
  request_id: string;
  email: string;
  request_status: "pending" | "verified" | "expired" | "revoked";
  account_id: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  extended_at: string | null;
  verification_pending: boolean;
}

export interface DemoAccountListResponse {
  items: DemoAccountItem[];
  total: number;
  page: number;
  page_size: number;
}

export async function getDemoAccounts(
  page = 1,
  pageSize = 20,
  status?: string,
  email?: string,
): Promise<DemoAccountListResponse> {
  const params: Record<string, unknown> = { page, page_size: pageSize };
  if (status) params.status = status;
  if (email) params.email = email;
  const res = await adminApi.get<DemoAccountListResponse>("/admin/demo-accounts", {
    params,
  });
  return res.data;
}

export async function extendDemoAccount(
  accountId: string,
  hours: number,
): Promise<{ account_id: string; expires_at: string; extended_at: string }> {
  const res = await adminApi.post(`/admin/demo-accounts/${accountId}/extend`, { hours });
  return res.data;
}

export async function revokeDemoAccount(
  accountId: string,
): Promise<{ email: string; message: string }> {
  const res = await adminApi.post(`/admin/demo-accounts/${accountId}/revoke`);
  return res.data;
}

export async function adminResendDemoVerification(
  requestId: string,
): Promise<{ email: string }> {
  const res = await adminApi.post(`/admin/demo-requests/${requestId}/resend`);
  return res.data;
}

// ── Demo Teacher Accounts ─────────────────────────────────────────────────────

export interface DemoTeacherAccountItem {
  request_id: string;
  email: string;
  request_status: "pending" | "verified" | "expired" | "revoked";
  account_id: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  extended_at: string | null;
  verification_pending: boolean;
}

export interface DemoTeacherAccountListResponse {
  items: DemoTeacherAccountItem[];
  total: number;
  page: number;
  page_size: number;
}

export async function getDemoTeacherAccounts(
  page = 1,
  pageSize = 20,
  status?: string,
  email?: string,
): Promise<DemoTeacherAccountListResponse> {
  const params: Record<string, unknown> = { page, page_size: pageSize };
  if (status) params.status = status;
  if (email) params.email = email;
  const res = await adminApi.get<DemoTeacherAccountListResponse>(
    "/admin/demo-teacher-accounts",
    { params },
  );
  return res.data;
}

export async function extendDemoTeacherAccount(
  accountId: string,
  hours: number,
): Promise<{ account_id: string; expires_at: string; extended_at: string }> {
  const res = await adminApi.post(`/admin/demo-teacher-accounts/${accountId}/extend`, {
    hours,
  });
  return res.data;
}

export async function revokeDemoTeacherAccount(
  accountId: string,
): Promise<{ email: string; message: string }> {
  const res = await adminApi.post(`/admin/demo-teacher-accounts/${accountId}/revoke`);
  return res.data;
}

export async function adminResendDemoTeacherVerification(
  requestId: string,
): Promise<{ email: string }> {
  const res = await adminApi.post(`/admin/demo-teacher-requests/${requestId}/resend`);
  return res.data;
}

// ── CI / Build Reports ────────────────────────────────────────────────────────

export interface CiJob {
  name: string;
  status: string;
  conclusion: string | null;
  duration_s: number | null;
  html_url: string;
}

export interface CiRun {
  run_id: number;
  head_branch: string;
  head_sha: string;
  conclusion: string | null; // "success" | "failure" | "cancelled" | "timed_out" | null
  created_at: string;
  duration_s: number | null;
  html_url: string;
  jobs: CiJob[]; // populated only for runs[0] (latest)
}

export interface CiReportsResponse {
  github_configured: boolean;
  repo: string;
  runs: CiRun[];
  cached_at: string;
}

export async function getCiReports(): Promise<CiReportsResponse> {
  const res = await adminApi.get<CiReportsResponse>("/admin/ci/reports");
  return res.data;
}

// ── Unit content viewer ────────────────────────────────────────────────────────

export interface UnitContentMeta {
  unit_id: string;
  title: string;
  curriculum_id: string;
  lang: string;
  available_types: string[];
  alex_warnings_count: number;
}

export async function getUnitContentMeta(
  versionId: string,
  unitId: string,
  lang = "en",
): Promise<UnitContentMeta> {
  const res = await adminApi.get<UnitContentMeta>(
    `/admin/content/review/${versionId}/unit/${unitId}`,
    { params: { lang } },
  );
  return res.data;
}

export interface UnitContentFile {
  unit_id: string;
  curriculum_id: string;
  content_type: string;
  lang: string;
  data: Record<string, unknown>;
}

export async function getUnitContentFile(
  versionId: string,
  unitId: string,
  contentType: string,
  lang = "en",
): Promise<UnitContentFile> {
  const res = await adminApi.get<UnitContentFile>(
    `/admin/content/review/${versionId}/unit/${unitId}/${contentType}`,
    { params: { lang } },
  );
  return res.data;
}

// ── Admin school management ───────────────────────────────────────────────────

export interface AdminSchoolListItem {
  school_id: string;
  name: string;
  contact_email: string;
  country: string;
  status: string;
  created_at: string;
  plan: string;
  subscription_status: string | null;
  seats_used_students: number;
  seats_used_teachers: number;
  has_override: boolean;
}

export interface AdminSchoolListResponse {
  schools: AdminSchoolListItem[];
  total: number;
  page: number;
  page_size: number;
}

export async function listAdminSchools(
  page = 1,
  pageSize = 20,
  search?: string,
): Promise<AdminSchoolListResponse> {
  const params: Record<string, unknown> = { page, page_size: pageSize };
  if (search) params.search = search;
  const res = await adminApi.get<AdminSchoolListResponse>("/admin/schools", { params });
  return res.data;
}

export interface AdminSchoolOverride {
  max_students: number | null;
  max_teachers: number | null;
  pipeline_quota: number | null;
  override_reason: string;
  set_by_admin_id: string;
  set_at: string;
}

export interface AdminSchoolLimits {
  plan: string;
  max_students: number;
  max_teachers: number;
  pipeline_quota_monthly: number;
  pipeline_runs_this_month: number;
  pipeline_resets_at: string;
  seats_used_students: number;
  seats_used_teachers: number;
  has_override: boolean;
  override: AdminSchoolOverride | null;
}

export async function getAdminSchoolLimits(schoolId: string): Promise<AdminSchoolLimits> {
  const res = await adminApi.get<AdminSchoolLimits>(`/admin/schools/${schoolId}/limits`);
  return res.data;
}

export interface SetOverridePayload {
  max_students?: number | null;
  max_teachers?: number | null;
  pipeline_quota?: number | null;
  override_reason: string;
}

export async function setAdminSchoolLimits(
  schoolId: string,
  payload: SetOverridePayload,
): Promise<{ status: string; school_id: string }> {
  const res = await adminApi.put(`/admin/schools/${schoolId}/limits`, payload);
  return res.data;
}

export async function clearAdminSchoolLimits(
  schoolId: string,
): Promise<{ status: string; school_id: string }> {
  const res = await adminApi.delete(`/admin/schools/${schoolId}/limits`);
  return res.data;
}
