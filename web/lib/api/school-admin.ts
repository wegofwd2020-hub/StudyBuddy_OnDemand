import schoolApi from "./school-client";

// ── School profile ────────────────────────────────────────────────────────────

export interface SchoolProfile {
  school_id: string;
  name: string;
  contact_email: string;
  country: string;
  enrolment_code: string | null;
  status: string;
  created_at: string;
}

export async function getSchoolProfile(schoolId: string): Promise<SchoolProfile> {
  const res = await schoolApi.get<SchoolProfile>(`/schools/${schoolId}`);
  return res.data;
}

// ── Roster ────────────────────────────────────────────────────────────────────

export interface RosterItem {
  student_email: string;
  student_id: string | null;
  status: string;
  added_at: string;
}

export interface RosterResponse {
  roster: RosterItem[];
}

export async function getRoster(schoolId: string): Promise<RosterResponse> {
  const res = await schoolApi.get<RosterResponse>(`/schools/${schoolId}/enrolment`);
  return res.data;
}

export interface EnrolmentUploadResponse {
  enrolled: number;
  already_enrolled: number;
}

export async function uploadRoster(
  schoolId: string,
  studentEmails: string[],
): Promise<EnrolmentUploadResponse> {
  const res = await schoolApi.post<EnrolmentUploadResponse>(
    `/schools/${schoolId}/enrolment`,
    { student_emails: studentEmails },
  );
  return res.data;
}

// ── Teachers ──────────────────────────────────────────────────────────────────

export interface TeacherInviteResponse {
  teacher_id: string;
  email: string;
  role: string;
}

export async function inviteTeacher(
  schoolId: string,
  name: string,
  email: string,
): Promise<TeacherInviteResponse> {
  const res = await schoolApi.post<TeacherInviteResponse>(
    `/schools/${schoolId}/teachers/invite`,
    { name, email },
  );
  return res.data;
}

// ── School pipeline — JSON upload, trigger, list, detail ─────────────────────

export interface CurriculumUploadResponse {
  curriculum_id: string;
  grade: number;
  year: number;
  unit_count: number;
  subject_count: number;
  subjects: string[];
}

export async function uploadCurriculumJSON(
  schoolId: string,
  file: File,
  year: number,
): Promise<CurriculumUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await schoolApi.post<CurriculumUploadResponse>(
    `/schools/${schoolId}/curriculum/upload?year=${year}`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return res.data;
}

export interface TriggerPipelineResponse {
  job_id: string;
  status: string;
  curriculum_id: string;
}

export async function triggerSchoolPipeline(
  schoolId: string,
  body: { langs: string; force: boolean; year: number },
): Promise<TriggerPipelineResponse> {
  const res = await schoolApi.post<TriggerPipelineResponse>(
    `/schools/${schoolId}/pipeline/trigger`,
    body,
  );
  return res.data;
}

export interface PipelineJob {
  job_id: string;
  curriculum_id: string;
  grade: number;
  langs: string;
  status: string;
  built: number | null;
  failed: number | null;
  total: number | null;
  triggered_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  payload_bytes: number | null;
  triggered_by_email: string | null;
  progress_pct?: number;
}

export interface PipelineJobListResponse {
  jobs: PipelineJob[];
  total: number;
  page: number;
  page_size: number;
}

export async function listSchoolPipelineJobs(
  schoolId: string,
  params: { page?: number; page_size?: number; status?: string } = {},
): Promise<PipelineJobListResponse> {
  const res = await schoolApi.get<PipelineJobListResponse>(
    `/schools/${schoolId}/pipeline`,
    { params },
  );
  return res.data;
}

export async function getSchoolPipelineJob(
  schoolId: string,
  jobId: string,
): Promise<PipelineJob> {
  const res = await schoolApi.get<PipelineJob>(
    `/schools/${schoolId}/pipeline/${jobId}`,
  );
  return res.data;
}

// ── School limits (quota indicator) ──────────────────────────────────────────

export interface SchoolLimits {
  plan: string;
  max_students: number;
  max_teachers: number;
  pipeline_quota_monthly: number;
  pipeline_runs_this_month: number;
  pipeline_resets_at: string;
  seats_used_students: number;
  seats_used_teachers: number;
  has_override: boolean;
}

export async function getSchoolLimits(schoolId: string): Promise<SchoolLimits> {
  const res = await schoolApi.get<SchoolLimits>(`/schools/${schoolId}/limits`);
  return res.data;
}

// ── School subscription ───────────────────────────────────────────────────────

export interface SchoolSubscription {
  plan: string;
  status: string | null;
  max_students: number;
  max_teachers: number;
  seats_used_students: number;
  seats_used_teachers: number;
  current_period_end: string | null;
}

export async function getSchoolSubscription(schoolId: string): Promise<SchoolSubscription> {
  const res = await schoolApi.get<SchoolSubscription>(`/schools/${schoolId}/subscription`);
  return res.data;
}

export async function createSchoolCheckout(
  schoolId: string,
  plan: string,
  successUrl: string,
  cancelUrl: string,
): Promise<{ checkout_url: string }> {
  const res = await schoolApi.post<{ checkout_url: string }>(
    `/schools/${schoolId}/subscription/checkout`,
    { plan, success_url: successUrl, cancel_url: cancelUrl },
  );
  return res.data;
}

export async function cancelSchoolSubscription(
  schoolId: string,
): Promise<{ status: string; current_period_end: string | null }> {
  const res = await schoolApi.delete<{ status: string; current_period_end: string | null }>(
    `/schools/${schoolId}/subscription`,
  );
  return res.data;
}
