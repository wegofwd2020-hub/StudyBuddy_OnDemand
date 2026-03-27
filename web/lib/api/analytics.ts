import api from "./client";
import type { LessonViewStartResponse, StudentStats } from "@/lib/types/api";

export async function startLessonView(
  unitId: string,
  curriculumId: string,
): Promise<LessonViewStartResponse> {
  const res = await api.post<LessonViewStartResponse>("/analytics/lesson/start", {
    unit_id: unitId,
    curriculum_id: curriculumId,
  });
  return res.data;
}

export async function endLessonView(
  viewId: string,
  durationSeconds: number,
  audioPlayed: boolean,
  experimentViewed: boolean,
): Promise<void> {
  await api.post("/analytics/lesson/end", {
    view_id: viewId,
    duration_s: durationSeconds,
    audio_played: audioPlayed,
    experiment_viewed: experimentViewed,
  });
}

export async function getStudentStats(
  period: "7d" | "30d" | "all" = "30d",
): Promise<StudentStats> {
  const res = await api.get<StudentStats>(`/analytics/student/stats?period=${period}`);
  return res.data;
}
