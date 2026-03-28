/**
 * Unit tests for section 3.13 — Digest Settings (`/school/digest`)
 * Covers TC-IDs: SCH-22, SCH-23
 *
 * Run with:
 *   npm test -- digest-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import DigestSettingsPage from "@/app/(school)/school/digest/page";
import { MOCK_TEACHER, DIGEST_STRINGS, TEST_EMAIL } from "../e2e/data/digest-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => MOCK_TEACHER),
}));

const mockSubscribeDigest = vi.fn();
vi.mock("@/lib/api/reports", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/reports")>();
  return { ...actual, subscribeDigest: (...args: unknown[]) => mockSubscribeDigest(...args) };
});

// ---------------------------------------------------------------------------
// SCH-22 — Digest settings form renders
// ---------------------------------------------------------------------------

describe("SCH-22 — Digest settings form renders", () => {
  it("renders the page heading", () => {
    render(<DigestSettingsPage />);
    expect(
      screen.getByRole("heading", { name: DIGEST_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders the digest settings card heading", () => {
    render(<DigestSettingsPage />);
    expect(screen.getByText(DIGEST_STRINGS.cardHeading)).toBeInTheDocument();
  });

  it("renders the email address field", () => {
    render(<DigestSettingsPage />);
    expect(screen.getByLabelText(DIGEST_STRINGS.emailLabel)).toBeInTheDocument();
  });

  it("renders the timezone selector", () => {
    render(<DigestSettingsPage />);
    expect(screen.getByLabelText(DIGEST_STRINGS.timezoneLabel)).toBeInTheDocument();
  });

  it("renders the Save settings button", () => {
    render(<DigestSettingsPage />);
    expect(screen.getByRole("button", { name: DIGEST_STRINGS.saveBtn })).toBeInTheDocument();
  });

  it("Save settings button is disabled when email is empty", () => {
    render(<DigestSettingsPage />);
    expect(screen.getByRole("button", { name: DIGEST_STRINGS.saveBtn })).toBeDisabled();
  });

  it("Save settings button is enabled when email is filled", () => {
    render(<DigestSettingsPage />);
    const emailInput = screen.getByLabelText(DIGEST_STRINGS.emailLabel);
    fireEvent.change(emailInput, { target: { value: TEST_EMAIL } });
    expect(screen.getByRole("button", { name: DIGEST_STRINGS.saveBtn })).not.toBeDisabled();
  });

  it("renders the digest enabled toggle label by default", () => {
    render(<DigestSettingsPage />);
    expect(screen.getByText(DIGEST_STRINGS.digestEnabled)).toBeInTheDocument();
  });

  it("renders the digest info card", () => {
    render(<DigestSettingsPage />);
    expect(screen.getByText(DIGEST_STRINGS.digestInfoHeading)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SCH-23 — Subscribe saves preferences
// ---------------------------------------------------------------------------

describe("SCH-23 — Subscribe saves preferences", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSubscribeDigest.mockResolvedValue({});
  });

  it("shows 'Saving…' while saving", async () => {
    mockSubscribeDigest.mockReturnValue(new Promise(() => {}));
    render(<DigestSettingsPage />);
    fireEvent.change(screen.getByLabelText(DIGEST_STRINGS.emailLabel), {
      target: { value: TEST_EMAIL },
    });
    fireEvent.click(screen.getByRole("button", { name: DIGEST_STRINGS.saveBtn }));
    expect(await screen.findByRole("button", { name: DIGEST_STRINGS.savingBtn })).toBeInTheDocument();
  });

  it("shows 'Saved' confirmation after successful save", async () => {
    render(<DigestSettingsPage />);
    fireEvent.change(screen.getByLabelText(DIGEST_STRINGS.emailLabel), {
      target: { value: TEST_EMAIL },
    });
    fireEvent.click(screen.getByRole("button", { name: DIGEST_STRINGS.saveBtn }));
    await waitFor(() =>
      expect(screen.getByText(DIGEST_STRINGS.savedConfirm)).toBeInTheDocument(),
    );
  });

  it("calls subscribeDigest with correct arguments", async () => {
    render(<DigestSettingsPage />);
    fireEvent.change(screen.getByLabelText(DIGEST_STRINGS.emailLabel), {
      target: { value: TEST_EMAIL },
    });
    fireEvent.click(screen.getByRole("button", { name: DIGEST_STRINGS.saveBtn }));
    await waitFor(() => expect(mockSubscribeDigest).toHaveBeenCalledTimes(1));
    expect(mockSubscribeDigest).toHaveBeenCalledWith(
      MOCK_TEACHER.school_id,
      TEST_EMAIL,
      expect.any(String), // timezone
      true,               // enabled
    );
  });

  it("shows error message when save fails", async () => {
    mockSubscribeDigest.mockRejectedValue(new Error("network error"));
    render(<DigestSettingsPage />);
    fireEvent.change(screen.getByLabelText(DIGEST_STRINGS.emailLabel), {
      target: { value: TEST_EMAIL },
    });
    fireEvent.click(screen.getByRole("button", { name: DIGEST_STRINGS.saveBtn }));
    expect(
      await screen.findByText("Failed to save digest settings. Please try again."),
    ).toBeInTheDocument();
  });
});
