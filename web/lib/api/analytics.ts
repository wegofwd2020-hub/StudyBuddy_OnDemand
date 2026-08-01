import api from "./client";
import type { LessonViewStartResponse, StudentStats } from "@/lib/types/api";

/** The server attributes the view to the student's resolved curriculum (#524). */
export async function startLessonView(unitId: string): Promise<LessonViewStartResponse> {
  const res = await api.post<LessonViewStartResponse>("/analytics/lesson/start", {
    unit_id: unitId,
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

/**
 * Reliable variant of {@link endLessonView} for page-unload paths (issue #464).
 *
 * Lesson-time records were lost when a student closed the tab or refreshed: the
 * end-write fired from a React unmount cleanup via axios, which the browser
 * cancels as the page goes away — so `lesson_views.duration_s` stayed NULL and
 * "Time" showed 0m.
 *
 * `keepalive: true` lets the request outlive the page. We use `fetch` rather
 * than `navigator.sendBeacon` because the analytics endpoint requires the
 * `Authorization` header, which sendBeacon cannot set. Same-origin (`/api/v1`).
 * Fire-and-forget — never throws into the caller.
 */
export function endLessonViewBeacon(
  viewId: string,
  durationSeconds: number,
  audioPlayed: boolean,
  experimentViewed: boolean,
): void {
  if (typeof window === "undefined") return;
  const token = localStorage.getItem("sb_token");
  void fetch("/api/v1/analytics/lesson/end", {
    method: "POST",
    keepalive: true,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      view_id: viewId,
      duration_s: durationSeconds,
      audio_played: audioPlayed,
      experiment_viewed: experimentViewed,
    }),
  }).catch(() => {});
}

export async function getStudentStats(
  period: "7d" | "30d" | "all" = "30d",
): Promise<StudentStats> {
  const res = await api.get<StudentStats>(`/analytics/student/stats?period=${period}`);
  return res.data;
}
