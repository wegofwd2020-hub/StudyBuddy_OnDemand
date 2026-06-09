/**
 * Guided "Set up your school" checklist (issue: school_admin onboarding wizard).
 *
 * Pure, data-driven step computation so it can be unit-tested without rendering.
 * Each step's `done` is derived from signals the school portal already exposes
 * (teacher/student/adoption/classroom counts) — no new backend endpoints.
 */

export interface SetupSignals {
  teacherCount: number;
  studentCount: number;
  activeAdoptionCount: number;
  classroomCount: number;
  /** classrooms that have ≥1 curriculum package assigned */
  classroomsWithPackage: number;
  /** classrooms that have ≥1 student enrolled */
  classroomsWithStudent: number;
}

export interface SetupStep {
  key: string;
  title: string;
  description: string;
  href: string;
  done: boolean;
}

/**
 * The ordered onboarding sequence (Path A — Adopt). Order matters: each step
 * unlocks the next, and the UI highlights the first not-yet-done step.
 */
export function computeSetupChecklist(s: SetupSignals): SetupStep[] {
  return [
    {
      key: "teachers",
      title: "Add your teachers",
      description:
        "Provision teacher accounts. Each gets a login and a first-time password.",
      href: "/school/teachers",
      done: s.teacherCount > 0,
    },
    {
      key: "students",
      title: "Add your students",
      description: "Provision student accounts so they can be enrolled into classes.",
      href: "/school/students",
      done: s.studentCount > 0,
    },
    {
      key: "adopt",
      title: "Adopt a curriculum",
      description:
        "Browse the catalog and adopt a curriculum into your school's library.",
      href: "/school/catalog",
      done: s.activeAdoptionCount > 0,
    },
    {
      key: "classroom",
      title: "Create a class",
      description: "Create a classroom for a grade/section you teach.",
      href: "/school/classrooms",
      done: s.classroomCount > 0,
    },
    {
      key: "assign",
      title: "Assign a curriculum to a class",
      description: "Open a class and pick one of your adopted curricula to assign.",
      href: "/school/classrooms",
      done: s.classroomsWithPackage > 0,
    },
    {
      key: "enrol",
      title: "Enrol students in a class",
      description: "Add students to a class so they see its curriculum when they log in.",
      href: "/school/classrooms",
      done: s.classroomsWithStudent > 0,
    },
  ];
}

/** Index of the first not-done step, or -1 when everything is complete. */
export function nextIncompleteIndex(steps: SetupStep[]): number {
  return steps.findIndex((step) => !step.done);
}
