/**
 * Unit tests for section 2.11 — Paywall Page (`/paywall`)
 * Covers TC-IDs: STU-34, STU-35
 *
 * Students cannot buy a subscription: individual student billing was removed in
 * migration 0027 (ADR-001), so the school controls access. The page used to
 * advertise "$9.99/month" with a Subscribe CTA pointing at endpoints that
 * returned 404 (#604). These tests now pin the opposite: no price, no purchase
 * CTA, and a clear statement of who to ask.
 *
 * Run with:
 *   npm test -- paywall-page
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import PaywallPage from "@/app/(student)/paywall/page";
import { PAYWALL_STRINGS, PAYWALL_HREFS } from "../e2e/data/paywall-page";

// ---------------------------------------------------------------------------
// Shared mocks
// ---------------------------------------------------------------------------

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

// ---------------------------------------------------------------------------
// STU-34 — Paywall page explains that the school controls access
// ---------------------------------------------------------------------------

describe("STU-34 — Paywall page renders", () => {
  it("renders the page title as H1", () => {
    render(<PaywallPage />);
    expect(
      screen.getByRole("heading", { level: 1, name: PAYWALL_STRINGS.title }),
    ).toBeInTheDocument();
  });

  it("renders the paywall message paragraph", () => {
    render(<PaywallPage />);
    expect(screen.getByText(PAYWALL_STRINGS.paywallMsg)).toBeInTheDocument();
  });

  it("renders a Lock icon (svg) in the amber badge", () => {
    const { container } = render(<PaywallPage />);
    expect(container.querySelector("svg")).toBeTruthy();
  });

  it("tells the student who can restore their access", () => {
    render(<PaywallPage />);
    expect(screen.getByText(PAYWALL_STRINGS.help)).toBeInTheDocument();
  });

  it("renders the Back to Dashboard link", () => {
    render(<PaywallPage />);
    expect(
      screen.getByRole("link", { name: PAYWALL_STRINGS.backToDashboard }),
    ).toBeInTheDocument();
  });

  it("offers no purchase CTA — a student cannot buy a subscription", () => {
    render(<PaywallPage />);
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(1);
    expect(links[0].getAttribute("href")).toBe(PAYWALL_HREFS.dashboardHref);
  });

  it("advertises no price", () => {
    const { container } = render(<PaywallPage />);
    expect(container.textContent).not.toMatch(/\$\d/);
  });
});

// ---------------------------------------------------------------------------
// STU-35 — the only CTA returns to the dashboard
// ---------------------------------------------------------------------------

describe("STU-35 — the only CTA returns to the dashboard", () => {
  it("Back to Dashboard href points to /dashboard", () => {
    render(<PaywallPage />);
    const dashLink = screen.getByRole("link", { name: PAYWALL_STRINGS.backToDashboard });
    expect(dashLink.getAttribute("href")).toBe(PAYWALL_HREFS.dashboardHref);
  });

  it("dashboard href is /dashboard", () => {
    expect(PAYWALL_HREFS.dashboardHref).toBe("/dashboard");
  });
});
