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
  status: "queued" | "running" | "done" | "failed";
  progress_pct: number;
  built: number;
  failed: number;
  total: number;
  triggered_by: string;
  triggered_at: string;
}

export interface PipelineJobsResponse {
  jobs: AdminPipelineJob[];
}

export async function getPipelineJobs(): Promise<PipelineJobsResponse> {
  const res = await adminApi.get<PipelineJobsResponse>("/admin/pipeline/status");
  return res.data;
}

export interface AdminPipelineTriggerResponse {
  job_id: string;
  status: string;
}

export async function triggerAdminPipeline(
  grade: number,
  lang: string,
  force: boolean,
): Promise<AdminPipelineTriggerResponse> {
  const res = await adminApi.post<AdminPipelineTriggerResponse>(
    "/admin/pipeline/trigger",
    { grade, lang, force },
  );
  return res.data;
}

// ── Content Review ─────────────────────────────────────────────────────────────

export interface ReviewQueueItem {
  version_id: string;
  unit_id: string;
  unit_title: string;
  grade: number;
  subject: string;
  lang: string;
  content_version: number;
  status: "pending" | "approved" | "rejected" | "published" | "blocked";
  submitted_at: string;
  reviewer_id: string | null;
}

export interface ReviewQueueResponse {
  items: ReviewQueueItem[];
  total: number;
}

export async function getReviewQueue(status?: string): Promise<ReviewQueueResponse> {
  const params = status ? { status } : {};
  const res = await adminApi.get<ReviewQueueResponse>("/admin/content-review/queue", {
    params,
  });
  return res.data;
}

export interface ReviewItemDetail extends ReviewQueueItem {
  lesson_preview: string;
  quiz_count: number;
  alexjs_score: number | null;
  annotations: { reviewer_id: string; note: string; created_at: string }[];
}

export async function getReviewItem(versionId: string): Promise<ReviewItemDetail> {
  const res = await adminApi.get<ReviewItemDetail>(`/admin/content-review/${versionId}`);
  return res.data;
}

export async function approveReview(versionId: string): Promise<void> {
  await adminApi.post(`/admin/content-review/${versionId}/approve`);
}

export async function rejectReview(versionId: string, reason: string): Promise<void> {
  await adminApi.post(`/admin/content-review/${versionId}/reject`, { reason });
}

export async function publishReview(versionId: string): Promise<void> {
  await adminApi.post(`/admin/content-review/${versionId}/publish`);
}

export async function rollbackReview(versionId: string): Promise<void> {
  await adminApi.post(`/admin/content-review/${versionId}/rollback`);
}

export async function blockReview(versionId: string, reason: string): Promise<void> {
  await adminApi.post(`/admin/content-review/${versionId}/block`, { reason });
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
