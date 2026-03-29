/**
 * Test data for section 2.5 — Quiz Page (`/quiz/[unit_id]`)
 * Covers TC-IDs: STU-19, STU-20, STU-21, STU-22, STU-23, STU-24
 *
 * Auth note: /quiz/[unit_id] requires a real Auth0 session for E2E.
 * Unit tests mock useQuiz() and progress API calls directly.
 *
 * Backend API routes for E2E page.route() interception:
 *   GET  /api/v1/content/{unit_id}/quiz     → MOCK_QUIZ
 *   POST /api/v1/progress/session/start     → MOCK_SESSION_START
 *   POST /api/v1/progress/answer            → MOCK_ANSWER_CORRECT | MOCK_ANSWER_WRONG
 *   POST /api/v1/progress/session/end       → MOCK_SESSION_END_PASSED | MOCK_SESSION_END_FAILED
 */

import type { QuizContent, AnswerResponse, SessionEndResponse } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Mock quiz — 3 questions, correct_index varies (STU-19..STU-23)
// ---------------------------------------------------------------------------

export const MOCK_QUIZ: QuizContent = {
  unit_id: "G8-SCI-001",
  title: "Cell Biology Quiz",
  pass_threshold: 0.7,
  questions: [
    {
      index: 0,
      question: "What is the basic unit of all living organisms?",
      options: ["Atom", "Cell", "Tissue", "Organ"],
      correct_index: 1,
      explanation:
        "The cell is the basic structural and functional unit of all living organisms.",
    },
    {
      index: 1,
      question: "Which organelle contains the cell's DNA?",
      options: ["Mitochondria", "Ribosome", "Nucleus", "Vacuole"],
      correct_index: 2,
      explanation: "The nucleus houses the cell's genetic material (DNA).",
    },
    {
      index: 2,
      question: "What do mitochondria produce?",
      options: ["Protein", "DNA", "ATP (energy)", "Cell membrane"],
      correct_index: 2,
      explanation:
        "Mitochondria are the powerhouse of the cell, producing ATP through cellular respiration.",
    },
  ],
};

// ---------------------------------------------------------------------------
// Mock session start (STU-24)
// ---------------------------------------------------------------------------

export const MOCK_SESSION_ID = "sess-test-001";

// ---------------------------------------------------------------------------
// Mock answer responses (STU-21, STU-22)
// ---------------------------------------------------------------------------

export const MOCK_ANSWER_CORRECT: AnswerResponse = {
  correct: true,
  explanation:
    "The cell is the basic structural and functional unit of all living organisms.",
};

export const MOCK_ANSWER_WRONG: AnswerResponse = {
  correct: false,
  explanation:
    "The cell is the basic structural and functional unit of all living organisms.",
};

// ---------------------------------------------------------------------------
// Mock session end responses (STU-23)
// ---------------------------------------------------------------------------

export const MOCK_SESSION_END_PASSED: SessionEndResponse = {
  score: 3,
  total: 3,
  passed: true,
  attempt_number: 1,
};

export const MOCK_SESSION_END_FAILED: SessionEndResponse = {
  score: 1,
  total: 3,
  passed: false,
  attempt_number: 2,
};

// ---------------------------------------------------------------------------
// Expected UI strings
// ---------------------------------------------------------------------------

export const QUIZ_STRINGS = {
  submitBtn: "Submit answer",
  nextBtn: "Next question",
  seeResultsBtn: "See results",
  passedHeading: "passed_heading",
  tryAgainHeading: "try_again_heading",
  backToCurriculum: "back_to_curriculum_btn",
  tryAgainBtn: "try_again_btn",
} as const;
