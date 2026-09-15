/**
 * Token resolution guard for PATCH /auth/change-password (issue #582).
 *
 * The first-login change-password page must never guess which cached JWT to
 * send by localStorage precedence — a browser that has ever signed in a
 * teacher/school-admin still holds `sb_teacher_token`, so preferring it over
 * `sb_token` silently sends a DIFFERENT ACCOUNT'S token. A provisioned
 * student then can't complete first login (their temp password doesn't match
 * the teacher's hash → 401), and — worse — entering the teacher's own
 * current password there would succeed and silently change the teacher's
 * password while the user believes they're setting a student's.
 *
 * Resolution order:
 *   1. The `account` query param — set explicitly by whichever sign-in path
 *      redirected here, since that code knows exactly which token it just
 *      obtained (see web/app/(public)/signin/page.tsx and
 *      web/components/school/LocalAuthGuard.tsx).
 *   2. Fallback: whichever local-auth session cookie is present
 *      (`sb_local_student_session` vs `sb_local_teacher_session`) — used
 *      only when a redirect source didn't supply the param.
 *
 * Either way, the resolved token's own JWT subject (`student_id` vs
 * `teacher_id`) MUST match the resolved account, or resolution fails closed
 * — the caller must not submit the request. This is the second line of
 * defense: even if the account param or cookie fallback is somehow wrong,
 * a token that doesn't carry the expected subject is never sent.
 */

export type ChangePasswordAccount = "student" | "teacher";

export interface ChangePasswordTokens {
  studentToken: string | null;
  teacherToken: string | null;
}

export interface ResolvedChangePasswordToken {
  token: string;
  account: ChangePasswordAccount;
}

export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split(".")[1];
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

/** Normalizes the `?account=` query param to a known account type, or null. */
export function parseAccountParam(raw: string | null): ChangePasswordAccount | null {
  return raw === "student" || raw === "teacher" ? raw : null;
}

/** Fallback account inference from which local-auth session cookie is present. */
export function accountFromCookies(cookieString: string): ChangePasswordAccount | null {
  if (cookieString.includes("sb_local_student_session=")) return "student";
  if (cookieString.includes("sb_local_teacher_session=")) return "teacher";
  return null;
}

/**
 * Resolve the exact token to send for a change-password request, or `null`
 * if resolution cannot be trusted (caller must fail safe — do not submit,
 * and should route the user back to sign-in).
 */
export function resolveChangePasswordToken(
  accountParam: ChangePasswordAccount | null,
  tokens: ChangePasswordTokens,
  cookieString: string,
): ResolvedChangePasswordToken | null {
  const account = accountParam ?? accountFromCookies(cookieString);
  if (!account) return null;

  const token = account === "student" ? tokens.studentToken : tokens.teacherToken;
  if (!token) return null;

  const payload = decodeJwtPayload(token);
  if (!payload) return null;

  const isStudentToken = typeof payload.student_id === "string";
  const isTeacherToken = typeof payload.teacher_id === "string";

  // The token must carry exactly the subject its localStorage key claims —
  // never both, never neither, and never the other account's.
  if (isStudentToken === isTeacherToken) return null;
  if (account === "student" && !isStudentToken) return null;
  if (account === "teacher" && !isTeacherToken) return null;

  return { token, account };
}
