/**
 * tests/e2e/helpers/tokens.ts
 *
 * Shared helpers for building mock JWTs and dev-session cookies
 * used across all persona-based E2E tests.
 *
 * No real secrets are used — these tokens are only valid against
 * the mock backend stubs wired up in each test file.
 */

// ---------------------------------------------------------------------------
// JWT factories
// ---------------------------------------------------------------------------

function encodeJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString(
    "base64url",
  );
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.sig`;
}

/** Student internal JWT — stored in localStorage as `sb_token`. */
export function makeStudentToken(
  studentId = "test-student-001",
  grade = 8,
  locale = "en",
): string {
  return encodeJwt({
    student_id: studentId,
    grade,
    locale,
    role: "student",
    exp: 9_999_999_999,
  });
}

/** Teacher internal JWT — stored in localStorage as `sb_teacher_token`. */
export function makeTeacherToken(
  teacherId = "test-teacher-001",
  schoolId = "test-school-001",
  role: "teacher" | "school_admin" = "school_admin",
): string {
  return encodeJwt({
    teacher_id: teacherId,
    school_id: schoolId,
    role,
    exp: 9_999_999_999,
  });
}

/** Admin internal JWT — stored in localStorage as `sb_admin_token`. */
export function makeAdminToken(
  role: "super_admin" | "developer" | "tester" | "product_admin" = "super_admin",
): string {
  return encodeJwt({
    admin_id: "test-admin-001",
    role,
    exp: 9_999_999_999,
  });
}

// ---------------------------------------------------------------------------
// Dev-session cookie
// ---------------------------------------------------------------------------

/**
 * Returns the value for the `sb_dev_session` cookie consumed by
 * `lib/dev-session.ts` on the server side.  This satisfies the
 * server-component layout auth check (auth0.getSession() returns null
 * with fake env vars; getDevSession() reads this cookie instead).
 */
export function makeDevSessionCookie(name: string, email: string): string {
  const payload = JSON.stringify({ name, email });
  return Buffer.from(payload).toString("base64url");
}

/** Cookie descriptor ready to pass to `page.context().addCookies()`. */
export function devSessionCookie(
  name = "Test Student",
  email = "student@test.invalid",
  domain = "localhost",
) {
  return {
    name: "sb_dev_session",
    value: makeDevSessionCookie(name, email),
    domain,
    path: "/",
    expires: -1,
    httpOnly: false,
    secure: false,
    sameSite: "Lax" as const,
  };
}
