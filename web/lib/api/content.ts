import api from "./client";
import type {
  LessonContent,
  AudioUrlResponse,
  QuizContent,
  TutorialContent,
  ExperimentContent,
  VisualBlock,
} from "@/lib/types/api";

export async function getLesson(unitId: string): Promise<LessonContent> {
  const res = await api.get<LessonContent>(`/content/${unitId}/lesson`);
  return res.data;
}

export async function getLessonAudioUrl(unitId: string): Promise<string> {
  const res = await api.get<AudioUrlResponse>(`/content/${unitId}/lesson/audio`);
  return res.data.url;
}

// Backend quiz shape differs from the simpler QuizContent type the UI uses.
interface BackendQuizOption {
  option_id: string;
  text: string;
}
interface BackendQuizQuestion {
  question_id: string;
  question_text: string;
  question_type: string;
  options: BackendQuizOption[];
  difficulty: string;
  // No correct_option / explanation — the server strips the answer key before
  // sending the quiz. Grading happens in POST /progress/session/{id}/answer.
}
interface BackendQuizResponse {
  unit_id: string;
  set_number: number;
  language: string;
  questions: BackendQuizQuestion[];
  total_questions: number;
  estimated_duration_minutes: number;
  passing_score: number;
  generated_at: string;
  model: string;
  content_version: number;
  subject: string | null;
  // The unit's own name. Present since #704; this interface did not declare it,
  // so the mapper below could not copy it and nothing complained.
  unit_title: string | null;
}

export async function getQuiz(unitId: string, sessionId?: string): Promise<QuizContent> {
  // The session id pins which quiz set is served, so a refetch (window focus,
  // remount, a retry) cannot change the questions mid-attempt (#567).
  const res = await api.get<BackendQuizResponse>(
    `/content/${unitId}/quiz${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ""}`,
  );
  const raw = res.data;
  return {
    unit_id: raw.unit_id,
    title: `Quiz — Set ${raw.set_number}`,
    pass_threshold: raw.passing_score,
    subject: raw.subject ?? undefined,
    // The field this mapper used to drop on the floor.
    //
    // #704 added `unit_title` to the API and to the result screen, which renders
    // `{quiz.unit_title && ...}`. Both halves were correct and verified. This
    // mapper sits between them and never copied the field, so the value arrived
    // from the server and was discarded one line before the component that
    // wanted it.
    //
    // Nothing caught it: `QuizContent.unit_title` is optional, so a mapper that
    // omits it typechecks perfectly, and API-level probes kept confirming the
    // server was right — which it was. A tester reported it twice as "still
    // facing the same problem" while every check I ran said it was fixed.
    unit_title: raw.unit_title ?? undefined,
    questions: raw.questions.map((q, index) => ({
      index,
      question_id: q.question_id,
      question: q.question_text,
      options: q.options.map((o) => o.text),
    })),
  };
}

interface BackendTutorialResponse {
  unit_id: string;
  language: string;
  title: string;
  sections: Array<{
    section_id: string;
    title: string;
    content: string;
    visuals?: VisualBlock[];
    examples: string[];
    practice_question: string;
  }>;
  common_mistakes: string[];
  generated_at: string;
  model: string;
  content_version: number;
}

export async function getTutorial(unitId: string): Promise<TutorialContent> {
  const res = await api.get<BackendTutorialResponse>(`/content/${unitId}/tutorial`);
  const raw = res.data;
  return {
    unit_id: raw.unit_id,
    title: raw.title,
    sections: raw.sections.map((s) => ({
      section_id: s.section_id,
      title: s.title,
      content: s.content,
      visuals: s.visuals,
      examples: s.examples,
      practice_question: s.practice_question,
    })),
    common_mistakes: raw.common_mistakes,
  };
}

export async function getExperiment(unitId: string): Promise<ExperimentContent> {
  const res = await api.get<ExperimentContent>(`/content/${unitId}/experiment`);
  return res.data;
}
