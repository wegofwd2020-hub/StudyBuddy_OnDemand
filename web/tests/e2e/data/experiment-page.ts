/**
 * Test data for section 2.7 — Experiment Page (`/experiment/[unit_id]`)
 * Covers TC-IDs: STU-27, STU-28
 *
 * Auth note: /experiment/[unit_id] requires a real Auth0 session for E2E.
 * Unit tests mock ExperimentRenderer props directly.
 *
 * STU-28 (non-lab 404): the backend returns HTTP 404 when getExperiment() is
 * called for a non-lab unit. The page renders an error state — tested here
 * by mocking useQuery isError=true.
 *
 * Backend API route for E2E page.route() interception:
 *   GET /api/v1/content/{unit_id}/experiment → MOCK_EXPERIMENT (lab unit)
 *   GET /api/v1/content/{unit_id}/experiment → 404 (non-lab unit)
 */

import type { ExperimentContent } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Mock experiment — lab unit with materials, safety notes, steps, outcome
// (STU-27)
// ---------------------------------------------------------------------------

export const MOCK_EXPERIMENT: ExperimentContent = {
  unit_id: "G8-SCI-001",
  title: "Observing Cell Structure",
  materials: [
    "Microscope",
    "Glass slides",
    "Cover slips",
    "Onion skin sample",
    "Iodine solution",
    "Dropper",
  ],
  steps: [
    {
      step: 1,
      instruction: "Peel a thin layer of onion skin and place it flat on a glass slide.",
    },
    {
      step: 2,
      instruction: "Add one drop of iodine solution to stain the cells and improve visibility.",
    },
    {
      step: 3,
      instruction: "Carefully lower a cover slip at an angle to avoid air bubbles.",
    },
    {
      step: 4,
      instruction: "Place the slide on the microscope stage and focus under low power (4×) first.",
    },
    {
      step: 5,
      instruction: "Switch to higher magnification (10×) and identify the cell wall, nucleus, and cytoplasm.",
    },
  ],
  safety_notes: [
    "Handle glass slides with care — edges are sharp.",
    "Iodine stains clothing; wear a lab apron.",
    "Do not touch your face after handling iodine.",
  ],
  expected_outcome:
    "You should see rectangular plant cells with a clear cell wall, stained nucleus, and cytoplasm visible under magnification.",
};

// ---------------------------------------------------------------------------
// Mock experiment — no safety notes (edge case)
// ---------------------------------------------------------------------------

export const MOCK_EXPERIMENT_NO_SAFETY: ExperimentContent = {
  ...MOCK_EXPERIMENT,
  unit_id: "G8-SCI-002",
  title: "Simple Pendulum Timing",
  safety_notes: [],
};

// ---------------------------------------------------------------------------
// Mock experiment — no expected outcome (edge case)
// ---------------------------------------------------------------------------

export const MOCK_EXPERIMENT_NO_OUTCOME: ExperimentContent = {
  ...MOCK_EXPERIMENT,
  unit_id: "G8-SCI-003",
  title: "Acid-Base Indicator Test",
  expected_outcome: "",
};

// ---------------------------------------------------------------------------
// Expected UI strings
// (keys match useTranslations("experiment_screen") — mock returns key as-is)
// ---------------------------------------------------------------------------

export const EXPERIMENT_STRINGS = {
  materialsHeading:       "materials_heading",
  safetyHeading:          "safety_heading",
  stepsHeading:           "steps_heading",
  expectedOutcomeHeading: "expected_outcome_heading",
  errorMessage:           "Could not load experiment. Please try again.",
  takeQuizBtn:            "Take Quiz",
} as const;

// ---------------------------------------------------------------------------
// Non-lab unit identifier (STU-28)
// ---------------------------------------------------------------------------

export const NON_LAB_UNIT_ID = "G8-MATH-001";
