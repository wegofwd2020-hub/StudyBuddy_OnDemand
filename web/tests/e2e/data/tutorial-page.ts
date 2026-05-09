/**
 * Test data for section 2.6 — Tutorial Page (`/tutorial/[unit_id]`)
 * Covers TC-IDs: STU-26
 *
 * Auth note: /tutorial/[unit_id] requires a real Auth0 session for E2E.
 * Unit tests mock useQuery / getTutorial() directly via vi.mock.
 *
 * Backend API route for E2E page.route() interception:
 *   GET /api/v1/content/{unit_id}/tutorial → MOCK_TUTORIAL
 */

import type { TutorialContent } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Mock tutorial — 4 sections + common mistakes (STU-26)
// ---------------------------------------------------------------------------

export const MOCK_TUTORIAL: TutorialContent = {
  unit_id: "G8-SCI-001",
  title: "Cell Biology Tutorial",
  sections: [
    {
      section_id: "s1",
      title: "Introduction to Cells",
      content:
        "Every living thing — from bacteria to blue whales — is made of cells. A cell is the smallest unit that can carry out the basic processes of life.",
      examples: [
        "Bacteria are single-celled organisms.",
        "Humans have ~37 trillion cells.",
      ],
      practice_question: "What is the smallest unit of life?",
    },
    {
      section_id: "s2",
      title: "The Cell Membrane",
      content:
        "The cell membrane is a thin, flexible barrier that surrounds the cell. It controls what enters and exits the cell, maintaining the internal environment.",
      examples: ["Oxygen passes through freely; large proteins cannot."],
      practice_question: "Name one molecule that crosses the membrane freely.",
    },
    {
      section_id: "s3",
      title: "The Nucleus",
      content:
        "The nucleus is the control centre of the cell. It contains DNA, which carries the instructions for building proteins and directing cell activities.",
      examples: [],
      practice_question: "Where is DNA stored in a eukaryotic cell?",
    },
    {
      section_id: "s4",
      title: "Mitochondria",
      content:
        "Mitochondria are the powerhouses of the cell. They convert glucose and oxygen into ATP — the energy currency cells use to do work.",
      examples: ["Muscle cells have many mitochondria."],
      practice_question: "What energy molecule do mitochondria produce?",
    },
  ],
  common_mistakes: [
    "Confusing cell membrane with cell wall (only plants have cell walls).",
    "Thinking the nucleus produces ATP — it doesn't; mitochondria do.",
  ],
};

// ---------------------------------------------------------------------------
// Mock tutorial — no common mistakes (edge case)
// ---------------------------------------------------------------------------

export const MOCK_TUTORIAL_NO_SUMMARY: TutorialContent = {
  ...MOCK_TUTORIAL,
  unit_id: "G8-MATH-001",
  title: "Linear Equations Tutorial",
  sections: [
    {
      section_id: "s1",
      title: "What is a Linear Equation?",
      content:
        "A linear equation is an equation where the highest power of the variable is 1. Example: 2x + 3 = 7.",
      examples: ["2x + 3 = 7", "x - 5 = 10"],
      practice_question: "Is x^2 + 1 = 5 a linear equation?",
    },
    {
      section_id: "s2",
      title: "Solving by Isolation",
      content:
        "To solve, perform the same operation on both sides until the variable is alone. For 2x + 3 = 7: subtract 3, then divide by 2.",
      examples: ["2x + 3 = 7  →  2x = 4  →  x = 2"],
      practice_question: "Solve 3x - 4 = 11.",
    },
  ],
  common_mistakes: [],
};

// ---------------------------------------------------------------------------
// Expected UI strings
// ---------------------------------------------------------------------------

export const TUTORIAL_STRINGS = {
  commonMistakesHeading: "Common mistakes",
  takeQuizBtn: "Take Quiz",
  errorMessage: "Could not load tutorial. Please try again.",
} as const;

// ---------------------------------------------------------------------------
// Href helpers
// ---------------------------------------------------------------------------

export function quizHref(unitId: string) {
  return `/quiz/${unitId}`;
}
