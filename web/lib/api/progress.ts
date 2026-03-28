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
  // Backend: POST /progress/session  (not /session/start)
  const res = await api.post<SessionStartResponse>("/progress/session", {
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
  correct_index: number;
}): Promise<AnswerResponse> {
  // Backend: POST /progress/session/{session_id}/answer
  // Body: { question_id, student_answer, correct_answer, correct, ms_taken }
  const { session_id, unit_id, question_index, answer_index, correct_index } = payload;
  const correct = answer_index === correct_index;

  const res = await api.post<{ answer_id: string; correct: boolean }>(
    `/progress/session/${session_id}/answer`,
    {
      question_id: `${unit_id}-Q${question_index + 1}`,
      student_answer: answer_index,
      correct_answer: correct_index,
      correct,
      ms_taken: 0,
    },
  );
  // Return shape the QuizPlayer expects
  return { correct: res.data.correct, explanation: "" };
}

export async function endSession(
  sessionId: string,
  score: number,
  total: number,
): Promise<SessionEndResponse> {
  // Backend: POST /progress/session/{session_id}/end
  // Body: { score, total_questions }  (not /session/end with body session_id)
  const res = await api.post<{
    session_id: string;
    score: number;
    total_questions: number;
    passed: boolean;
    attempt_number: number;
    ended_at: string;
  }>(`/progress/session/${sessionId}/end`, {
    score,
    total_questions: total,
  });
  // Map total_questions → total for the SessionEndResponse type
  return {
    score: res.data.score,
    total: res.data.total_questions,
    passed: res.data.passed,
    attempt_number: res.data.attempt_number,
  };
}

export async function getProgressHistory(limit = 20): Promise<ProgressHistory> {
  const res = await api.get<{
    student_id: string;
    sessions: {
      session_id: string;
      unit_id: string;
      curriculum_id: string;
      subject: string;
      started_at: string;
      ended_at: string | null;
      score: number | null;
      total_questions: number | null;
      completed: boolean;
      passed: boolean | null;
      attempt_number: number;
    }[];
  }>(`/progress/student?limit=${limit}`);

  const raw = res.data;

  // Map backend sessions to frontend ProgressSession shape
  const sessions = raw.sessions.map((s) => ({
    session_id: s.session_id,
    unit_id: s.unit_id,
    unit_title: s.unit_id,   // title not returned by this endpoint
    subject: s.subject,
    started_at: s.started_at,
    ended_at: s.ended_at,
    score: s.score,
    total: s.total_questions,
    passed: s.passed,
    attempt_number: s.attempt_number,
  }));

  // Derive unit_progress from sessions
  const byUnit = new Map<string, typeof raw.sessions>();
  for (const s of raw.sessions) {
    if (!byUnit.has(s.unit_id)) byUnit.set(s.unit_id, []);
    byUnit.get(s.unit_id)!.push(s);
  }

  const unit_progress = Array.from(byUnit.entries()).map(([unit_id, unitSessions]) => {
    const completed = unitSessions.filter((s) => s.completed);
    const passed = completed.filter((s) => s.passed);
    const scores = completed.map((s) => s.score).filter((s): s is number => s !== null);
    const best_score = scores.length ? Math.max(...scores) : null;
    const last = unitSessions.reduce((a, b) =>
      a.started_at > b.started_at ? a : b,
    );

    let status: "completed" | "needs_retry" | "in_progress" | "not_started";
    if (passed.length > 0) status = "completed";
    else if (completed.length > 0) status = "needs_retry";
    else status = "in_progress";

    return {
      unit_id,
      status,
      best_score,
      attempts: unitSessions.length,
      last_attempted_at: last.started_at,
    };
  });

  return { sessions, unit_progress };
}
