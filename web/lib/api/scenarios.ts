import axios from "axios";

const SCENARIO_KEY = "jt2026";

const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
    "x-scenario-key": SCENARIO_KEY,
  },
  timeout: 30_000,
});

export interface ClipStatus {
  turn_index: number;
  status: "pending" | "generating" | "ready" | "error";
  error?: string | null;
}

export interface GenerateClipsResponse {
  job_id: string;
  scenario_id: string;
}

export interface ClipsStatusResponse {
  job_id: string;
  scenario_id: string;
  status: "pending" | "running" | "done" | "failed";
  total_clips: number;
  completed_clips: number;
  clips: ClipStatus[];
  error?: string | null;
}

export async function generateClips(scenario: object): Promise<GenerateClipsResponse> {
  const res = await api.post<GenerateClipsResponse>("/scenarios/generate-clips", {
    scenario,
  });
  return res.data;
}

export async function pollClipsStatus(
  scenarioId: string,
  jobId: string,
): Promise<ClipsStatusResponse> {
  const res = await api.get<ClipsStatusResponse>(
    `/scenarios/${scenarioId}/clips/status`,
    { params: { job_id: jobId } },
  );
  return res.data;
}

export function clipVideoUrl(scenarioId: string, turnIndex: number): string {
  return `/api/v1/scenarios/${scenarioId}/clips/${turnIndex}`;
}
