/**
 * Regression tests for issue #582 — the first-login change-password page must
 * send the JWT belonging to the account that is actually changing its
 * password. It must never guess by localStorage precedence: a browser that
 * has ever signed in a teacher/school-admin still holds `sb_teacher_token`,
 * and preferring it over `sb_token` silently sends a DIFFERENT ACCOUNT'S
 * token — a provisioned student can't set their first password, and (worse)
 * entering the teacher's own current password there would succeed and
 * silently change the teacher's password instead.
 *
 * Run with: docker compose exec -T web npx vitest run change-password-token
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChangePasswordPage from "@/app/(public)/school/change-password/page";
import * as authApi from "@/lib/api/auth";

const mockPush = vi.fn();
const mockReplace = vi.fn();
let searchParamsValue = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({ push: mockPush, replace: mockReplace })),
  useSearchParams: vi.fn(() => searchParamsValue),
}));

vi.mock("@/lib/api/auth", async () => {
  const actual = await vi.importActual<typeof authApi>("@/lib/api/auth");
  return { ...actual, changePassword: vi.fn() };
});

/** Build a minimal unsigned JWT — only the payload matters for these tests. */
function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

const STUDENT_JWT = makeJwt({ student_id: "stu-1", role: "student", first_login: true });
const TEACHER_JWT = makeJwt({
  teacher_id: "tch-1",
  school_id: "sch-1",
  role: "school_admin",
  first_login: true,
});

async function fillAndSubmit(currentPassword = "TempPassw0rd!!") {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Current password"), currentPassword);
  await user.type(screen.getByLabelText("New password"), "BrandNewPassw0rd!!");
  await user.type(screen.getByLabelText("Confirm new password"), "BrandNewPassw0rd!!");
  await user.click(screen.getByRole("button", { name: /set new password/i }));
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  document.cookie.split(";").forEach((c) => {
    const name = c.split("=")[0]?.trim();
    if (name) document.cookie = `${name}=; path=/; Max-Age=0`;
  });
  searchParamsValue = new URLSearchParams();
  (authApi.changePassword as ReturnType<typeof vi.fn>).mockResolvedValue({
    token: "new-token",
    refresh_token: "new-refresh",
    role: "student",
  });
});

describe("issue #582 — change-password token resolution", () => {
  it("student flow: both tokens present, account=student in the URL → the student's token is used", async () => {
    localStorage.setItem("sb_token", STUDENT_JWT);
    localStorage.setItem("sb_teacher_token", TEACHER_JWT);
    searchParamsValue = new URLSearchParams("required=1&account=student");

    render(<ChangePasswordPage />);
    await fillAndSubmit();

    await waitFor(() => expect(authApi.changePassword).toHaveBeenCalled());
    expect(authApi.changePassword).toHaveBeenCalledWith(
      STUDENT_JWT,
      expect.objectContaining({ current_password: "TempPassw0rd!!" }),
    );
  });

  it("teacher flow: both tokens present, account=teacher in the URL → the teacher's token is used", async () => {
    localStorage.setItem("sb_token", STUDENT_JWT);
    localStorage.setItem("sb_teacher_token", TEACHER_JWT);
    searchParamsValue = new URLSearchParams("required=1&account=teacher");
    (authApi.changePassword as ReturnType<typeof vi.fn>).mockResolvedValue({
      token: "new-token",
      refresh_token: "new-refresh",
      role: "teacher",
    });

    render(<ChangePasswordPage />);
    await fillAndSubmit();

    await waitFor(() => expect(authApi.changePassword).toHaveBeenCalled());
    expect(authApi.changePassword).toHaveBeenCalledWith(TEACHER_JWT, expect.anything());
  });

  it("mismatched token: account=student but sb_token actually holds a teacher JWT → the request is never sent, and the user is bounced to sign-in instead of silently changing the wrong account", async () => {
    // Simulates a corrupted/foreign token under the student key — the guard
    // must refuse to trust localStorage-key naming alone.
    localStorage.setItem("sb_token", TEACHER_JWT);
    localStorage.setItem("sb_teacher_token", TEACHER_JWT);
    searchParamsValue = new URLSearchParams("required=1&account=student");

    render(<ChangePasswordPage />);

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/signin"));
    expect(authApi.changePassword).not.toHaveBeenCalled();
  });
});
