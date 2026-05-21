import { describe, it, expect } from "vitest";
import {
  claimsFromPayload,
  canManageCurriculum,
  hasCapability,
  type TeacherClaims,
} from "@/lib/hooks/useTeacher";

const base = { teacher_id: "t1", school_id: "s1" };

describe("claimsFromPayload — capabilities (issue #358)", () => {
  it("exposes capabilities array from the payload", () => {
    const c = claimsFromPayload({ ...base, role: "teacher", capabilities: ["curriculum_mgmt"] });
    expect(c?.capabilities).toEqual(["curriculum_mgmt"]);
    expect(c?.role).toBe("teacher");
  });

  it("defaults capabilities to [] when absent (coercion must not drop it)", () => {
    const c = claimsFromPayload({ ...base, role: "teacher" });
    expect(c?.capabilities).toEqual([]);
    expect(c?.role).toBe("teacher");
  });

  it("returns null when required ids are missing", () => {
    expect(claimsFromPayload({ role: "teacher" })).toBeNull();
    expect(claimsFromPayload(null)).toBeNull();
  });
});

describe("canManageCurriculum", () => {
  const make = (role: TeacherClaims["role"], caps: string[]): TeacherClaims => ({
    ...base,
    role,
    capabilities: caps,
    first_login: false,
  });

  it("true for school_admin (implicit superset)", () => {
    expect(canManageCurriculum(make("school_admin", []))).toBe(true);
  });
  it("true for any curriculum capability", () => {
    expect(canManageCurriculum(make("teacher", ["curriculum.review"]))).toBe(true);
    expect(canManageCurriculum(make("teacher", ["curriculum.commission"]))).toBe(true);
  });
  it("false for a plain teacher", () => {
    expect(canManageCurriculum(make("teacher", []))).toBe(false);
    expect(canManageCurriculum(null)).toBe(false);
  });
});

describe("hasCapability — gate isolation", () => {
  const make = (caps: string[]): TeacherClaims => ({
    ...base,
    role: "teacher",
    capabilities: caps,
    first_login: false,
  });

  it("exact grant clears only its gate", () => {
    const t = make(["curriculum.commission"]);
    expect(hasCapability(t, "curriculum.commission")).toBe(true);
    expect(hasCapability(t, "curriculum.review")).toBe(false);
  });

  it("umbrella clears both gates", () => {
    const t = make(["curriculum_mgmt"]);
    expect(hasCapability(t, "curriculum.commission")).toBe(true);
    expect(hasCapability(t, "curriculum.review")).toBe(true);
  });

  it("school_admin clears both gates implicitly", () => {
    const t: TeacherClaims = { ...base, role: "school_admin", capabilities: [], first_login: false };
    expect(hasCapability(t, "curriculum.commission")).toBe(true);
    expect(hasCapability(t, "curriculum.review")).toBe(true);
  });
});
