/**
 * Unit tests for the pure token-resolution guard (issue #582).
 * See web/lib/auth/change-password.ts for the rationale.
 */
import { describe, it, expect } from "vitest";
import {
  accountFromCookies,
  parseAccountParam,
  resolveChangePasswordToken,
} from "@/lib/auth/change-password";

function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

const STUDENT_JWT = makeJwt({ student_id: "stu-1", role: "student" });
const TEACHER_JWT = makeJwt({ teacher_id: "tch-1", school_id: "sch-1", role: "teacher" });

describe("parseAccountParam", () => {
  it("accepts only 'student' or 'teacher'", () => {
    expect(parseAccountParam("student")).toBe("student");
    expect(parseAccountParam("teacher")).toBe("teacher");
    expect(parseAccountParam("admin")).toBeNull();
    expect(parseAccountParam(null)).toBeNull();
  });
});

describe("accountFromCookies", () => {
  it("prefers whichever local-auth session cookie is present", () => {
    expect(accountFromCookies("sb_local_student_session=abc; other=1")).toBe("student");
    expect(accountFromCookies("sb_local_teacher_session=abc")).toBe("teacher");
    expect(accountFromCookies("")).toBeNull();
  });
});

describe("resolveChangePasswordToken — issue #582", () => {
  it("student account param + both tokens cached → resolves the student token", () => {
    const resolved = resolveChangePasswordToken(
      "student",
      { studentToken: STUDENT_JWT, teacherToken: TEACHER_JWT },
      "",
    );
    expect(resolved).toEqual({ token: STUDENT_JWT, account: "student" });
  });

  it("teacher account param + both tokens cached → resolves the teacher token", () => {
    const resolved = resolveChangePasswordToken(
      "teacher",
      { studentToken: STUDENT_JWT, teacherToken: TEACHER_JWT },
      "",
    );
    expect(resolved).toEqual({ token: TEACHER_JWT, account: "teacher" });
  });

  it("no account param → falls back to the session cookie", () => {
    const resolved = resolveChangePasswordToken(
      null,
      { studentToken: STUDENT_JWT, teacherToken: TEACHER_JWT },
      "sb_local_student_session=abc",
    );
    expect(resolved).toEqual({ token: STUDENT_JWT, account: "student" });
  });

  it("account param requested but its token is missing → fails closed", () => {
    expect(
      resolveChangePasswordToken(
        "student",
        { studentToken: null, teacherToken: TEACHER_JWT },
        "",
      ),
    ).toBeNull();
  });

  it("account param says student but the cached token's own JWT subject is a teacher's → fails closed", () => {
    // e.g. a stale/corrupted sb_token, or the wrong value ever written there.
    expect(
      resolveChangePasswordToken(
        "student",
        { studentToken: TEACHER_JWT, teacherToken: TEACHER_JWT },
        "",
      ),
    ).toBeNull();
  });

  it("no account param and no session cookie → fails closed", () => {
    expect(
      resolveChangePasswordToken(
        null,
        { studentToken: STUDENT_JWT, teacherToken: TEACHER_JWT },
        "",
      ),
    ).toBeNull();
  });

  it("malformed token (not decodable) → fails closed", () => {
    expect(
      resolveChangePasswordToken(
        "student",
        { studentToken: "not-a-jwt", teacherToken: TEACHER_JWT },
        "",
      ),
    ).toBeNull();
  });
});
