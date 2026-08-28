import api from "./client";
import type {
  SessionStartResponse,
  AnswerResponse,
  SessionEndResponse,
  ProgressHistory,
} from "@/lib/types/api";

/**
 * Open a quiz attempt.
 *
 * No curriculum id is sent: the server resolves the student's curriculum from
 * their identity. This page used to send a hardcoded "default", which the
 * session stored and grading then looked the answer key up under — nothing
 * resolves there, so every answer 404'd and Submit became a dead button (#524).
 */
export async function startSession(unitId: string): Promise<SessionStartResponse> {
  // Backend: POST /progress/session  (not /session/start)
  const res = await api.post<SessionStartResponse>("/progress/session", {
    unit_id: unitId,
  });
  return res.data;
}

/**
 * Submit the option the student picked. The server grades it.
 *
 * We send only the choice — never whether it was right. The verdict, the correct
 * option and the explanation all come back in the response; the browser is never
 * given the answer key up front.
 *
 * `question_id` must be the id from the quiz payload (the content's own ids are
 * `q1`…`qN`), because that is what the server looks the answer up by.
 */
export async function submitAnswer(payload: {
  session_id: string;
  question_id: string;
  answer_index: number;
  ms_taken?: number;
}): Promise<AnswerResponse> {
  const { session_id, question_id, answer_index, ms_taken = 0 } = payload;

  const res = await api.post<{
    answer_id: string;
    correct: boolean;
    correct_index: number;
    explanation: string;
  }>(`/progress/session/${session_id}/answer`, {
    question_id,
    student_answer: answer_index,
    ms_taken,
  });

  return {
    correct: res.data.correct,
    correct_index: res.data.correct_index,
    explanation: res.data.explanation ?? "",
  };
}

/**
 * Close the session. The score is whatever the server graded during it — there is
 * no score to send.
 */
export async function endSession(sessionId: string): Promise<SessionEndResponse> {
  const res = await api.post<{
    session_id: string;
    score: number;
    total_questions: number;
    passed: boolean;
    attempt_number: number;
    ended_at: string;
  }>(`/progress/session/${sessionId}/end`, {});

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
    unit_title: s.unit_id, // title not returned by this endpoint
    subject: s.subject,
    started_at: s.started_at,
    ended_at: s.ended_at,
    score: s.score,
    total: s.total_questions,
    passed: s.passed,
    attempt_number: s.attempt_number,
  }));

  // No unit_progress here any more (#677). This used to derive a unit's status
  // in the browser from quiz sessions alone — a definition separate from the
  // server's, with no lesson input and no `not_started` branch, which is why
  // #675's fix was invisible on the Curriculum Map. Status now comes from
  // /student/progress via `useProgressMap`; leaving the derivation behind as
  // dead code would just wait for someone to pick it up again.
  return { sessions };
}

/**
 * Which options the student has already picked in this session (#667).
 *
 * A refresh mid-quiz used to clear every selection on screen. The answers were
 * never lost — they are graded server-side as they are given and the session
 * resumes with the same question set (#646) — the page just could not read them
 * back, so a student re-answered questions they had already done.
 *
 * Returns the picked index only, never whether it was correct: the reveal
 * belongs to the summary (#532).
 */
export async function getSessionAnswers(
  sessionId: string,
): Promise<{ question_id: string; answer_index: number }[]> {
  const res = await api.get<{
    session_id: string;
    answers: { question_id: string; answer_index: number }[];
  }>(`/progress/session/${sessionId}/answers`);
  return res.data.answers;
}
