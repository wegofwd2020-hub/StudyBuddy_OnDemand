/**
 * Unit tests for section 2.14 — Subscription Success (`/account/subscription/success`)
 * Covers TC-IDs: STU-46, STU-47
 *
 * Run with:
 *   npm test -- subscription-success-page
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import SubscriptionSuccessPage from "@/app/(student)/account/subscription/success/page";
import { SUCCESS_STRINGS, SUCCESS_HREFS } from "../e2e/data/subscription-success-page";

// ---------------------------------------------------------------------------
// Shared mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

// Mock react-query client (page calls invalidateQueries in useEffect)
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })) };
});

// ---------------------------------------------------------------------------
// STU-46 — Success page renders with icon and confirmation message
// ---------------------------------------------------------------------------

describe("STU-46 — Success page renders", () => {
  it("renders the subscribed heading", () => {
    render(<SubscriptionSuccessPage />);
    expect(
      screen.getByRole("heading", { level: 1, name: SUCCESS_STRINGS.heading }),
    ).toBeInTheDocument();
  });

  it("renders the confirmation body text", () => {
    render(<SubscriptionSuccessPage />);
    expect(screen.getByText(SUCCESS_STRINGS.bodyText)).toBeInTheDocument();
  });

  it("renders a CheckCircle icon (green svg)", () => {
    const { container } = render(<SubscriptionSuccessPage />);
    expect(container.querySelector("svg.text-green-500")).toBeTruthy();
  });

  it("renders both CTA links", () => {
    render(<SubscriptionSuccessPage />);
    expect(
      screen.getByRole("link", { name: SUCCESS_STRINGS.dashboardBtn }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: SUCCESS_STRINGS.subjectsBtn }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// STU-47 — "Go to dashboard" link is present with correct href
// ---------------------------------------------------------------------------

describe("STU-47 — Dashboard link present", () => {
  it("Go to dashboard link href points to /dashboard", () => {
    render(<SubscriptionSuccessPage />);
    const link = screen.getByRole("link", { name: SUCCESS_STRINGS.dashboardBtn });
    expect(link.getAttribute("href")).toBe(SUCCESS_HREFS.dashboard);
  });

  it("Browse subjects link href points to /subjects", () => {
    render(<SubscriptionSuccessPage />);
    const link = screen.getByRole("link", { name: SUCCESS_STRINGS.subjectsBtn });
    expect(link.getAttribute("href")).toBe(SUCCESS_HREFS.subjects);
  });

  it("dashboard href constant is /dashboard", () => {
    expect(SUCCESS_HREFS.dashboard).toBe("/dashboard");
  });

  it("subjects href constant is /subjects", () => {
    expect(SUCCESS_HREFS.subjects).toBe("/subjects");
  });

  it("invalidateQueries is called on mount to refresh subscription cache", async () => {
    const { useQueryClient } = await import("@tanstack/react-query");
    const invalidateQueries = vi.fn();
    vi.mocked(useQueryClient).mockReturnValue({ invalidateQueries } as unknown as ReturnType<typeof useQueryClient>);
    render(<SubscriptionSuccessPage />);
    expect(invalidateQueries).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["subscription"] }),
    );
  });
});
