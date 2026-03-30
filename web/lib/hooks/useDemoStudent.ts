import { useState } from "react";

export interface DemoStudentClaims {
  student_id: string;
  grade: number;
  locale: string;
  demo_account_id: string;
  /** ISO 8601 datetime string — when the demo account expires. */
  demo_expires_at: string;
}

function readDemoClaims(): DemoStudentClaims | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("sb_token");
  if (!token) return null;
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    if (payload.role !== "demo_student") return null;
    return {
      student_id: payload.student_id,
      grade: payload.grade,
      locale: payload.locale,
      demo_account_id: payload.demo_account_id,
      demo_expires_at: payload.demo_expires_at,
    };
  } catch {
    return null;
  }
}

/**
 * Returns the decoded JWT claims for the current demo student session,
 * or null if the current session is not a demo student.
 *
 * Used by DemoBanner (issue #38) to show the expiry countdown and
 * by any component that needs to branch on demo vs regular student.
 */
export function useDemoStudent(): DemoStudentClaims | null {
  const [claims] = useState<DemoStudentClaims | null>(() => readDemoClaims());
  return claims;
}
