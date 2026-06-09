import { describe, it, expect } from "vitest";
import {
  computeSetupChecklist,
  nextIncompleteIndex,
  type SetupSignals,
} from "@/lib/school/setup-checklist";

const empty: SetupSignals = {
  teacherCount: 0,
  studentCount: 0,
  activeAdoptionCount: 0,
  classroomCount: 0,
  classroomsWithPackage: 0,
  classroomsWithStudent: 0,
};

describe("computeSetupChecklist (school onboarding wizard)", () => {
  it("has the 6 ordered steps", () => {
    const keys = computeSetupChecklist(empty).map((s) => s.key);
    expect(keys).toEqual([
      "teachers",
      "students",
      "adopt",
      "classroom",
      "assign",
      "enrol",
    ]);
  });

  it("all steps not-done for an empty school; first incomplete is step 0", () => {
    const steps = computeSetupChecklist(empty);
    expect(steps.every((s) => !s.done)).toBe(true);
    expect(nextIncompleteIndex(steps)).toBe(0);
  });

  it("marks each step done from its signal", () => {
    const full: SetupSignals = {
      teacherCount: 2,
      studentCount: 5,
      activeAdoptionCount: 1,
      classroomCount: 1,
      classroomsWithPackage: 1,
      classroomsWithStudent: 1,
    };
    const steps = computeSetupChecklist(full);
    expect(steps.every((s) => s.done)).toBe(true);
    expect(nextIncompleteIndex(steps)).toBe(-1);
  });

  it("points at the assign step when classes exist but none has a package", () => {
    const s: SetupSignals = {
      ...empty,
      teacherCount: 1,
      studentCount: 1,
      activeAdoptionCount: 1,
      classroomCount: 1,
      classroomsWithPackage: 0,
      classroomsWithStudent: 0,
    };
    const steps = computeSetupChecklist(s);
    expect(steps[nextIncompleteIndex(steps)].key).toBe("assign");
  });

  it("every step has a /school deep-link", () => {
    for (const step of computeSetupChecklist(empty)) {
      expect(step.href.startsWith("/school/")).toBe(true);
    }
  });
});
