/**
 * Test data for section 2.5 — Quiz Page (`/quiz/[unit_id]`)
 * Covers TC-IDs: STU-19, STU-20, STU-21, STU-22, STU-23, STU-24
 *
 * Auth note: /quiz/[unit_id] requires a real Auth0 session for E2E.
 * Unit tests mock useQuiz() and progress API calls directly.
 *
 * Backend API routes for E2E page.route() interception:
 *   GET  /api/v1/content/{unit_id}/quiz           → MOCK_BACKEND_QUIZ_RESPONSE (BackendQuizResponse shape)
 *   POST /api/v1/progress/session                 → { session_id }
 *   POST /api/v1/progress/session/{id}/answer     → MOCK_ANSWER_CORRECT | MOCK_ANSWER_WRONG
 *   POST /api/v1/progress/session/{id}/end        → { session_id, score, total_questions, passed, ... }
 *
 * Note: getQuiz() in lib/api/content.ts maps BackendQuizResponse → QuizContent.
 * MOCK_BACKEND_QUIZ_RESPONSE is the raw backend shape that must be returned by the stub.
 * MOCK_QUIZ is the frontend QuizContent shape (used for assertion values only).
 */

import type { QuizContent, AnswerResponse, SessionEndResponse } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Mock quiz backend response — BackendQuizResponse shape (stub for GET /quiz)
// getQuiz() in content.ts maps this to QuizContent. set_number=1 → title
// becomes "Quiz — Set 1".
// ---------------------------------------------------------------------------

export const MOCK_BACKEND_QUIZ_RESPONSE = {
  unit_id: "G8-SCI-001",
  set_number: 1,
  language: "en",
  total_questions: 3,
  estimated_duration_minutes: 5,
  passing_score: 0.7,
  generated_at: "2026-01-01T00:00:00Z",
  model: "claude-sonnet-4-6",
  content_version: 1,
  questions: [
    {
      question_id: "G8-SCI-001-Q1",
      question_text: "What is the basic unit of all living organisms?",
      question_type: "multiple_choice",
      options: [
        { option_id: "A", text: "Atom" },
        { option_id: "B", text: "Cell" },
        { option_id: "C", text: "Tissue" },
        { option_id: "D", text: "Organ" },
      ],
      correct_option: "B",
      explanation:
        "The cell is the basic structural and functional unit of all living organisms.",
      difficulty: "easy",
    },
    {
      question_id: "G8-SCI-001-Q2",
      question_text: "Which organelle contains the cell's DNA?",
      question_type: "multiple_choice",
      options: [
        { option_id: "A", text: "Mitochondria" },
        { option_id: "B", text: "Ribosome" },
        { option_id: "C", text: "Nucleus" },
        { option_id: "D", text: "Vacuole" },
      ],
      correct_option: "C",
      explanation: "The nucleus houses the cell's genetic material (DNA).",
      difficulty: "easy",
    },
    {
      question_id: "G8-SCI-001-Q3",
      question_text: "What do mitochondria produce?",
      question_type: "multiple_choice",
      options: [
        { option_id: "A", text: "Protein" },
        { option_id: "B", text: "DNA" },
        { option_id: "C", text: "ATP (energy)" },
        { option_id: "D", text: "Cell membrane" },
      ],
      correct_option: "C",
      explanation:
        "Mitochondria are the powerhouse of the cell, producing ATP through cellular respiration.",
      difficulty: "medium",
    },
  ],
} as const;

/** Display title rendered by getQuiz() from the backend response above. */
export const MOCK_QUIZ_DISPLAY_TITLE = "Quiz — Set 1";

// ---------------------------------------------------------------------------
// Mock quiz frontend shape — QuizContent (used for assertion values only, not
// as a stub response — stubs must use MOCK_BACKEND_QUIZ_RESPONSE)
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
