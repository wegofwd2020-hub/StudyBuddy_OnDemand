// ─── Curriculum ──────────────────────────────────────────────────────────────

export interface Unit {
  unit_id: string;
  title: string;
  subject: string;
  grade: number;
  sort_order: number;
  has_lab: boolean;
  /**
   * Whether generated content exists for this unit. Absent (undefined) is
   * treated as available — only an explicit `false` greys out / disables
   * selection so the click doesn't dead-end on a "Could not load" 404
   * (#468/#469).
   */
  has_content?: boolean;
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
  /** The content's own question id (`q1`…`qN`) — what the server grades against. */
  question_id: string;
  question: string;
  options: string[];
  // No correct_index / explanation: the answer key is not sent to the browser.
  // Both arrive in AnswerResponse once the student has committed to a choice.
}

export interface QuizContent {
  unit_id: string;
  title: string;
  pass_threshold: number;
  questions: QuizQuestion[];
  subject?: string;
}

export interface VisualItem {
  src: string;
  alt: string;
  caption?: string;
  poster?: string; // for kind="video"
  duration?: string; // for kind="video"
}

export interface VisualBlock {
  kind: "image" | "image-grid" | "animated-svg" | "video";
  heading?: string;
  items: VisualItem[];
}

export interface TutorialSection {
  section_id: string;
  title: string;
  content: string;
  visuals?: VisualBlock[];
  examples: string[];
  practice_question: string;
}

export interface TutorialContent {
  unit_id: string;
  title: string;
  sections: TutorialSection[];
  common_mistakes: string[];
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
  /** The server's answer, revealed only after the student has answered. */
  correct_index: number;
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
  subject_breakdown: { subject: string; attempts: number; pass_rate: number }[];
}

// ─── Feedback ────────────────────────────────────────────────────────────────

export type FeedbackRating = "up" | "down";

export interface FeedbackPayload {
  unit_id: string;
  content_type: "lesson" | "quiz" | "experiment" | "tutorial";
  rating: FeedbackRating;
  comment?: string;
}

// ─── Student dashboard (#640) ────────────────────────────────────────────────

export interface SubjectProgress {
  subject: string;
  units_total: number;
  units_completed: number;
  pct: number;
  /** null — not 0 — when nothing has been answered in the subject yet. */
  avg_score: number | null;
}

export interface Standing {
  you: number;
  cohort: number;
  cohort_size: number;
  grade: number;
}

export interface NextUnit {
  unit_id: string;
  title: string;
  subject: string;
  estimated_minutes: number;
}

export interface StudentDashboard {
  summary: {
    units_completed: number;
    quizzes_passed: number;
    current_streak_days: number;
    total_time_minutes: number;
    avg_quiz_score: number;
  };
  subject_progress: SubjectProgress[];
  next_unit: NextUnit | null;
  /** Absent when the cohort is too small to aggregate without disclosure. */
  standing: Standing | null;
  recent_activity: {
    type: string;
    unit_id: string;
    title: string;
    score: number | null;
    at: string;
  }[];
}
