// ─── Curriculum ──────────────────────────────────────────────────────────────

export interface Unit {
  unit_id: string;
  title: string;
  subject: string;
  grade: number;
  sort_order: number;
  has_lab: boolean;
}

export interface Subject {
  subject: string;
  units: Unit[];
}

export interface CurriculumTree {
  curriculum_id: string;
  grade: number;
  subjects: Subject[];
}

// ─── Content ─────────────────────────────────────────────────────────────────

export interface LessonSection {
  heading: string;
  body: string;
}

export interface LessonContent {
  unit_id: string;
  title: string;
  grade: number;
  subject: string;
  lang: string;
  sections: LessonSection[];
  key_points: string[];
  has_audio: boolean;
}

export interface AudioUrlResponse {
  url: string;
  expires_in: number;
}

export interface QuizQuestion {
  index: number;
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

export interface QuizContent {
  unit_id: string;
  title: string;
  pass_threshold: number;
  questions: QuizQuestion[];
}

export interface TutorialStep {
  step: number;
  title: string;
  body: string;
}

export interface TutorialContent {
  unit_id: string;
  title: string;
  objective: string;
  steps: TutorialStep[];
  summary: string;
}

export interface ExperimentStep {
  step: number;
  instruction: string;
}

export interface ExperimentContent {
  unit_id: string;
  title: string;
  materials: string[];
  steps: ExperimentStep[];
  safety_notes: string[];
  expected_outcome: string;
}

// ─── Progress ────────────────────────────────────────────────────────────────

export interface SessionStartResponse {
  session_id: string;
}

export interface AnswerResponse {
  correct: boolean;
  explanation: string;
}

export interface SessionEndResponse {
  score: number;
  total: number;
  passed: boolean;
  attempt_number: number;
}

export type UnitStatus = "completed" | "needs_retry" | "in_progress" | "not_started";

export interface ProgressSession {
  session_id: string;
  unit_id: string;
  unit_title: string;
  subject: string;
  started_at: string;
  ended_at: string | null;
  score: number | null;
  total: number | null;
  passed: boolean | null;
  attempt_number: number;
}

export interface UnitProgress {
  unit_id: string;
  status: UnitStatus;
  best_score: number | null;
  attempts: number;
  last_attempted_at: string | null;
}

export interface ProgressHistory {
  sessions: ProgressSession[];
  unit_progress: UnitProgress[];
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export interface LessonViewStartResponse {
  view_id: string;
}

export interface StudentStats {
  streak_days: number;
  lessons_viewed: number;
  quizzes_completed: number;
  pass_rate: number;
  avg_score: number;
  audio_sessions: number;
  session_dates: string[];
  subject_breakdown: { subject: string; lessons: number; pass_rate: number }[];
}

// ─── Feedback ────────────────────────────────────────────────────────────────

export type FeedbackRating = "up" | "down";

export interface FeedbackPayload {
  unit_id: string;
  content_type: "lesson" | "quiz" | "experiment" | "tutorial";
  rating: FeedbackRating;
  comment?: string;
}
