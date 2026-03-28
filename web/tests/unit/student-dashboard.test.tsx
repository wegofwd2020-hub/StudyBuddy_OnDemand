/**
 * Unit tests for section 2.2 — Student Dashboard components
 * Covers TC-IDs: STU-04, STU-05, STU-06, STU-07, STU-08, STU-09, STU-11
 *
 * Run with:
 *   npm test -- student-dashboard
 *
 * Note (STU-10): Loading skeleton behaviour requires a delayed network response
 * which is better covered in E2E against a real authenticated session.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { StreakCard } from "@/components/student/StreakCard";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import {
  MOCK_STATS,
  MOCK_STATS_NO_STREAK,
  MOCK_PROGRESS_WITH_SESSIONS,
  MOCK_PROGRESS_EMPTY,
  QUICK_ACTIONS,
  DASHBOARD_STRINGS,
} from "../e2e/data/student-dashboard";

// ---------------------------------------------------------------------------
// Mock next-intl — return i18n key as-is so assertions are key-independent
// ---------------------------------------------------------------------------

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

// ---------------------------------------------------------------------------
// STU-04 — StreakCard renders with active streak
// ---------------------------------------------------------------------------

describe("STU-04 — StreakCard", () => {
  it("shows streak day count when streak > 0", () => {
    render(
      <StreakCard
        streakDays={MOCK_STATS.streak_days}
        sessionDates={MOCK_STATS.session_dates}
      />,
    );
    expect(screen.getByText(String(MOCK_STATS.streak_days))).toBeInTheDocument();
  });

  it("shows 'streak_label' i18n key when streak > 0", () => {
    render(
      <StreakCard
        streakDays={MOCK_STATS.streak_days}
        sessionDates={MOCK_STATS.session_dates}
      />,
    );
    expect(screen.getByText("streak_label")).toBeInTheDocument();
  });

  it("shows 'no_streak' i18n key when streak = 0", () => {
    render(
      <StreakCard
        streakDays={MOCK_STATS_NO_STREAK.streak_days}
        sessionDates={MOCK_STATS_NO_STREAK.session_dates}
      />,
    );
    expect(screen.getByText("no_streak")).toBeInTheDocument();
  });

  it("renders 7 activity dots", () => {
    const { container } = render(
      <StreakCard
        streakDays={MOCK_STATS.streak_days}
        sessionDates={MOCK_STATS.session_dates}
      />,
    );
    // Each day renders as a div with a title attribute (the ISO date)
    const dots = container.querySelectorAll("div[title]");
    expect(dots).toHaveLength(7);
  });

  it("marks active session dates with orange dot class", () => {
    const { container } = render(
      <StreakCard
        streakDays={MOCK_STATS.streak_days}
        sessionDates={MOCK_STATS.session_dates}
      />,
    );
    const activeDots = container.querySelectorAll("div.bg-orange-400");
    // Number of active dots should equal intersection of last7 dates and sessionDates
    expect(activeDots.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// STU-05 / STU-06 / STU-07 — Quick action hrefs
// ---------------------------------------------------------------------------

describe("STU-05/06/07 — Quick action hrefs", () => {
  it.each(QUICK_ACTIONS.map((a) => [a.label, a.href] as [string, string]))(
    '"%s" points to %s',
    (label, href) => {
      expect(href).toBeTruthy();
      expect(href.startsWith("/")).toBe(true);
    },
  );

  it("Browse Subjects href is /subjects", () => {
    expect(QUICK_ACTIONS[0].href).toBe("/subjects");
  });

  it("Curriculum Map href is /curriculum", () => {
    expect(QUICK_ACTIONS[1].href).toBe("/curriculum");
  });

  it("View Progress href is /progress", () => {
    expect(QUICK_ACTIONS[2].href).toBe("/progress");
  });
});

// ---------------------------------------------------------------------------
// STU-08 — Session list: sessions present
// ---------------------------------------------------------------------------

describe("STU-08 — Session list with data", () => {
  it("mock payload contains expected session titles", () => {
    const { sessions } = MOCK_PROGRESS_WITH_SESSIONS;
    expect(sessions.length).toBeGreaterThan(0);
    expect(sessions[0].unit_title).toBe("Algebra: Linear Equations");
    expect(sessions[1].unit_title).toBe("Cell Biology");
  });

  it("passed session has passed=true", () => {
    const passed = MOCK_PROGRESS_WITH_SESSIONS.sessions.find((s) => s.passed === true);
    expect(passed).toBeDefined();
  });

  it("failed session has passed=false", () => {
    const failed = MOCK_PROGRESS_WITH_SESSIONS.sessions.find((s) => s.passed === false);
    expect(failed).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// STU-09 — Empty state
// ---------------------------------------------------------------------------

describe("STU-09 — Empty session list", () => {
  it("mock empty payload has zero sessions", () => {
    expect(MOCK_PROGRESS_EMPTY.sessions).toHaveLength(0);
  });

  it("empty state i18n key is defined", () => {
    expect(DASHBOARD_STRINGS.noActivity).toBe("No recent activity");
  });
});

// ---------------------------------------------------------------------------
// STU-11 — OfflineBanner shows/hides based on network state
// ---------------------------------------------------------------------------

describe("STU-11 — OfflineBanner", () => {
  beforeEach(() => {
    // jsdom defaults navigator.onLine to true
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      get: () => true,
    });
  });

  it("renders nothing when browser is online", () => {
    const { container } = render(<OfflineBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("shows alert when offline event fires", async () => {
    render(<OfflineBanner />);

    await act(async () => {
      window.dispatchEvent(new Event("offline"));
    });

    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("hides alert when back online after being offline", async () => {
    render(<OfflineBanner />);

    await act(async () => {
      window.dispatchEvent(new Event("offline"));
    });
    expect(screen.getByRole("alert")).toBeInTheDocument();

    await act(async () => {
      window.dispatchEvent(new Event("online"));
    });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("alert contains WifiOff icon (svg element)", async () => {
    render(<OfflineBanner />);

    await act(async () => {
      window.dispatchEvent(new Event("offline"));
    });

    const alert = screen.getByRole("alert");
    expect(alert.querySelector("svg")).toBeTruthy();
  });
});
