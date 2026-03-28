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
// Mock tutorial — 4 steps with summary (STU-26)
// ---------------------------------------------------------------------------

export const MOCK_TUTORIAL: TutorialContent = {
  unit_id: "G8-SCI-001",
  title: "Cell Biology Tutorial",
  objective: "Understand the structure and function of cells in living organisms.",
  steps: [
    {
      step: 1,
      title: "Introduction to Cells",
      body: "Every living thing — from bacteria to blue whales — is made of cells. A cell is the smallest unit that can carry out the basic processes of life.",
    },
    {
      step: 2,
      title: "The Cell Membrane",
      body: "The cell membrane is a thin, flexible barrier that surrounds the cell. It controls what enters and exits the cell, maintaining the internal environment.",
    },
    {
      step: 3,
      title: "The Nucleus",
      body: "The nucleus is the control centre of the cell. It contains DNA, which carries the instructions for building proteins and directing cell activities.",
    },
    {
      step: 4,
      title: "Mitochondria",
      body: "Mitochondria are the powerhouses of the cell. They convert glucose and oxygen into ATP — the energy currency cells use to do work.",
    },
  ],
  summary:
    "Cells are the building blocks of life. Key organelles include the membrane (boundary), nucleus (control), and mitochondria (energy).",
};

// ---------------------------------------------------------------------------
// Mock tutorial — no summary (edge case)
// ---------------------------------------------------------------------------

export const MOCK_TUTORIAL_NO_SUMMARY: TutorialContent = {
  ...MOCK_TUTORIAL,
  unit_id: "G8-MATH-001",
  title: "Linear Equations Tutorial",
  objective: "Learn to solve linear equations by isolating the variable.",
  steps: [
    {
      step: 1,
      title: "What is a Linear Equation?",
      body: "A linear equation is an equation where the highest power of the variable is 1. Example: 2x + 3 = 7.",
    },
    {
      step: 2,
      title: "Solving by Isolation",
      body: "To solve, perform the same operation on both sides until the variable is alone. For 2x + 3 = 7: subtract 3, then divide by 2.",
    },
  ],
  summary: "",
};

// ---------------------------------------------------------------------------
// Expected UI strings
// ---------------------------------------------------------------------------

export const TUTORIAL_STRINGS = {
  summaryHeading: "Summary",
  takeQuizBtn:    "Take Quiz",
  errorMessage:   "Could not load tutorial. Please try again.",
} as const;

// ---------------------------------------------------------------------------
// Href helpers
// ---------------------------------------------------------------------------

export function quizHref(unitId: string) {
  return `/quiz/${unitId}`;
}
