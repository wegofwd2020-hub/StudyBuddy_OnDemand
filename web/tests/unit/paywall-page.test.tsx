/**
 * Unit tests for section 2.11 — Paywall Page (`/paywall`)
 * Covers TC-IDs: STU-34, STU-35
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
// STU-34 — Paywall page renders with upgrade prompt
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

  it("renders the monthly price text", () => {
    render(<PaywallPage />);
    expect(screen.getByText(new RegExp(`\\${PAYWALL_STRINGS.monthlyPrice}`))).toBeInTheDocument();
  });

  it("renders the annual price text", () => {
    const { container } = render(<PaywallPage />);
    // Text is split across nodes inside the <p> — check combined textContent
    const para = Array.from(container.querySelectorAll("p")).find((p) =>
      p.textContent?.includes(PAYWALL_STRINGS.annualPrice),
    );
    expect(para).toBeTruthy();
  });

  it("renders the annual savings i18n text", () => {
    render(<PaywallPage />);
    expect(screen.getByText(new RegExp(PAYWALL_STRINGS.annualSavings))).toBeInTheDocument();
  });

  it("renders the Back to Dashboard link", () => {
    render(<PaywallPage />);
    expect(
      screen.getByRole("link", { name: PAYWALL_STRINGS.backToDashboard }),
    ).toBeInTheDocument();
  });

  it("renders the subscribe CTA link", () => {
    render(<PaywallPage />);
    // Link text contains subscribe_btn key + price suffix
    const links = screen.getAllByRole("link");
    const upgradeLink = links.find((l) =>
      l.textContent?.includes(PAYWALL_STRINGS.subscribeBtn),
    );
    expect(upgradeLink).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// STU-35 — Upgrade button navigates to /account/subscription
// ---------------------------------------------------------------------------

describe("STU-35 — Upgrade button href", () => {
  it("subscribe CTA href points to /account/subscription", () => {
    render(<PaywallPage />);
    const links = screen.getAllByRole("link");
    const upgradeLink = links.find((l) =>
      l.textContent?.includes(PAYWALL_STRINGS.subscribeBtn),
    );
    expect(upgradeLink?.getAttribute("href")).toBe(PAYWALL_HREFS.upgradeHref);
  });

  it("Back to Dashboard href points to /dashboard", () => {
    render(<PaywallPage />);
    const dashLink = screen.getByRole("link", { name: PAYWALL_STRINGS.backToDashboard });
    expect(dashLink.getAttribute("href")).toBe(PAYWALL_HREFS.dashboardHref);
  });

  it("upgrade href is /account/subscription", () => {
    expect(PAYWALL_HREFS.upgradeHref).toBe("/account/subscription");
  });

  it("dashboard href is /dashboard", () => {
    expect(PAYWALL_HREFS.dashboardHref).toBe("/dashboard");
  });

  it("both CTAs are present simultaneously", () => {
    render(<PaywallPage />);
    const links = screen.getAllByRole("link");
    const hasUpgrade = links.some((l) => l.getAttribute("href") === PAYWALL_HREFS.upgradeHref);
    const hasDashboard = links.some((l) => l.getAttribute("href") === PAYWALL_HREFS.dashboardHref);
    expect(hasUpgrade).toBe(true);
    expect(hasDashboard).toBe(true);
  });
});
