import api from "./client";
import type {
  LessonContent,
  AudioUrlResponse,
  QuizContent,
  TutorialContent,
  ExperimentContent,
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
  correct_option: string; // "A" | "B" | "C" | "D"
  explanation: string;
  difficulty: string;
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
}

const OPTION_IDS = ["A", "B", "C", "D"];

export async function getQuiz(unitId: string): Promise<QuizContent> {
  const res = await api.get<BackendQuizResponse>(`/content/${unitId}/quiz`);
  const raw = res.data;
  return {
    unit_id: raw.unit_id,
    title: `Quiz — Set ${raw.set_number}`,
    pass_threshold: raw.passing_score,
    questions: raw.questions.map((q, index) => ({
      index,
      question: q.question_text,
      options: q.options.map((o) => o.text),
      correct_index: OPTION_IDS.indexOf(q.correct_option),
      explanation: q.explanation,
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
