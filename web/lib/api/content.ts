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

export async function getQuiz(unitId: string): Promise<QuizContent> {
  const res = await api.get<QuizContent>(`/content/${unitId}/quiz`);
  return res.data;
}

export async function getTutorial(unitId: string): Promise<TutorialContent> {
  const res = await api.get<TutorialContent>(`/content/${unitId}/tutorial`);
  return res.data;
}

export async function getExperiment(unitId: string): Promise<ExperimentContent> {
  const res = await api.get<ExperimentContent>(`/content/${unitId}/experiment`);
  return res.data;
}
