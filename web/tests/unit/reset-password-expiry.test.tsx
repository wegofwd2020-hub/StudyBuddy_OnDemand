/**
 * The reset page must not offer a form for a link that cannot work.
 *
 * It used to gate purely on the token being PRESENT in the URL, never on it
 * being valid, so an expired link rendered "Set new password" identically to a
 * live one and the expiry surfaced only after the user had typed a new password
 * twice and pressed the button. A tester reported that twice as "the reset link
 * still worked hours later" — the link did not work, but nothing on screen said
 * so until the very end.
 *
 * The backend was never wrong here, which is why an API-level probe found
 * nothing: an expired token has always been rejected at POST /auth/reset-password.
 * The defect was entirely in what the page showed before that point.
 *
 * Run with: docker compose exec -T web npx vitest run reset-password-expiry
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import ResetPasswordPage from "@/app/(public)/reset-password/page";
import * as authApi from "@/lib/api/auth";

let searchParamsValue = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({ push: vi.fn(), replace: vi.fn() })),
  useSearchParams: vi.fn(() => searchParamsValue),
}));

// House pattern (see paywall-page.test.tsx): translations echo their key, so
// translated strings are matched here as `password_label`, `set_new_password`
// and so on. Literals in the JSX — "Confirm password", "This link has expired" —
// are matched as written.
vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api/auth", async () => {
  const actual = await vi.importActual<typeof authApi>("@/lib/api/auth");
  return { ...actual, checkResetToken: vi.fn(), resetPassword: vi.fn() };
});

const checkResetToken = vi.mocked(authApi.checkResetToken);
const resetPassword = vi.mocked(authApi.resetPassword);

beforeEach(() => {
  vi.clearAllMocks();
  searchParamsValue = new URLSearchParams();
});

describe("reset-password page — expired links", () => {
  it("shows the expired notice instead of the form when the token is dead", async () => {
    searchParamsValue = new URLSearchParams("token=stale-token");
    checkResetToken.mockResolvedValue(false);

    render(<ResetPasswordPage />);

    await screen.findByText(/this link has expired/i);
    // The form is the thing that must be absent — its presence is the bug.
    expect(screen.queryByLabelText(/confirm password/i)).toBeNull();
    expect(screen.getByRole("link", { name: /request a new link/i })).toHaveAttribute(
      "href",
      "/reset-password",
    );
  });

  it("still renders the form for a live token", async () => {
    // The negative direction. Without this, a page hardcoded to always show
    // "expired" passes the test above while breaking every real reset.
    searchParamsValue = new URLSearchParams("token=good-token");
    checkResetToken.mockResolvedValue(true);

    render(<ResetPasswordPage />);

    await screen.findByLabelText(/confirm password/i);
    expect(screen.queryByText(/this link has expired/i)).toBeNull();
  });

  it("never shows the form before the check answers", async () => {
    // Rendering the form and swapping it for the expired notice a moment later
    // is the same flash of a dead form this change exists to remove.
    searchParamsValue = new URLSearchParams("token=slow-token");
    let settle: (v: boolean) => void = () => {};
    checkResetToken.mockReturnValue(
      new Promise<boolean>((resolve) => {
        settle = resolve;
      }),
    );

    render(<ResetPasswordPage />);

    expect(screen.queryByLabelText(/confirm password/i)).toBeNull();
    expect(screen.getByText(/checking your link/i)).toBeInTheDocument();

    settle(false);
    await screen.findByText(/this link has expired/i);
  });

  it("does not check anything when there is no token", async () => {
    // The no-token branch is the "email me a link" form. Asking the server to
    // validate an absent token would be a wasted round-trip on every visit.
    render(<ResetPasswordPage />);

    await screen.findByLabelText("email_label");
    expect(checkResetToken).not.toHaveBeenCalled();
  });

  it("switches to the expired screen when the token lapses mid-form", async () => {
    // The TTL runs from issue, not from page load, so a token can die while the
    // user is typing. An inline "reset failed" sentence offers no way forward;
    // the expired screen carries the request-a-new-link action.
    searchParamsValue = new URLSearchParams("token=lapsing-token");
    checkResetToken.mockResolvedValueOnce(true).mockResolvedValueOnce(false);
    resetPassword.mockRejectedValue(new Error("400"));

    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await screen.findByLabelText(/confirm password/i);
    await user.type(screen.getByLabelText("password_label"), "BrandNewPassw0rd!!");
    await user.type(screen.getByLabelText(/confirm password/i), "BrandNewPassw0rd!!");
    await user.click(screen.getByRole("button", { name: "set_new_password" }));

    await waitFor(() => {
      expect(screen.getByText(/this link has expired/i)).toBeInTheDocument();
    });
  });
});
