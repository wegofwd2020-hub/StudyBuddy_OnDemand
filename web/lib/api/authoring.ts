/**
 * web/lib/api/authoring.ts
 *
 * Admin API client for the Curriculum Authoring Studio (super-admin only).
 * Mirrors the backend endpoints under /api/v1/admin/authoring/. All calls go
 * through the admin axios instance (sb_admin_token injected).
 */
import adminApi from "./admin-client";

// ── Structured TOC tree ────────────────────────────────────────────────────
export interface TopicNode {
  title: string;
  subtopics: string[];
  prerequisites: string[];
}
export interface SubjectNode {
  subject_label: string;
  units: TopicNode[];
}
export interface StructuredTOC {
  subjects: SubjectNode[];
}

export interface FlowWarning {
  kind: string;
  unit?: string;
  subject?: string | null;
  detail?: string;
}
export interface FlowReport {
  warnings: FlowWarning[];
  summary: string;
}

// ── Project ────────────────────────────────────────────────────────────────
export type AuthoringStatus =
  | "draft"
  | "analyzing"
  | "analyzed"
  | "structured"
  | "generating"
  | "generated"
  | "published";

export interface ProjectSummary {
  project_id: string;
  title: string;
  grade: number | null;
  languages: string[];
  status: AuthoringStatus;
  curriculum_id: string | null;
  visibility: "private" | "catalog";
  created_at: string;
  updated_at: string;
}
export interface ProjectDetail extends ProjectSummary {
  raw_toc: string | null;
  structured_toc: StructuredTOC | null;
  flow_report: FlowReport | null;
  analyze_error: string | null;
}

export interface CreateProjectInput {
  title: string;
  grade: number | null;
  languages: string[];
  raw_toc: string;
}

// ── Topics / content ─────────────────────────────────────────────────────────
export type ContentType =
  | "lesson"
  | "tutorial"
  | "quiz_set_1"
  | "quiz_set_2"
  | "quiz_set_3"
  | "experiment";

export interface TopicContentStatus {
  content_type: ContentType;
  lang: string;
  version_number: number;
  review_status: "pending" | "accepted";
}
export interface TopicListItem {
  unit_id: string;
  title: string;
  subject: string;
  contents: TopicContentStatus[];
  content_count: number;
  accepted_count: number;
}
export interface TopicListResponse {
  curriculum_id: string | null;
  status: AuthoringStatus | null;
  topics: TopicListItem[];
  total: number;
}

export interface TopicVersion {
  topic_version_id: string;
  unit_id: string;
  lang: string;
  content_type: ContentType;
  version_number: number;
  body: Record<string, unknown> | null;
  regen_reason: string | null;
  flow_recheck: FlowWarning[] | null;
  review_status: "pending" | "accepted";
  created_at: string;
  is_active: boolean;
}

// ── Snapshots ────────────────────────────────────────────────────────────────
export interface SnapshotItem {
  snapshot_id: string;
  snapshot_number: number;
  label: string | null;
  created_at: string;
}

// ── Endpoints ──────────────────────────────────────────────────────────────
const BASE = "/admin/authoring/projects";

export async function listProjects(): Promise<ProjectSummary[]> {
  const res = await adminApi.get<{ projects: ProjectSummary[]; total: number }>(BASE);
  return res.data.projects;
}

export async function createProject(
  input: CreateProjectInput,
): Promise<{ project_id: string }> {
  const res = await adminApi.post<{ project_id: string; status: string }>(BASE, input);
  return res.data;
}

export async function getProject(id: string): Promise<ProjectDetail> {
  const res = await adminApi.get<ProjectDetail>(`${BASE}/${id}`);
  return res.data;
}

export async function analyzeProject(id: string): Promise<void> {
  await adminApi.post(`${BASE}/${id}/analyze`);
}

export async function saveStructure(
  id: string,
  structured_toc: StructuredTOC,
): Promise<ProjectDetail> {
  const res = await adminApi.put<ProjectDetail>(`${BASE}/${id}/structure`, {
    structured_toc,
  });
  return res.data;
}

export async function materialize(
  id: string,
): Promise<{ curriculum_id: string; units_created: number }> {
  const res = await adminApi.post<{ curriculum_id: string; units_created: number }>(
    `${BASE}/${id}/materialize`,
  );
  return res.data;
}

export async function generate(id: string, langs = "en", force = false): Promise<void> {
  await adminApi.post(`${BASE}/${id}/generate`, { langs, force });
}

export async function listTopics(id: string): Promise<TopicListResponse> {
  const res = await adminApi.get<TopicListResponse>(`${BASE}/${id}/topics`);
  return res.data;
}

export async function getTopic(
  id: string,
  unitId: string,
  contentType: ContentType,
  lang = "en",
): Promise<TopicVersion> {
  const res = await adminApi.get<TopicVersion>(`${BASE}/${id}/topics/${unitId}`, {
    params: { content_type: contentType, lang },
  });
  return res.data;
}

export async function getTopicHistory(
  id: string,
  unitId: string,
  contentType: ContentType,
  lang = "en",
): Promise<TopicVersion[]> {
  const res = await adminApi.get<{ versions: TopicVersion[] }>(
    `${BASE}/${id}/topics/${unitId}`,
    {
      params: { content_type: contentType, lang, history: 1 },
    },
  );
  return res.data.versions;
}

export async function regenerateTopic(
  id: string,
  unitId: string,
  contentType: ContentType,
  reason: string,
  lang = "en",
): Promise<{ version_number: number; flow_recheck: FlowWarning[] }> {
  const res = await adminApi.post<{
    version_number: number;
    flow_recheck: FlowWarning[];
  }>(`${BASE}/${id}/topics/${unitId}/regenerate`, {
    content_type: contentType,
    reason,
    lang,
  });
  return res.data;
}

export async function acceptTopic(
  id: string,
  unitId: string,
  contentType: ContentType,
  lang = "en",
): Promise<void> {
  await adminApi.post(`${BASE}/${id}/topics/${unitId}/accept`, {
    content_type: contentType,
    lang,
  });
}

export async function listSnapshots(id: string): Promise<SnapshotItem[]> {
  const res = await adminApi.get<{ snapshots: SnapshotItem[] }>(
    `${BASE}/${id}/snapshots`,
  );
  return res.data.snapshots;
}

export async function createSnapshot(id: string, label?: string): Promise<SnapshotItem> {
  const res = await adminApi.post<SnapshotItem>(`${BASE}/${id}/snapshots`, {
    label: label ?? null,
  });
  return res.data;
}

export async function restoreSnapshot(id: string, snapshotId: string): Promise<void> {
  await adminApi.post(`${BASE}/${id}/snapshots/${snapshotId}/restore`);
}

export async function flowRecheck(id: string): Promise<void> {
  await adminApi.post(`${BASE}/${id}/flow-recheck`);
}

export async function publishProject(
  id: string,
  visibility: "private" | "catalog",
): Promise<{ curriculum_id: string }> {
  const res = await adminApi.post<{ curriculum_id: string }>(`${BASE}/${id}/publish`, {
    visibility,
  });
  return res.data;
}
