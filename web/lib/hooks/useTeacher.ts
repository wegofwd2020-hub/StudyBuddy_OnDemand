/**
 * Decode the teacher JWT stored in localStorage and expose key claims.
 * All school portal components use this hook to get school_id, teacher_id, and role.
 */
"use client";

import { useState, useEffect } from "react";

export interface TeacherClaims {
  teacher_id: string;
  school_id: string;
  role: "teacher" | "school_admin";
  /** Additive curriculum-management capabilities (issue #358). Empty for teachers
   *  with no grants. school_admin is an implicit superset (see canManageCurriculum). */
  capabilities: string[];
  /** True when logged in with a system-issued default password — client must redirect to change-password */
  first_login: boolean;
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split(".")[1];
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

/** Pure claims-extraction from a decoded JWT payload. Exported for unit testing. */
export function claimsFromPayload(
  payload: Record<string, unknown> | null,
): TeacherClaims | null {
  if (!payload) return null;
  const teacher_id = payload.teacher_id as string | undefined;
  const school_id = payload.school_id as string | undefined;
  const role = payload.role as string | undefined;
  if (!teacher_id || !school_id) return null;
  const rawCaps = payload.capabilities;
  return {
    teacher_id,
    school_id,
    role: (role === "school_admin" ? "school_admin" : "teacher") as TeacherClaims["role"],
    // Never let the role coercion drop capabilities — default to [] when absent.
    capabilities: Array.isArray(rawCaps) ? (rawCaps as string[]) : [],
    first_login: Boolean(payload.first_login),
  };
}

function readTeacherClaims(): TeacherClaims | null {
  try {
    const token = localStorage.getItem("sb_teacher_token");
    if (!token) return null;
    return claimsFromPayload(decodeJwtPayload(token));
  } catch {
    return null;
  }
}

/** True if the teacher may manage curriculum at all (holds any curriculum
 *  capability, or is a school_admin superset). Drives the top-bar menu. */
export function canManageCurriculum(teacher: TeacherClaims | null): boolean {
  if (!teacher) return false;
  if (teacher.role === "school_admin") return true;
  return teacher.capabilities.some((c) => c.startsWith("curriculum"));
}

/** True if the teacher holds the school_admin superset role. Drives the
 *  Administration menu's User Management section (issue #415). */
export function isSchoolAdmin(teacher: TeacherClaims | null): boolean {
  return teacher?.role === "school_admin";
}

/** True if the teacher can clear a specific gate (exact capability, the
 *  curriculum_mgmt umbrella, or school_admin superset). */
export function hasCapability(
  teacher: TeacherClaims | null,
  capability: "curriculum.commission" | "curriculum.review",
): boolean {
  if (!teacher) return false;
  if (teacher.role === "school_admin") return true;
  return (
    teacher.capabilities.includes(capability) ||
    teacher.capabilities.includes("curriculum_mgmt")
  );
}

export function useTeacher(): TeacherClaims | null {
  const [teacher, setTeacher] = useState<TeacherClaims | null>(null);

  useEffect(() => {
    setTeacher(readTeacherClaims());
  }, []);

  return teacher;
}
