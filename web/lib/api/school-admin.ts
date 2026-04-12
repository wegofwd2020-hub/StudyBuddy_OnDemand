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
  // Curriculum build allowance (Option A — absorbed into plan)
  builds_included: number;        // -1 = unlimited (Enterprise)
  builds_used: number;
  builds_remaining: number;       // -1 = unlimited
  builds_period_end: string | null;
  // Rollover credit balance (Option C, #107 — never expires)
  builds_credits_balance: number;
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

// ── Extra build / credit bundle checkouts (#106 / #107) ──────────────────────

export async function createExtraBuildCheckout(
  schoolId: string,
  successUrl: string,
  cancelUrl: string,
): Promise<{ checkout_url: string }> {
  const res = await schoolApi.post<{ checkout_url: string }>(
    `/schools/${schoolId}/pipeline/extra-build-checkout`,
    { success_url: successUrl, cancel_url: cancelUrl },
  );
  return res.data;
}

export async function createCreditsBundleCheckout(
  schoolId: string,
  bundleSize: 3 | 10 | 25,
  successUrl: string,
  cancelUrl: string,
): Promise<{ checkout_url: string }> {
  const res = await schoolApi.post<{ checkout_url: string }>(
    `/schools/${schoolId}/pipeline/credits-checkout`,
    { bundle_size: bundleSize, success_url: successUrl, cancel_url: cancelUrl },
  );
  return res.data;
}

// ── Phase A provisioning ──────────────────────────────────────────────────────

export interface ProvisionTeacherRequest {
  name: string;
  email: string;
  subject_specialisation?: string;
}

export interface ProvisionedTeacher {
  teacher_id: string;
  school_id: string;
  name: string;
  email: string;
  role: string;
}

/**
 * Create a teacher with a system-generated default password.
 * The backend emails credentials to the teacher. Sets first_login=true.
 * Requires school_admin role.
 */
export async function provisionTeacher(
  schoolId: string,
  body: ProvisionTeacherRequest,
): Promise<ProvisionedTeacher> {
  const res = await schoolApi.post<ProvisionedTeacher>(
    `/schools/${schoolId}/teachers`,
    body,
  );
  return res.data;
}

export interface ProvisionStudentRequest {
  name: string;
  email: string;
  /** 1–12 */
  grade: number;
}

export interface ProvisionedStudent {
  student_id: string;
  school_id: string;
  name: string;
  email: string;
  grade: number;
}

/**
 * Create a student with a system-generated default password.
 * The backend emails credentials to the student. Sets first_login=true.
 * Requires school_admin role.
 */
export async function provisionStudent(
  schoolId: string,
  body: ProvisionStudentRequest,
): Promise<ProvisionedStudent> {
  const res = await schoolApi.post<ProvisionedStudent>(
    `/schools/${schoolId}/students`,
    body,
  );
  return res.data;
}

/**
 * Admin-initiated password reset for a teacher.
 * Generates a new default password, emails it, and sets first_login=true.
 */
export async function resetTeacherPassword(
  schoolId: string,
  teacherId: string,
): Promise<{ detail: string }> {
  const res = await schoolApi.post<{ detail: string }>(
    `/schools/${schoolId}/teachers/${teacherId}/reset-password`,
  );
  return res.data;
}

/**
 * Admin-initiated password reset for a student.
 * Generates a new default password, emails it, and sets first_login=true.
 */
export async function resetStudentPassword(
  schoolId: string,
  studentId: string,
): Promise<{ detail: string }> {
  const res = await schoolApi.post<{ detail: string }>(
    `/schools/${schoolId}/students/${studentId}/reset-password`,
  );
  return res.data;
}

export interface PromoteTeacherResponse {
  teacher_id: string;
  name: string;
  email: string;
  role: string;
}

/**
 * Promote a teacher to school_admin.
 * Multiple school_admins per school are allowed.
 */
export async function promoteTeacher(
  schoolId: string,
  teacherId: string,
): Promise<PromoteTeacherResponse> {
  const res = await schoolApi.post<PromoteTeacherResponse>(
    `/schools/${schoolId}/teachers/${teacherId}/promote`,
  );
  return res.data;
}

// ── Teacher roster + grade assignments ────────────────────────────────────────

export interface TeacherRosterItem {
  teacher_id: string;
  name: string;
  email: string;
  role: string;
  account_status: string;
  assigned_grades: number[];
}

