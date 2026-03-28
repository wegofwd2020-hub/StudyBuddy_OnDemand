/**
 * Test data for section 2.4 — Lesson Page (`/lesson/[unit_id]`)
 * Covers TC-IDs: STU-15, STU-16, STU-17, STU-18
 *
 * Auth note: /lesson/[unit_id] requires a real Auth0 session for E2E.
 * Unit tests mock useLesson() directly.
 *
 * STU-18 (paywall): the HTTP 402 → /paywall redirect is handled by the
 * global axios response interceptor in lib/api/client.ts — tested in
 * tests/unit/lesson-page.test.tsx as an interceptor unit test.
 *
 * Backend API routes for E2E page.route() interception:
 *   GET /api/v1/content/{unit_id}/lesson → MOCK_LESSON_WITH_AUDIO | MOCK_LESSON_NO_AUDIO
 *   GET /api/v1/content/{unit_id}/lesson/audio → MOCK_AUDIO_URL_RESPONSE
 */

import type { LessonContent, AudioUrlResponse } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Mock lesson — with audio + key points (STU-15, STU-16, STU-17)
// ---------------------------------------------------------------------------

export const MOCK_LESSON_WITH_AUDIO: LessonContent = {
  unit_id: "G8-SCI-001",
  title: "Cell Biology",
  grade: 8,
  subject: "Science",
  lang: "en",
  has_audio: true,
  sections: [
    {
      heading: "What is a Cell?",
      body: "A cell is the basic structural and functional unit of all living organisms.",
    },
    {
      heading: "Cell Structure",
      body: "Cells contain a nucleus, cytoplasm, and a cell membrane that controls what enters and exits.",
    },
    {
      heading: "Types of Cells",
      body: "There are two main types: prokaryotic cells (no nucleus) and eukaryotic cells (with nucleus).",
    },
  ],
  key_points: [
    "All living things are made of cells.",
    "The nucleus contains the cell's DNA.",
    "Mitochondria produce energy for the cell.",
  ],
};

// ---------------------------------------------------------------------------
// Mock lesson — without audio (STU-15, STU-17 only — no AudioPlayer rendered)
// ---------------------------------------------------------------------------

export const MOCK_LESSON_NO_AUDIO: LessonContent = {
  ...MOCK_LESSON_WITH_AUDIO,
  unit_id: "G8-MATH-001",
  title: "Linear Equations",
  subject: "Mathematics",
  has_audio: false,
  sections: [
    {
      heading: "Introduction",
      body: "A linear equation is an equation that makes a straight line when graphed.",
    },
  ],
  key_points: ["The standard form is ax + b = c.", "Solve by isolating the variable."],
};

// ---------------------------------------------------------------------------
// Mock audio URL response (STU-16)
// ---------------------------------------------------------------------------

export const MOCK_AUDIO_URL_RESPONSE: AudioUrlResponse = {
  url: "https://cdn.studybuddy.example.com/audio/G8-SCI-001-en.mp3",
  expires_in: 900,
};

// ---------------------------------------------------------------------------
// Expected UI strings
// ---------------------------------------------------------------------------

export const LESSON_STRINGS = {
  takeQuizBtn:  "Take Quiz",
  tutorialBtn:  "Tutorial",
  keyPoints:    "Key Points",
  errorMessage: "Could not load lesson. Please try again.",
  playAudio:    "Play audio",
  pauseAudio:   "Pause audio",
  audioProgress:"Audio progress",
} as const;

// ---------------------------------------------------------------------------
// STU-17 — CTA href helpers
// ---------------------------------------------------------------------------

export function quizHref(unitId: string)     { return `/quiz/${unitId}`; }
export function tutorialHref(unitId: string) { return `/tutorial/${unitId}`; }
