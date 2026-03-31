import { useState, useEffect } from "react";

export interface DemoTeacherClaims {
  teacher_id: string;
  demo_account_id: string;
  /** ISO 8601 datetime string — when the demo account expires. */
  demo_expires_at: string;
}

function readDemoTeacherClaims(): DemoTeacherClaims | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("sb_teacher_token");
  if (!token) return null;
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    if (payload.role !== "demo_teacher") return null;
    return {
      teacher_id: payload.teacher_id,
      demo_account_id: payload.demo_account_id,
      demo_expires_at: payload.demo_expires_at,
    };
  } catch {
    return null;
  }
}

/**
 * Returns the decoded JWT claims for the current demo teacher session,
 * or null if the current session is not a demo teacher.
 *
 * Used by DemoTeacherBanner to show the expiry countdown and
 * by any component that needs to branch on demo vs regular teacher.
 */
export function useDemoTeacher(): DemoTeacherClaims | null {
  const [claims, setClaims] = useState<DemoTeacherClaims | null>(null);

  useEffect(() => {
    setClaims(readDemoTeacherClaims());
  }, []);

  return claims;
}