export async function listTeachers(schoolId: string): Promise<TeacherRosterItem[]> {
  const res = await schoolApi.get<{ teachers: TeacherRosterItem[] }>(
    `/schools/${schoolId}/teachers`,
  );
  return res.data.teachers;
}

export async function assignTeacherGrades(
  schoolId: string,
  teacherId: string,
  grades: number[],
): Promise<{ teacher_id: string; school_id: string; assigned_grades: number[] }> {
  const res = await schoolApi.put(
    `/schools/${schoolId}/teachers/${teacherId}/grades`,
    { grades },
  );
  return res.data;
}

// ── School content (read-only curriculum viewer for teachers) ─────────────────

export interface SchoolContentSubject {
  version_id: string;
  curriculum_id: string;
  subject: string;
  subject_name: string | null;
  version_number: number;
  status: string;
  generated_at: string;
  published_at: string | null;
  alex_warnings_count: number;
  grade: number;
  year: number;
  curriculum_name: string;
  has_content: boolean;
  unit_count: number;
}

export interface SchoolContentUnit {
  unit_id: string;
  title: string;
  sort_order: number;
}

export interface SchoolContentVersion {
  version_id: string;
  curriculum_id: string;
  subject: string;
  subject_name: string | null;
  version_number: number;
  status: string;
  generated_at: string;
  published_at: string | null;
  alex_warnings_count: number;
  grade: number;
  year: number;
  curriculum_name: string;
  units: SchoolContentUnit[];
}

export interface SchoolUnitMeta {
  unit_id: string;
  title: string;
  curriculum_id: string;
  lang: string;
  available_types: string[];
  alex_warnings_count: number;
  annotations: Array<{
    annotation_id: string;
    content_type: string;
    annotation_text: string;
    created_at: string;
    reviewer_email: string | null;
  }>;
}

export async function listSchoolContentSubjects(
  schoolId: string,
  grade?: number,
): Promise<SchoolContentSubject[]> {
  const res = await schoolApi.get<{ subjects: SchoolContentSubject[] }>(
    `/schools/${schoolId}/content/subjects`,
    { params: grade !== undefined ? { grade } : {} },
  );
  return res.data.subjects;
}

export async function getSchoolContentVersion(
  schoolId: string,
  versionId: string,
): Promise<SchoolContentVersion> {
  const res = await schoolApi.get<SchoolContentVersion>(
    `/schools/${schoolId}/content/versions/${versionId}`,
  );
  return res.data;
}

export async function getSchoolUnitMeta(
  schoolId: string,
  versionId: string,
  unitId: string,
  lang = "en",
): Promise<SchoolUnitMeta> {
  const res = await schoolApi.get<SchoolUnitMeta>(
    `/schools/${schoolId}/content/versions/${versionId}/unit/${unitId}`,
    { params: { lang } },
  );
  return res.data;
}

export async function getSchoolUnitContent(
  schoolId: string,
  versionId: string,
  unitId: string,
  contentType: string,
  lang = "en",
): Promise<{ unit_id: string; content_type: string; lang: string; content: unknown }> {
  const res = await schoolApi.get(
    `/schools/${schoolId}/content/versions/${versionId}/unit/${unitId}/${contentType}`,
    { params: { lang } },
  );
  return res.data;
}

// ── Retention dashboard (Phase H) ─────────────────────────────────────────────

export interface RetentionVersion {
  curriculum_id: string;
  grade: number;
  name: string;
  year: number;
  retention_status: "active" | "unavailable" | "purged";
  expires_at: string | null;
  grace_until: string | null;
  renewed_at: string | null;
  is_assigned: boolean;
  days_until_expiry: number | null;
  days_until_purge: number | null;
}

export interface RetentionDashboard {
  school_id: string;
  total_versions: number;
  active_count: number;
  unavailable_count: number;
  purged_count: number;
  curricula: RetentionVersion[];
}

export interface RenewResponse {
  curriculum_id: string;
  grade: number;
  previous_expires_at: string | null;
  new_expires_at: string;
  renewed_at: string;
  retention_status: string;
}

export interface AssignCurriculumResponse {
  school_id: string;
  grade: number;
  curriculum_id: string;
  assigned_at: string;
  previous_curriculum_id: string | null;
}

export async function getRetentionDashboard(schoolId: string): Promise<RetentionDashboard> {
  const res = await schoolApi.get<RetentionDashboard>(`/schools/${schoolId}/retention`);
  return res.data;
}

export async function renewCurriculum(
  schoolId: string,
  curriculumId: string,
): Promise<RenewResponse> {
  const res = await schoolApi.post<RenewResponse>(
    `/schools/${schoolId}/curriculum/versions/${curriculumId}/renew`,
  );
  return res.data;
}

