/**
 * Unit tests for section 2.13 — Subscription Page (`/account/subscription`)
 * Covers TC-IDs: STU-42, STU-43, STU-44, STU-45
 *
 * Run with:
 *   npm test -- subscription-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SubscriptionPage from "@/app/(student)/account/subscription/page";
import {
  MOCK_SUB_FREE,
  MOCK_SUB_TRIAL,
  MOCK_SUB_ACTIVE_MONTHLY,
  MOCK_SUB_ACTIVE_ANNUAL,
  MOCK_SUB_CANCELLED,
  STRIPE_CHECKOUT_URL,
  STRIPE_PORTAL_URL,
  SUBSCRIPTION_STRINGS,
  PLAN_FEATURES,
} from "../e2e/data/subscription-page";

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

// Mock react-query client
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })) };
});

const mockUseSubscription = vi.fn();
const mockCreateCheckout = vi.fn();
const mockGetBillingPortal = vi.fn();
const mockCancelSub = vi.fn();

vi.mock("@/lib/hooks/useSubscription", () => ({
  useSubscription: () => mockUseSubscription(),
  trialDaysRemaining: (date: string | null) => {
    if (!date) return null;
    const diff = new Date(date).getTime() - Date.now();
    if (diff <= 0) return 0;
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  },
}));

vi.mock("@/lib/api/subscription", () => ({
  createCheckout: (...a: unknown[]) => mockCreateCheckout(...a),
  getBillingPortalUrl: (...a: unknown[]) => mockGetBillingPortal(...a),
  cancelSubscription: (...a: unknown[]) => mockCancelSub(...a),
}));

// Capture window.location.href assignments
let redirectTarget = "";
beforeEach(() => {
  redirectTarget = "";
  Object.defineProperty(window, "location", {
    configurable: true,
    value: {
      ...window.location,
      get href() {
        return redirectTarget;
      },
      set href(val: string) {
        redirectTarget = val;
      },
    },
  });
});

// ---------------------------------------------------------------------------
// STU-42 — Current plan shown
// ---------------------------------------------------------------------------

describe("STU-42 — Current plan displayed", () => {
  it("shows page title", () => {
    mockUseSubscription.mockReturnValue({ data: MOCK_SUB_FREE, isLoading: false });
    render(<SubscriptionPage />);
    expect(
      screen.getByRole("heading", { name: SUBSCRIPTION_STRINGS.title }),
    ).toBeInTheDocument();
  });

  it("shows 'Current plan' label when subscription data loads", () => {
    mockUseSubscription.mockReturnValue({ data: MOCK_SUB_FREE, isLoading: false });
    render(<SubscriptionPage />);
    expect(screen.getByText(SUBSCRIPTION_STRINGS.currentPlanLabel)).toBeInTheDocument();
  });

  it("shows free plan label for free status", () => {
    mockUseSubscription.mockReturnValue({ data: MOCK_SUB_FREE, isLoading: false });
    render(<SubscriptionPage />);
    expect(screen.getByText(SUBSCRIPTION_STRINGS.currentPlanFree)).toBeInTheDocument();
  });

  it("shows 'Free Trial' for trial status", () => {
    mockUseSubscription.mockReturnValue({ data: MOCK_SUB_TRIAL, isLoading: false });
    render(<SubscriptionPage />);
    expect(screen.getByText(SUBSCRIPTION_STRINGS.freeTrial)).toBeInTheDocument();
  });

  it("shows 'Student — Monthly' for active monthly plan", () => {
    mockUseSubscription.mockReturnValue({
      data: MOCK_SUB_ACTIVE_MONTHLY,
      isLoading: false,
    });
    render(<SubscriptionPage />);
    expect(screen.getByText(SUBSCRIPTION_STRINGS.studentMonthly)).toBeInTheDocument();
  });

  it("shows 'Student — Annual' for active annual plan", () => {
    mockUseSubscription.mockReturnValue({
      data: MOCK_SUB_ACTIVE_ANNUAL,
      isLoading: false,
    });
    render(<SubscriptionPage />);
    expect(screen.getByText(SUBSCRIPTION_STRINGS.studentAnnual)).toBeInTheDocument();
  });

  it("shows all plan features for free/trial users", () => {
    mockUseSubscription.mockReturnValue({ data: MOCK_SUB_FREE, isLoading: false });
    render(<SubscriptionPage />);
    for (const feature of PLAN_FEATURES) {
      expect(screen.getByText(feature)).toBeInTheDocument();
    }
  });

  it("shows monthly price $9.99 by default", () => {
    mockUseSubscription.mockReturnValue({ data: MOCK_SUB_FREE, isLoading: false });
    render(<SubscriptionPage />);
    expect(
      screen.getByText(new RegExp(`\\${SUBSCRIPTION_STRINGS.monthlyPrice}`)),
    ).toBeInTheDocument();
  });

  it("shows 'Manage billing' button for active paid plan", () => {
    mockUseSubscription.mockReturnValue({
      data: MOCK_SUB_ACTIVE_MONTHLY,
      isLoading: false,
    });
    render(<SubscriptionPage />);
    expect(screen.getByRole("button", { name: /Manage billing/ })).toBeInTheDocument();
  });

  it("shows loading skeleton while fetching", () => {
    mockUseSubscription.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<SubscriptionPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("shows 'Cancels at period end' badge for cancel_at_period_end", () => {
    mockUseSubscription.mockReturnValue({ data: MOCK_SUB_CANCELLED, isLoading: false });
    render(<SubscriptionPage />);
    expect(screen.getByText("Cancels at period end")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// STU-43 — Upgrade initiates Stripe checkout
// ---------------------------------------------------------------------------

describe("STU-43 — Upgrade initiates Stripe checkout", () => {
  beforeEach(() => {
    mockUseSubscription.mockReturnValue({ data: MOCK_SUB_FREE, isLoading: false });
    mockCreateCheckout.mockResolvedValue(STRIPE_CHECKOUT_URL);
  });

  it("subscribe button is present for free plan", () => {
    render(<SubscriptionPage />);
    const btns = screen.getAllByRole("button");
    expect(
      btns.some((b) => b.textContent?.includes(SUBSCRIPTION_STRINGS.subscribeBtn)),
    ).toBe(true);
  });

  it("clicking subscribe calls createCheckout with student_monthly by default", async () => {
    render(<SubscriptionPage />);
    const btn = screen
      .getAllByRole("button")
      .find((b) => b.textContent?.includes(SUBSCRIPTION_STRINGS.subscribeBtn))!;
    fireEvent.click(btn);
    await waitFor(() =>
      expect(mockCreateCheckout).toHaveBeenCalledWith("student_monthly", "monthly"),
    );
  });

  it("redirects to Stripe checkout URL after createCheckout resolves", async () => {
    render(<SubscriptionPage />);
    const btn = screen
      .getAllByRole("button")
      .find((b) => b.textContent?.includes(SUBSCRIPTION_STRINGS.subscribeBtn))!;
    fireEvent.click(btn);
    await waitFor(() => expect(redirectTarget).toBe(STRIPE_CHECKOUT_URL));
  });

  it("switching to Annual and subscribing calls createCheckout with student_annual", async () => {
    render(<SubscriptionPage />);
    fireEvent.click(screen.getByRole("button", { name: /Annual/ }));
    const btn = screen
      .getAllByRole("button")
      .find((b) => b.textContent?.includes(SUBSCRIPTION_STRINGS.subscribeBtn))!;
    fireEvent.click(btn);
    await waitFor(() =>
      expect(mockCreateCheckout).toHaveBeenCalledWith("student_annual", "annual"),
    );
  });

  it("switching to Annual shows annual price $99.99", () => {
    render(<SubscriptionPage />);
    fireEvent.click(screen.getByRole("button", { name: /Annual/ }));
    expect(
      screen.getByText(new RegExp(`\\${SUBSCRIPTION_STRINGS.annualPrice}`)),
    ).toBeInTheDocument();
  });

  it("switching to Annual shows annual saving message", () => {
    render(<SubscriptionPage />);
    fireEvent.click(screen.getByRole("button", { name: /Annual/ }));
    expect(screen.getByText(SUBSCRIPTION_STRINGS.annualSaving)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// STU-44 — Billing portal opens for paid plan
// ---------------------------------------------------------------------------

describe("STU-44 — Billing portal for paid plan", () => {
  beforeEach(() => {
    mockUseSubscription.mockReturnValue({
      data: MOCK_SUB_ACTIVE_MONTHLY,
      isLoading: false,
    });
    mockGetBillingPortal.mockResolvedValue(STRIPE_PORTAL_URL);
  });

  it("Manage billing button is present for active plan", () => {
    render(<SubscriptionPage />);
    expect(screen.getByRole("button", { name: /Manage billing/ })).toBeInTheDocument();
  });

  it("clicking Manage billing calls getBillingPortalUrl", async () => {
    render(<SubscriptionPage />);
    fireEvent.click(screen.getByRole("button", { name: /Manage billing/ }));
    await waitFor(() => expect(mockGetBillingPortal).toHaveBeenCalled());
  });

  it("redirects to Stripe portal URL after getBillingPortalUrl resolves", async () => {
    render(<SubscriptionPage />);
    fireEvent.click(screen.getByRole("button", { name: /Manage billing/ }));
    await waitFor(() => expect(redirectTarget).toBe(STRIPE_PORTAL_URL));
  });

  it("subscribe button is NOT shown for active plan", () => {
    render(<SubscriptionPage />);
    const btns = screen.getAllByRole("button");
    expect(
      btns.every((b) => !b.textContent?.includes(SUBSCRIPTION_STRINGS.subscribeBtn)),
    ).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// STU-45 — Trial days remaining shown (Unit)
// ---------------------------------------------------------------------------

describe("STU-45 — Trial days remaining", () => {
  it("shows trial days remaining text for trial status", () => {
    mockUseSubscription.mockReturnValue({ data: MOCK_SUB_TRIAL, isLoading: false });
    render(<SubscriptionPage />);
    expect(
      screen.getByText(new RegExp(SUBSCRIPTION_STRINGS.trialSuffix)),
    ).toBeInTheDocument();
  });

  it("trial days count is positive (future trial end date)", () => {
    mockUseSubscription.mockReturnValue({ data: MOCK_SUB_TRIAL, isLoading: false });
    render(<SubscriptionPage />);
    // Text pattern: "N days remaining in trial"
    const el = screen.getByText(new RegExp(SUBSCRIPTION_STRINGS.trialSuffix));
    const match = el.textContent?.match(/(\d+)\s+day/);
    expect(Number(match?.[1])).toBeGreaterThan(0);
  });

  it("trial days text is NOT shown for free plan", () => {
    mockUseSubscription.mockReturnValue({ data: MOCK_SUB_FREE, isLoading: false });
    render(<SubscriptionPage />);
    expect(screen.queryByText(new RegExp(SUBSCRIPTION_STRINGS.trialSuffix))).toBeNull();
  });

  it("trial days text is NOT shown for active paid plan", () => {
    mockUseSubscription.mockReturnValue({
      data: MOCK_SUB_ACTIVE_MONTHLY,
      isLoading: false,
    });
    render(<SubscriptionPage />);
    expect(screen.queryByText(new RegExp(SUBSCRIPTION_STRINGS.trialSuffix))).toBeNull();
  });
});
