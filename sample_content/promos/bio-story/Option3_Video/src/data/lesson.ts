/**
 * Photosynthesis lesson content — Grade 11 Biology.
 *
 * Authored to be technically correct and concise. Section bodies are
 * pitched two grades below G11 (target ~G9 reading level), matching
 * the StudyBuddy lesson pipeline's standard reading-level target.
 */
import type { LessonSection } from "../components/app/LessonPage";
import type { QuizQuestion } from "../components/app/QuizPage";
import type { TutorialSection } from "../components/app/TutorialPage";
import type { UnitTile } from "../components/app/DashboardPage";

export const PHOTOSYNTHESIS_LESSON = {
  unitId: "G11-BIO-004",
  title: "Photosynthesis",
  sections: [
    {
      heading: "The big picture",
      body:
        "Plants use sunlight to turn carbon dioxide and water into glucose and oxygen. " +
        "The summary equation is: 6 CO₂ + 6 H₂O + light → C₆H₁₂O₆ + 6 O₂. " +
        "It happens in two stages — light reactions and the Calvin cycle — both inside the chloroplast.",
    },
    {
      heading: "Stage 1 — light reactions",
      body:
        "Inside the thylakoid membranes, chlorophyll absorbs light energy. " +
        "Water molecules are split, releasing oxygen as a by-product. " +
        "The captured energy is stored in two molecules — ATP and NADPH — which power the next stage.",
    },
    {
      heading: "Stage 2 — the Calvin cycle",
      body:
        "In the stroma, the enzyme RuBisCO grabs CO₂ from the air and locks it onto a 5-carbon sugar (RuBP). " +
        "Using the ATP and NADPH from stage 1, the cycle runs three turns to produce one molecule of glucose. " +
        "No light is needed directly here — that's why it's sometimes called the dark reactions.",
    },
  ] as LessonSection[],
  keyPoints: [
    "Photosynthesis turns CO₂ + H₂O + light into glucose + O₂.",
    "Light reactions happen on thylakoid membranes; the Calvin cycle happens in the stroma.",
    "The light reactions produce ATP and NADPH, which power the Calvin cycle.",
    "Chlorophyll absorbs red and blue light strongly — green light is reflected, which is why plants look green.",
  ],
} as const;

export const PHOTOSYNTHESIS_QUIZ: QuizQuestion = {
  prompt: "Which colour of light does chlorophyll absorb LEAST?",
  options: [
    "Red",
    "Blue",
    "Green",
    "Violet",
  ],
  correctIndex: 2,
  explanation:
    "Chlorophyll absorbs red and blue strongly but reflects green light. That reflected green is what reaches your eyes — it's why plants look green to us.",
};

export const PHOTOSYNTHESIS_TUTORIAL: {
  title: string;
  sections: TutorialSection[];
  commonMistakes: string[];
} = {
  title: "Tracing energy through photosynthesis",
  sections: [
    {
      title: "Step 1 — light hits chlorophyll",
      content:
        "A photon of red or blue light strikes a chlorophyll molecule in the thylakoid membrane. The energy boosts an electron to a higher energy level.",
      examples: [
        "Photon (red, ~680 nm) → chlorophyll a → high-energy electron",
        "Photon (blue, ~440 nm) → chlorophyll a → high-energy electron",
      ],
    },
    {
      title: "Step 2 — electron transport chain",
      content:
        "The high-energy electron flows down a chain of proteins. As it moves, the energy is used to pump protons (H⁺) across the membrane, which drives ATP synthesis. Water donates electrons to replace those that left chlorophyll — splitting H₂O and releasing O₂.",
      practiceQuestion:
        "If a plant is starved of water, which two outputs of photosynthesis will drop the fastest?",
    },
    {
      title: "Step 3 — Calvin cycle uses the energy",
      content:
        "ATP and NADPH from step 2 fuel the Calvin cycle in the stroma. RuBisCO catalyses the first step — fixing CO₂ onto a 5-carbon sugar. Three full turns of the cycle yield one new glucose molecule.",
    },
  ],
  commonMistakes: [
    "Saying photosynthesis happens in mitochondria — it happens in CHLOROPLASTS.",
    "Confusing 'dark reactions' with happening at night — they happen any time, just don't need light directly.",
    "Forgetting that O₂ comes from H₂O, not from CO₂.",
  ],
};

export const DASHBOARD_TILES: UnitTile[] = [
  { unitId: "G11-BIO-002", title: "The cell — structure and function", status: "done" },
  { unitId: "G11-BIO-003", title: "Cellular respiration", status: "done" },
  { unitId: "G11-BIO-004", title: "Photosynthesis", status: "active" },
  { unitId: "G11-BIO-005", title: "DNA structure and replication", status: "locked" },
  { unitId: "G11-BIO-006", title: "Mendelian genetics", status: "locked" },
  { unitId: "G11-BIO-007", title: "Evolution and natural selection", status: "locked" },
];

export const PERSONA = {
  name: "Daniel M.",
  initials: "DM",
  grade: "Grade 11 · Science (Biology)",
  greeting: "Welcome back, Daniel",
  subjectName: "Grade 11 — Biology",
} as const;
