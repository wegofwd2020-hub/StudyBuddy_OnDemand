/**
 * #764 — the enrolment invite link, and what it tells a teacher.
 *
 * Venki asked whether "Share this link with students. They will be prompted to
 * sign in and confirm enrolment" was clear. Checking the flow showed the wording
 * was also untrue in two ways:
 *
 *   - There is nothing to confirm: opening the link while signed in enrols the
 *     student into the school immediately.
 *   - A signed-out student WAS prompted to sign in — and then always landed on
 *     /dashboard. The link was forgotten and they were never enrolled.
 *
 * The page now sends a signed-out student to sign-in with the link as `next`, and
 * sign-in returns them there. `next` is only honoured for a same-site path, so
 * the parameter cannot be used to bounce a freshly signed-in user off-site.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { safeNextPath, studentSignInDestination } from "@/lib/auth/safe-next";

// ── safeNextPath ──────────────────────────────────────────────────────────────

describe("#764 — safeNextPath only accepts same-site paths", () => {
  it("accepts an absolute path on this site", () => {
    expect(safeNextPath("/enrol/ABC123")).toBe("/enrol/ABC123");
  });

  it.each([
    ["protocol-relative", "//evil.example.com/x"],
    ["backslash trick", "/\\evil.example.com"],
    ["absolute URL", "https://evil.example.com/enrol/x"],
    ["javascript scheme", "javascript:alert(1)"],
    ["relative path", "enrol/ABC123"],
    ["empty", ""],
  ])("rejects %s", (_label, value) => {
    expect(safeNextPath(value)).toBeNull();
  });

  it("rejects a missing value", () => {
    expect(safeNextPath(null)).toBeNull();
    expect(safeNextPath(undefined)).toBeNull();
  });
});

// ── where a student goes after sign-in ────────────────────────────────────────

describe("#764 — student sign-in destination", () => {
  it("returns to the enrolment link when one was passed", () => {
    expect(studentSignInDestination("/enrol/ABC123")).toBe("/enrol/ABC123");
  });

  it("falls back to the dashboard without a safe next", () => {
    expect(studentSignInDestination(null)).toBe("/dashboard");
    expect(studentSignInDestination("//evil.example.com")).toBe("/dashboard");
  });
});

// ── the enrol page itself ─────────────────────────────────────────────────────

const mockReplace = vi.fn();
const mockConfirmEnrolment = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: vi.fn(() => ({ token: "ABC123" })),
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
}));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));
vi.mock("@/lib/api/school", () => ({
  confirmEnrolment: (...args: unknown[]) => mockConfirmEnrolment(...args),
}));

import EnrolConfirmPage from "@/app/(public)/enrol/[token]/page";

describe("#764 — a signed-out student is sent to sign in and brought back", () => {
  beforeEach(() => {
    mockReplace.mockClear();
    mockConfirmEnrolment.mockReset();
    localStorage.clear();
  });

  it("redirects to sign-in with the link as next, without calling the API", async () => {
    render(<EnrolConfirmPage />);

    await waitFor(() =>
      expect(mockReplace).toHaveBeenCalledWith("/signin?next=%2Fenrol%2FABC123"),
    );
    expect(mockConfirmEnrolment).not.toHaveBeenCalled();
  });

  it("enrols straight away when the student is already signed in", async () => {
    localStorage.setItem("sb_token", "token");
    mockConfirmEnrolment.mockResolvedValue({ school_name: "ABC School" });

    render(<EnrolConfirmPage />);

    await waitFor(() => expect(mockConfirmEnrolment).toHaveBeenCalledWith("ABC123"));
    expect(mockReplace).not.toHaveBeenCalled();
  });
});
