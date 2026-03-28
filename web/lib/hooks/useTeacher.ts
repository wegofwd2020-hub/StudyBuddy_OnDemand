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

export function useTeacher(): TeacherClaims | null {
  const [teacher, setTeacher] = useState<TeacherClaims | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("sb_teacher_token");
    if (!token) return;
    const payload = decodeJwtPayload(token);
    if (!payload) return;
    const teacher_id = payload.teacher_id as string | undefined;
    const school_id = payload.school_id as string | undefined;
    const role = payload.role as string | undefined;
    if (!teacher_id || !school_id) return;
    setTeacher({
      teacher_id,
      school_id,
      role: (role === "school_admin" ? "school_admin" : "teacher") as TeacherClaims["role"],
    });
  }, []);

  return teacher;
}
