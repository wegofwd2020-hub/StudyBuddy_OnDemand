/**
 * Alkenes lesson content — Grade 11 Chemistry.
 *
 * Authored to be technically correct and concise. Section bodies are
 * pitched two grades below G11 (target ~G9 reading level) for in-app
 * realism, since the StudyBuddy lesson pipeline targets readability
 * 1–2 grades below the student's grade.
 */
import type { LessonSection } from "../components/app/LessonPage";
import type { QuizQuestion } from "../components/app/QuizPage";
import type { TutorialSection } from "../components/app/TutorialPage";
import type { UnitTile } from "../components/app/DashboardPage";

export const ALKENES_LESSON = {
  unitId: "G11-CHEM-007",
  title: "Reactions of Alkenes",
  sections: [
    {
      heading: "What is an alkene?",
      body:
        "An alkene is a hydrocarbon with at least one carbon–carbon double bond (C=C). " +
        "The simplest alkene is ethene, CH₂=CH₂. Because the double bond holds extra electron density, alkenes are far more reactive than alkanes — they're the workhorse starting material for plastics, fuels, and many drugs.",
    },
    {
      heading: "Electrophilic addition",
      body:
        "Alkenes react with electrophiles by breaking the weaker π-bond and adding two new groups across the C=C. " +
        "Common partners: hydrogen (with a Pd catalyst) gives an alkane; HBr gives a haloalkane; bromine gives a vicinal dibromide; water (with H₂SO₄) gives an alcohol.",
    },
    {
      heading: "Markovnikov's rule",
      body:
        "When an unsymmetrical electrophile like HBr adds to an unsymmetrical alkene, the H attaches to the carbon that already carries more H atoms, and the heavier fragment lands on the more substituted carbon. " +
        "Easy mnemonic: the rich get richer.",
    },
  ] as LessonSection[],
  keyPoints: [
    "Alkenes contain a C=C double bond, making them more reactive than alkanes.",
    "Electrophilic addition is the defining reaction class — π-bond breaks, two new groups attach.",
    "Markovnikov's rule predicts regiochemistry: the more substituted carbon gets the heavier group.",
    "Alkenes are starting materials for plastics, alcohols, and haloalkanes.",
  ],
} as const;

export const ALKENES_QUIZ: QuizQuestion = {
  prompt: "When HBr is added to propene (CH₃-CH=CH₂), the major product is:",
  options: [
    "1-bromopropane",
    "2-bromopropane",
    "Propan-1-ol",
    "Propane",
  ],
  correctIndex: 1,
  explanation:
    "Markovnikov's rule. The H attaches to the CH₂= carbon (which already has 2 H's), so Br lands on the middle carbon — giving 2-bromopropane.",
};

export const ALKENES_TUTORIAL: {
  title: string;
  sections: TutorialSection[];
  commonMistakes: string[];
} = {
  title: "Predicting alkene products step by step",
  sections: [
    {
      title: "Step 1 — identify the C=C and the electrophile",
      content:
        "Look for the double bond. Identify which atom of the electrophile is δ⁺ (the partial-positive end). For HBr, that's the H.",
      examples: [
        "Propene + HBr → the δ⁺ end is H",
        "Ethene + Cl₂ → here Cl₂ is symmetric, so both ends matter equally",
      ],
    },
    {
      title: "Step 2 — apply Markovnikov where applicable",
      content:
        "On unsymmetrical alkenes, ask: which carbon already has more H's? That's where the H of HBr lands; the Br goes to the more substituted carbon.",
      practiceQuestion:
        "What's the major product when HBr adds to but-1-ene (CH₃-CH₂-CH=CH₂)?",
    },
    {
      title: "Step 3 — write the new structure",
      content:
        "Replace the π-bond with a single bond between the two carbons. Attach the two new groups — one per carbon — according to step 2.",
    },
  ],
  commonMistakes: [
    "Forgetting that Markovnikov only applies to UNSYMMETRICAL alkenes.",
    "Adding both H's to the same carbon — the rule splits one H per carbon.",
    "Reversing the H and Br — H always goes to the carbon with more H atoms already.",
  ],
};

export const DASHBOARD_TILES: UnitTile[] = [
  { unitId: "G11-CHEM-005", title: "Hydrocarbons — naming and nomenclature", status: "done" },
  { unitId: "G11-CHEM-006", title: "Reactions of alkanes", status: "done" },
  { unitId: "G11-CHEM-007", title: "Reactions of alkenes", status: "active" },
  { unitId: "G11-CHEM-008", title: "Aromatic compounds — benzene", status: "locked" },
  { unitId: "G11-CHEM-009", title: "Functional groups — alcohols", status: "locked" },
  { unitId: "G11-CHEM-010", title: "Carbonyl compounds", status: "locked" },
];

export const PERSONA = {
  name: "Aditi K.",
  initials: "AK",
  grade: "Grade 11 · Science (Chemistry)",
  greeting: "Welcome back, Aditi",
  subjectName: "Grade 11 — Chemistry",
} as const;
