/**
 * Hook for independent teachers (school_id may be null).
 *
 * Unlike useTeacher(), this does not require school_id in the JWT.
 * Used by Option A (flat-fee) and Option B (revenue-share) teacher pages.
 */
"use client";

import { useEffect, useState } from "react";

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split(".")[1];
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

/**
 * Returns the teacher_id from the stored JWT, or null if not authenticated.
 * Works for both school-affiliated and independent teachers.
 */
export function useTeacherIdFromToken(): string | null {
  const [teacherId, setTeacherId] = useState<string | null>(null);

  useEffect(() => {
    try {
      const token = localStorage.getItem("sb_teacher_token");
      if (!token) return;
      const payload = decodeJwtPayload(token);
      if (!payload) return;
      const tid = payload.teacher_id as string | undefined;
      if (tid) setTeacherId(tid);
    } catch {
      // localStorage not available
    }
  }, []);

  return teacherId;
}