export async function createRenewalCheckout(
  schoolId: string,
  curriculumId: string,
  successUrl: string,
  cancelUrl: string,
): Promise<{ checkout_url: string }> {
  const res = await schoolApi.post<{ checkout_url: string }>(
    `/schools/${schoolId}/curriculum/versions/${curriculumId}/renewal-checkout`,
    { success_url: successUrl, cancel_url: cancelUrl },
  );
  return res.data;
}

export async function createStorageCheckout(
  schoolId: string,
  gbPackage: 5 | 10 | 25,
  successUrl: string,
  cancelUrl: string,
): Promise<{ checkout_url: string }> {
  const res = await schoolApi.post<{ checkout_url: string }>(
    `/schools/${schoolId}/storage/checkout`,
    { gb_package: gbPackage, success_url: successUrl, cancel_url: cancelUrl },
  );
  return res.data;
}

// ── School storage quota ──────────────────────────────────────────────────────

export interface StorageBreakdownItem {
  curriculum_id: string;
  grade: number;
  name: string;
  bytes_used: number;
  gb_used: number;
  job_count: number;
}

export interface SchoolStorageQuota {
  school_id: string;
  base_gb: number;
  purchased_gb: number;
  total_gb: number;
  used_bytes: number;
  used_gb: number;
  used_pct: number;
  over_quota: boolean;
  breakdown: StorageBreakdownItem[];
}

export async function getSchoolStorage(schoolId: string): Promise<SchoolStorageQuota> {
  const res = await schoolApi.get<SchoolStorageQuota>(`/schools/${schoolId}/storage`);
  return res.data;
}

export async function assignCurriculumToGrade(
  schoolId: string,
  grade: number,
  curriculumId: string,
): Promise<AssignCurriculumResponse> {
  const res = await schoolApi.put<AssignCurriculumResponse>(
    `/schools/${schoolId}/grades/${grade}/curriculum`,
    { curriculum_id: curriculumId },
  );
  return res.data;
}

// ── Phase B — Classrooms ──────────────────────────────────────────────────────

export interface ClassroomItem {
  classroom_id: string;
  school_id: string;
  teacher_id: string | null;
  teacher_name: string | null;
  name: string;
  grade: number | null;
  status: "active" | "archived";
  created_at: string;
  student_count: number;
  package_count: number;
}

export interface ClassroomPackageItem {
  curriculum_id: string;
  curriculum_name: string | null;
  assigned_at: string;
  sort_order: number;
}

export interface ClassroomStudentItem {
  student_id: string;
  name: string;
  email: string;
  grade: number | null;
  joined_at: string;
}

export interface ClassroomDetail extends ClassroomItem {
  packages: ClassroomPackageItem[];
  students: ClassroomStudentItem[];
}

export async function listClassrooms(schoolId: string): Promise<ClassroomItem[]> {
  const res = await schoolApi.get<ClassroomItem[]>(`/schools/${schoolId}/classrooms`);
  return res.data;
}

export async function getClassroom(schoolId: string, classroomId: string): Promise<ClassroomDetail> {
  const res = await schoolApi.get<ClassroomDetail>(
    `/schools/${schoolId}/classrooms/${classroomId}`,
  );
  return res.data;
}

export async function createClassroom(
  schoolId: string,
  body: { name: string; grade?: number | null; teacher_id?: string | null },
): Promise<ClassroomItem> {
  const res = await schoolApi.post<ClassroomItem>(`/schools/${schoolId}/classrooms`, body);
  return res.data;
}

export async function updateClassroom(
  schoolId: string,
  classroomId: string,
  body: { name?: string; grade?: number | null; teacher_id?: string | null; status?: string },
): Promise<ClassroomItem> {
  const res = await schoolApi.patch<ClassroomItem>(
    `/schools/${schoolId}/classrooms/${classroomId}`,
    body,
  );
  return res.data;
}

export async function assignPackageToClassroom(
  schoolId: string,
  classroomId: string,
  curriculumId: string,
  sortOrder = 0,
): Promise<void> {
  await schoolApi.post(
    `/schools/${schoolId}/classrooms/${classroomId}/packages`,
    { curriculum_id: curriculumId, sort_order: sortOrder },
  );
}

export async function reorderPackageInClassroom(
  schoolId: string,
  classroomId: string,
  curriculumId: string,
  sortOrder: number,
): Promise<void> {
  await schoolApi.patch(
    `/schools/${schoolId}/classrooms/${classroomId}/packages/${curriculumId}`,
    { sort_order: sortOrder },
  );
}

