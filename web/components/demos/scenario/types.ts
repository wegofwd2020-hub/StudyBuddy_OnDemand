// Shared types for the scenario builder and players

export type QuizFormat = "true_false" | "single_choice" | "multiple_choice";
export type Language = "en" | "fr" | "es";
export type Difficulty = "beginner" | "intermediate" | "advanced";
export type AnimationStyle = "realistic" | "animated";

export interface ScenarioCharacter {
  id: string; // "user1", "user2", …
  name: string;
  role_label: string; // "Sales Director — Vendor"
  org?: string;
  gender: "male" | "female" | "non-binary";
  ethnicity?: string;
  approx_age?: number;
  animation_style: AnimationStyle;
  voice_id?: string; // D-ID / Azure Neural voice
  background?: string; // D-ID virtual background key
}

export interface DialogTurn {
  id: string; // uuid — stable key for React lists / drag-drop
  speaker: string; // character id
  text: string;
}

export interface QuizOption {
  id: string;
  text: string;
}

export interface QuizQuestion {
  id: string;
  question: string;
  format: QuizFormat;
  options?: QuizOption[]; // single_choice | multiple_choice
  correct_answer: boolean | string | string[]; // bool | option id | option ids
  explanation: string;
}

export interface ScenarioDraft {
  // Step 1 — metadata
  title: string;
  domain: string;
  language: Language;
  difficulty: Difficulty;
  target_seniority: string;
  description: string;

  // Step 2 — characters
  characters: ScenarioCharacter[];

  // Step 3 — dialog
  dialog: DialogTurn[];

  // Step 4 — quiz
  quiz_questions: QuizQuestion[];
}

// Wire-format written to JSON — extends draft with generation metadata
export interface ScenarioFile extends Omit<ScenarioDraft, "dialog"> {
  scenario_id: string;
  content_source: "human_authored" | "ai_generated" | "ai_assisted";
  // dialog stripped of internal id field
  dialog: Omit<DialogTurn, "id">[];
  // legacy single-question compat — derived from quiz_questions[0] on save
  quiz?: {
    question: string;
    format: QuizFormat;
    correct_answer: boolean | string | string[];
    explanation: string;
    options?: QuizOption[];
  };
  video_clips?: VideoClip[] | null;
  generated_at: string;
  model: string;
  content_version: number;
}

export interface VideoClip {
  turn_index: number;
  speaker: string;
  video_url: string;
  duration_seconds: number;
  status: "ready" | "pending" | "error";
}

// Voices available through D-ID / Azure Neural
export const VOICES_EN = [
  { id: "en-US-JennyNeural", label: "Jenny (US Female)" },
  { id: "en-US-GuyNeural", label: "Guy (US Male)" },
  { id: "en-US-AriaNeural", label: "Aria (US Female)" },
  { id: "en-GB-SoniaNeural", label: "Sonia (UK Female)" },
  { id: "en-GB-RyanNeural", label: "Ryan (UK Male)" },
] as const;

export const VOICES_FR = [
  { id: "fr-FR-DeniseNeural", label: "Denise (FR Female)" },
  { id: "fr-FR-HenriNeural", label: "Henri (FR Male)" },
] as const;

export const VOICES_ES = [
  { id: "es-ES-ElviraNeural", label: "Elvira (ES Female)" },
  { id: "es-ES-AlvaroNeural", label: "Alvaro (ES Male)" },
] as const;

export const VOICES_BY_LANG: Record<Language, readonly { id: string; label: string }[]> =
  {
    en: VOICES_EN,
    fr: VOICES_FR,
    es: VOICES_ES,
  };

export const COMPLIANCE_DOMAINS = [
  "Contract Law",
  "FCPA / Anti-Bribery",
  "AML / KYC",
  "GDPR / Data Privacy",
  "HR Compliance",
  "Health & Safety",
  "Information Security",
  "Financial Regulations",
  "Code of Conduct",
  "Export Controls",
  "ESG / Sustainability",
  "Other",
] as const;

export const BACKGROUNDS = [
  { id: "office", label: "Office" },
  { id: "boardroom", label: "Boardroom" },
  { id: "lobby", label: "Lobby" },
  { id: "outdoor", label: "Outdoor" },
  { id: "none", label: "Plain background" },
] as const;

export function emptyDraft(): ScenarioDraft {
  return {
    title: "",
    domain: "",
    language: "en",
    difficulty: "intermediate",
    target_seniority: "",
    description: "",
    characters: [],
    dialog: [],
    quiz_questions: [],
  };
}

export function emptyCharacter(index: number): ScenarioCharacter {
  return {
    id: `user${index + 1}`,
    name: "",
    role_label: "",
    org: "",
    gender: "female",
    ethnicity: "",
    approx_age: undefined,
    animation_style: "realistic",
    voice_id: "en-US-JennyNeural",
    background: "office",
  };
}

export function emptyQuestion(): QuizQuestion {
  return {
    id: crypto.randomUUID(),
    question: "",
    format: "true_false",
    correct_answer: true,
    explanation: "",
  };
}
