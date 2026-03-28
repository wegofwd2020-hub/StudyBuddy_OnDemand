/**
 * Unit tests for section 2.15 — Enrolment Confirmation (`/enrol/[token]`)
 * Covers TC-IDs: STU-48, STU-49, STU-50
 *
 * Run with:
 *   npm test -- enrol-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import EnrolConfirmPage from "@/app/(student)/enrol/[token]/page";
import {
  VALID_TOKEN,
  MOCK_ENROL_SUCCESS,
  MOCK_ENROL_ERROR_DETAIL,
  ENROL_STRINGS,
  ENROL_HREFS,
} from "../e2e/data/enrol-page";

// ---------------------------------------------------------------------------
// Shared mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  useParams: vi.fn(() => ({ token: VALID_TOKEN })),
}));

const mockConfirmEnrolment = vi.fn();
vi.mock("@/lib/api/school", () => ({
  confirmEnrolment: (...args: unknown[]) => mockConfirmEnrolment(...args),
}));

// ---------------------------------------------------------------------------
// STU-48 — Valid token shows success with school name
// ---------------------------------------------------------------------------

describe("STU-48 — Valid token shows success", () => {
  beforeEach(() => {
    mockConfirmEnrolment.mockResolvedValue(MOCK_ENROL_SUCCESS);
  });

  it("renders the enrolled heading after success", async () => {
    render(<EnrolConfirmPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { level: 1, name: ENROL_STRINGS.successHeading }),
      ).toBeInTheDocument(),
    );
  });

  it("renders the school name in the success message", async () => {
    render(<EnrolConfirmPage />);
    await waitFor(() =>
      expect(
        screen.getByText(MOCK_ENROL_SUCCESS.school_name),
      ).toBeInTheDocument(),
    );
  });

  it("renders success body text containing enrolled phrase", async () => {
    render(<EnrolConfirmPage />);
    await waitFor(() =>
      expect(
        screen.getByText(new RegExp(ENROL_STRINGS.successBodyPart)),
      ).toBeInTheDocument(),
    );
  });

  it("renders green CheckCircle icon on success", async () => {
    const { container } = render(<EnrolConfirmPage />);
    await waitFor(() =>
      expect(container.querySelector("svg.text-green-500")).toBeTruthy(),
    );
  });

  it("renders Go to dashboard link on success", async () => {
    render(<EnrolConfirmPage />);
    await waitFor(() => {
      const link = screen.getByRole("link", { name: ENROL_STRINGS.dashboardBtn });
      expect(link).toBeInTheDocument();
      expect(link.getAttribute("href")).toBe(ENROL_HREFS.dashboard);
    });
  });

  it("calls confirmEnrolment with the token from params", async () => {
    render(<EnrolConfirmPage />);
    await waitFor(() => expect(mockConfirmEnrolment).toHaveBeenCalledWith(VALID_TOKEN));
  });
});

// ---------------------------------------------------------------------------
// STU-49 — Invalid token shows error message
// ---------------------------------------------------------------------------

describe("STU-49 — Invalid token shows error", () => {
  beforeEach(() => {
    mockConfirmEnrolment.mockRejectedValue({
      response: { data: { detail: MOCK_ENROL_ERROR_DETAIL } },
    });
  });

  it("renders the error heading after failure", async () => {
    render(<EnrolConfirmPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { level: 1, name: ENROL_STRINGS.errorHeading }),
      ).toBeInTheDocument(),
    );
  });

  it("renders the error detail message", async () => {
    render(<EnrolConfirmPage />);
    await waitFor(() =>
      expect(screen.getByText(MOCK_ENROL_ERROR_DETAIL)).toBeInTheDocument(),
    );
  });

  it("renders red XCircle icon on error", async () => {
    const { container } = render(<EnrolConfirmPage />);
    await waitFor(() =>
      expect(container.querySelector("svg.text-red-400")).toBeTruthy(),
    );
  });

  it("renders Back to dashboard link on error", async () => {
    render(<EnrolConfirmPage />);
    await waitFor(() => {
      const link = screen.getByRole("link", { name: ENROL_STRINGS.backBtn });
      expect(link).toBeInTheDocument();
      expect(link.getAttribute("href")).toBe(ENROL_HREFS.dashboard);
    });
  });

  it("falls back to default error message when no detail in response", async () => {
    mockConfirmEnrolment.mockRejectedValue(new Error("network error"));
    render(<EnrolConfirmPage />);
    await waitFor(() =>
      expect(screen.getByText(ENROL_STRINGS.defaultError)).toBeInTheDocument(),
    );
  });

  it("does not render success heading on error", async () => {
    render(<EnrolConfirmPage />);
    await waitFor(() =>
      expect(
        screen.queryByRole("heading", { name: ENROL_STRINGS.successHeading }),
      ).toBeNull(),
    );
  });
});

// ---------------------------------------------------------------------------
// STU-50 — Loading skeleton shown while API resolves
// ---------------------------------------------------------------------------

describe("STU-50 — Loading skeleton during confirmation", () => {
  it("shows skeleton while confirmEnrolment is pending", () => {
    mockConfirmEnrolment.mockReturnValue(new Promise(() => {})); // never resolves
    const { container } = render(<EnrolConfirmPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("hides skeleton once success state is reached", async () => {
    mockConfirmEnrolment.mockResolvedValue(MOCK_ENROL_SUCCESS);
    const { container } = render(<EnrolConfirmPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: ENROL_STRINGS.successHeading }),
      ).toBeInTheDocument(),
    );
    expect(container.querySelector("[data-slot='skeleton']")).toBeNull();
  });

  it("hides skeleton once error state is reached", async () => {
    mockConfirmEnrolment.mockRejectedValue(new Error("bad token"));
    const { container } = render(<EnrolConfirmPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: ENROL_STRINGS.errorHeading }),
      ).toBeInTheDocument(),
    );
    expect(container.querySelector("[data-slot='skeleton']")).toBeNull();
  });
});