export async function removePackageFromClassroom(
  schoolId: string,
  classroomId: string,
  curriculumId: string,
): Promise<void> {
  await schoolApi.delete(
    `/schools/${schoolId}/classrooms/${classroomId}/packages/${curriculumId}`,
  );
}

export async function assignStudentToClassroom(
  schoolId: string,
  classroomId: string,
  studentId: string,
): Promise<void> {
  await schoolApi.post(
    `/schools/${schoolId}/classrooms/${classroomId}/students`,
    { student_id: studentId },
  );
}

export async function removeStudentFromClassroom(
  schoolId: string,
  classroomId: string,
  studentId: string,
): Promise<void> {
  await schoolApi.delete(
    `/schools/${schoolId}/classrooms/${classroomId}/students/${studentId}`,
  );
}

// ── Phase C — Curriculum Catalog ──────────────────────────────────────────────

export interface CatalogSubjectSummary {
  subject: string;
  subject_name: string | null;
  unit_count: number;
  has_content: boolean;
}

export interface CatalogEntry {
  curriculum_id: string;
  name: string;
  grade: number;
  year: number;
  is_default: boolean;
  owner_type: string;
  subject_count: number;
  unit_count: number;
  subjects: CatalogSubjectSummary[];
  created_at: string;
}

export interface CatalogResponse {
  packages: CatalogEntry[];
  total: number;
}

export async function getCatalog(grade?: number): Promise<CatalogResponse> {
  const params = grade !== undefined ? { grade } : {};
  const res = await schoolApi.get<CatalogResponse>("/curricula/catalog", { params });
  return res.data;
}

// ── Phase D — Curriculum Definitions ──────────────────────────────────────────

export interface DefinitionUnit {
  title: string;
}

export interface DefinitionSubject {
  subject_label: string;
  units: DefinitionUnit[];
}

export interface CurriculumDefinition {
  definition_id: string;
  school_id: string;
  submitted_by: string;
  submitted_by_name: string | null;
  name: string;
  grade: number;
  languages: string[];
  subjects: DefinitionSubject[];
  status: "pending_approval" | "approved" | "rejected";
  rejection_reason: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface DefinitionListResponse {
  definitions: CurriculumDefinition[];
  total: number;
}

export interface SubmitDefinitionRequest {
  name: string;
  grade: number;
  languages: string[];
  subjects: DefinitionSubject[];
}

export async function listDefinitions(
  schoolId: string,
  status?: string,
): Promise<DefinitionListResponse> {
  const params = status ? { status } : {};
  const res = await schoolApi.get<DefinitionListResponse>(
    `/schools/${schoolId}/curriculum/definitions`,
    { params },
  );
  return res.data;
}

export async function getDefinition(
  schoolId: string,
  definitionId: string,
): Promise<CurriculumDefinition> {
  const res = await schoolApi.get<CurriculumDefinition>(
    `/schools/${schoolId}/curriculum/definitions/${definitionId}`,
  );
  return res.data;
}

export async function submitDefinition(
  schoolId: string,
  body: SubmitDefinitionRequest,
): Promise<CurriculumDefinition> {
  const res = await schoolApi.post<CurriculumDefinition>(
    `/schools/${schoolId}/curriculum/definitions`,
    body,
  );
  return res.data;
}

export async function approveDefinition(
  schoolId: string,
  definitionId: string,
): Promise<CurriculumDefinition> {
  const res = await schoolApi.post<CurriculumDefinition>(
    `/schools/${schoolId}/curriculum/definitions/${definitionId}/approve`,
  );
  return res.data;
}

export async function rejectDefinition(
  schoolId: string,
  definitionId: string,
  reason: string,
): Promise<CurriculumDefinition> {
  const res = await schoolApi.post<CurriculumDefinition>(
    `/schools/${schoolId}/curriculum/definitions/${definitionId}/reject`,
    { reason },
  );
  return res.data;
}

// ── Setup status (Layer 1.5 onboarding checklist) ────────────────────────────

export interface SetupStatus {
  teacher_count: number;
  student_count: number;
  classroom_count: number;
  curriculum_assigned: boolean;
  setup_complete: boolean;
}

export async function getSetupStatus(schoolId: string): Promise<SetupStatus> {
  const res = await schoolApi.get<SetupStatus>(`/schools/${schoolId}/setup-status`);
  return res.data;
}
