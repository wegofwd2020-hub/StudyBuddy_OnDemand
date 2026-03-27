import api from "./client";
import type {
  SessionStartResponse,
  AnswerResponse,
  SessionEndResponse,
  ProgressHistory,
} from "@/lib/types/api";

export async function startSession(
  unitId: string,
  curriculumId: string,
): Promise<SessionStartResponse> {
  const res = await api.post<SessionStartResponse>("/progress/session/start", {
    unit_id: unitId,
    curriculum_id: curriculumId,
  });
  return res.data;
}

export async function submitAnswer(payload: {
  session_id: string;
  unit_id: string;
  question_index: number;
  answer_index: number;
}): Promise<AnswerResponse> {
  const res = await api.post<AnswerResponse>("/progress/answer", payload);
  return res.data;
}

export async function endSession(
  sessionId: string,
  score: number,
  total: number,
): Promise<SessionEndResponse> {
  const res = await api.post<SessionEndResponse>("/progress/session/end", {
    session_id: sessionId,
    score,
    total,
  });
  return res.data;
}

export async function getProgressHistory(limit = 20): Promise<ProgressHistory> {
  const res = await api.get<ProgressHistory>(`/progress/history?limit=${limit}`);
  return res.data;
}
