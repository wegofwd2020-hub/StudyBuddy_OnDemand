/**
 * Unit tests for /school/reports/alerts/settings — the #526 fix.
 *
 * The bug: the form seeded from a hardcoded DEFAULTS const on every visit, so a
 * saved threshold was never shown and saves looked lost. These pin that the form
 * now seeds from the server-loaded settings and saves the edited values.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AlertSettingsPage from "@/app/(school)/school/reports/alerts/settings/page";

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: () => ({ school_id: "school-1", role: "school_admin" }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockGet = vi.fn();
const mockUpdate = vi.fn();
vi.mock("@/lib/api/reports", () => ({
  getAlertSettings: (...args: unknown[]) => mockGet(...args),
  updateAlertSettings: (...args: unknown[]) => mockUpdate(...args),
}));

const SAVED = {
  pass_rate_threshold: 63,
  feedback_count_threshold: 3,
  inactive_days_threshold: 9,
  score_drop_threshold: 10,
  new_feedback_immediate: false,
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AlertSettingsPage />
    </QueryClientProvider>,
  );
}

describe("Alert settings page (#526)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue(SAVED);
    mockUpdate.mockResolvedValue(undefined);
  });

  it("seeds the form from the saved settings, not hardcoded defaults", async () => {
    renderPage();
    // 63 is the saved value; the old bug always showed the hardcoded 50.
    const input = (await screen.findByLabelText(/Low pass-rate/i)) as HTMLInputElement;
    expect(input.value).toBe("63");
    const days = screen.getByLabelText(/Inactive-student/i) as HTMLInputElement;
    expect(days.value).toBe("9");
  });

  it("saves the (edited) values to the school-scoped endpoint", async () => {
    renderPage();
    const input = (await screen.findByLabelText(/Low pass-rate/i)) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "42" } });
    fireEvent.click(screen.getByRole("button", { name: /Save thresholds/i }));
    await waitFor(() =>
      expect(mockUpdate).toHaveBeenCalledWith(
        "school-1",
        expect.objectContaining({ pass_rate_threshold: 42 }),
      ),
    );
  });
});
