/**
 * Visual asset management API client (issue #318 phase 2b/2c).
 *
 * Wraps the school-scoped /schools/{school_id}/visuals/* endpoints.
 * All calls auth via the school-portal Axios instance (sb_teacher_token).
 */
import schoolApi from "./school-client";
import type { VisualBlock } from "@/lib/types/api";

export interface VisualAsset {
  path: string;
  url: string;
}

export interface UploadResult extends VisualAsset {
  bytes: number;
  content_type: string;
}

export interface UploadParams {
  schoolId: string;
  curriculumId: string;
  unitId: string;
  sectionId: string;
  file: File;
}

export async function uploadVisual(p: UploadParams): Promise<UploadResult> {
  const fd = new FormData();
  fd.append("file", p.file);
  fd.append("curriculum_id", p.curriculumId);
  fd.append("unit_id", p.unitId);
  fd.append("section_id", p.sectionId);
  const res = await schoolApi.post<UploadResult>(
    `/schools/${p.schoolId}/visuals/upload`,
    fd,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return res.data;
}

export async function listVisuals(
  schoolId: string,
  filter?: { curriculumId?: string; unitId?: string },
): Promise<VisualAsset[]> {
  const params: Record<string, string> = {};
  if (filter?.curriculumId) params.curriculum_id = filter.curriculumId;
  if (filter?.unitId) params.unit_id = filter.unitId;
  const res = await schoolApi.get<{ assets: VisualAsset[] }>(
    `/schools/${schoolId}/visuals`,
    { params },
  );
  return res.data.assets;
}

export async function deleteVisual(
  schoolId: string,
  assetPath: string,
): Promise<void> {
  // assetPath may contain slashes; the backend route uses `:path` matching.
  // axios's serializer keeps the slashes intact when we hand-build the URL.
  const url = `/schools/${schoolId}/visuals/${assetPath}`;
  await schoolApi.delete(url);
}

// ── Per-unit visual editor (issue #318 phase 2c-3) ─────────────────────────

export interface SectionSummary {
  section_id: string;
  title: string;
  visuals: VisualBlock[];
}

export interface SectionVisualsListResponse {
  unit_id: string;
  title: string;
  sections: SectionSummary[];
  override_version: number | null;
  override_status: string | null;
}

export interface SectionVisualsUpdateResponse {
  override_id: string;
  version_number: number;
  review_status: string;
}

export async function listSectionVisuals(
  schoolId: string,
  adoptionId: string,
  unitId: string,
): Promise<SectionVisualsListResponse> {
  const res = await schoolApi.get<SectionVisualsListResponse>(
    `/schools/${schoolId}/visuals/sections`,
    { params: { adoption_id: adoptionId, unit_id: unitId } },
  );
  return res.data;
}

export async function putSectionVisuals(
  schoolId: string,
  payload: {
    adoptionId: string;
    unitId: string;
    sectionId: string;
    visuals: VisualBlock[];
  },
): Promise<SectionVisualsUpdateResponse> {
  const res = await schoolApi.put<SectionVisualsUpdateResponse>(
    `/schools/${schoolId}/visuals/sections`,
    {
      adoption_id: payload.adoptionId,
      unit_id: payload.unitId,
      section_id: payload.sectionId,
      visuals: payload.visuals,
    },
  );
  return res.data;
}
