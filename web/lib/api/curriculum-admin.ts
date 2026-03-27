import schoolApi from "./school-client";

// ── Upload ────────────────────────────────────────────────────────────────────

export interface UploadError {
  row: number;
  field: string;
  message: string;
}

export interface CurriculumUploadResponse {
  curriculum_id: string | null;
  unit_count: number;
  errors: UploadError[];
}

export async function uploadCurriculumXlsx(
  file: File,
  grade: number,
  year: number,
  name: string,
): Promise<CurriculumUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await schoolApi.post<CurriculumUploadResponse>(
    `/curriculum/upload/xlsx?grade=${grade}&year=${year}&name=${encodeURIComponent(name)}`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return res.data;
}

export async function downloadXlsxTemplate(): Promise<Blob> {
  const res = await schoolApi.get("/curriculum/template", { responseType: "blob" });
  return res.data as Blob;
}

// ── Pipeline ──────────────────────────────────────────────────────────────────

export interface PipelineTriggerResponse {
  job_id: string;
  status: string;
}

export interface PipelineJobStatus {
  job_id: string;
  status: "queued" | "running" | "done" | "failed";
  built: number;
  failed: number;
  total: number;
  progress_pct: number;
}

export async function triggerPipeline(
  curriculumId: string,
  langs = "en",
  force = false,
): Promise<PipelineTriggerResponse> {
  const res = await schoolApi.post<PipelineTriggerResponse>(
    "/curriculum/pipeline/trigger",
    { curriculum_id: curriculumId, langs, force },
  );
  return res.data;
}

export async function getPipelineStatus(jobId: string): Promise<PipelineJobStatus> {
  const res = await schoolApi.get<PipelineJobStatus>(
    `/curriculum/pipeline/${jobId}/status`,
  );
  return res.data;
}
