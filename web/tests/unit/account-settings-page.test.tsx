/**
 * Unit tests for section 2.12 — Account Settings (`/account/settings`)
 * Covers TC-IDs: STU-36, STU-37, STU-38, STU-39, STU-40
 *
 * Run with:
 *   npm test -- account-settings-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SettingsPage from "@/app/(student)/account/settings/page";
import {
  MOCK_ACCOUNT_SETTINGS,
  UPDATED_DISPLAY_NAME,
  SETTINGS_STRINGS,
} from "../e2e/data/account-settings-page";

// ---------------------------------------------------------------------------
// Shared mocks
// ---------------------------------------------------------------------------

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

const mockGetAccountSettings = vi.fn();
const mockSaveAccountSettings = vi.fn();

vi.mock("@/lib/api/settings", () => ({
  getAccountSettings: (...args: unknown[]) => mockGetAccountSettings(...args),
  saveAccountSettings: (...args: unknown[]) => mockSaveAccountSettings(...args),
}));

// ---------------------------------------------------------------------------
// STU-36 — Settings load with current values pre-filled
// ---------------------------------------------------------------------------

describe("STU-36 — Settings load with current values", () => {
  beforeEach(() => {
    mockGetAccountSettings.mockResolvedValue(MOCK_ACCOUNT_SETTINGS);
    mockSaveAccountSettings.mockResolvedValue(undefined);
  });

  it("renders the page title", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: SETTINGS_STRINGS.title }),
      ).toBeInTheDocument(),
    );
  });

  it("renders Profile section heading", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(SETTINGS_STRINGS.profileHeading)).toBeInTheDocument(),
    );
  });

  it("pre-fills display name input with current value", async () => {
    render(<SettingsPage />);
    await waitFor(() => {
      const input = screen.getByLabelText(
        SETTINGS_STRINGS.displayNameLabel,
      ) as HTMLInputElement;
      expect(input.value).toBe(MOCK_ACCOUNT_SETTINGS.display_name);
    });
  });

  it("renders Language section heading", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(SETTINGS_STRINGS.languageHeading)).toBeInTheDocument(),
    );
  });

  it("renders all three locale buttons", async () => {
    render(<SettingsPage />);
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: SETTINGS_STRINGS.english }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: SETTINGS_STRINGS.french }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: SETTINGS_STRINGS.spanish }),
      ).toBeInTheDocument();
    });
  });

  it("active locale button (en) has blue background", async () => {
    render(<SettingsPage />);
    await waitFor(() => {
      const btn = screen.getByRole("button", { name: SETTINGS_STRINGS.english });
      expect(btn.className).toContain("bg-blue-600");
    });
  });

  it("renders Notifications section heading", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(SETTINGS_STRINGS.notifHeading)).toBeInTheDocument(),
    );
  });

  it("renders all three notification labels", async () => {
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText(SETTINGS_STRINGS.streakReminders)).toBeInTheDocument();
      expect(screen.getByText(SETTINGS_STRINGS.weeklySummary)).toBeInTheDocument();
      expect(screen.getByText(SETTINGS_STRINGS.quizNudges)).toBeInTheDocument();
    });
  });

  it("renders the Save button", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: SETTINGS_STRINGS.saveBtn }),
      ).toBeInTheDocument(),
    );
  });
});

// ---------------------------------------------------------------------------
// STU-37 — Display name can be updated
// ---------------------------------------------------------------------------

describe("STU-37 — Display name update", () => {
  beforeEach(() => {
    mockGetAccountSettings.mockResolvedValue(MOCK_ACCOUNT_SETTINGS);
    mockSaveAccountSettings.mockResolvedValue(undefined);
  });

  it("allows typing a new display name into the input", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByLabelText(SETTINGS_STRINGS.displayNameLabel),
      ).toBeInTheDocument(),
    );
    const input = screen.getByLabelText(
      SETTINGS_STRINGS.displayNameLabel,
    ) as HTMLInputElement;
    fireEvent.change(input, { target: { value: UPDATED_DISPLAY_NAME } });
    expect(input.value).toBe(UPDATED_DISPLAY_NAME);
  });

  it("clicking Save calls saveAccountSettings with updated name", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByLabelText(SETTINGS_STRINGS.displayNameLabel),
      ).toBeInTheDocument(),
    );
    const input = screen.getByLabelText(SETTINGS_STRINGS.displayNameLabel);
    fireEvent.change(input, { target: { value: UPDATED_DISPLAY_NAME } });
    fireEvent.click(screen.getByRole("button", { name: SETTINGS_STRINGS.saveBtn }));
    await waitFor(() =>
      expect(mockSaveAccountSettings).toHaveBeenCalledWith(
        expect.objectContaining({ display_name: UPDATED_DISPLAY_NAME }),
      ),
    );
  });

  it("shows Saved confirmation after successful save", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: SETTINGS_STRINGS.saveBtn }),
      ).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: SETTINGS_STRINGS.saveBtn }));
    await waitFor(() =>
      expect(screen.getByText(SETTINGS_STRINGS.savedText)).toBeInTheDocument(),
    );
  });
});

// ---------------------------------------------------------------------------
// STU-38 — Language selection works
// ---------------------------------------------------------------------------

describe("STU-38 — Language selection", () => {
  beforeEach(() => {
    mockGetAccountSettings.mockResolvedValue(MOCK_ACCOUNT_SETTINGS);
    mockSaveAccountSettings.mockResolvedValue(undefined);
  });

  it("clicking Français activates it with blue background", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: SETTINGS_STRINGS.french }),
      ).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: SETTINGS_STRINGS.french }));
    expect(
      screen.getByRole("button", { name: SETTINGS_STRINGS.french }).className,
    ).toContain("bg-blue-600");
  });

  it("clicking Français deactivates English button", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: SETTINGS_STRINGS.french }),
      ).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: SETTINGS_STRINGS.french }));
    expect(
      screen.getByRole("button", { name: SETTINGS_STRINGS.english }).className,
    ).not.toContain("bg-blue-600");
  });

  it("saving after language change calls saveAccountSettings with locale fr", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: SETTINGS_STRINGS.french }),
      ).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: SETTINGS_STRINGS.french }));
    fireEvent.click(screen.getByRole("button", { name: SETTINGS_STRINGS.saveBtn }));
    await waitFor(() =>
      expect(mockSaveAccountSettings).toHaveBeenCalledWith(
        expect.objectContaining({ locale: "fr" }),
      ),
    );
  });
});

// ---------------------------------------------------------------------------
// STU-39 — Notification toggles save
// ---------------------------------------------------------------------------

describe("STU-39 — Notification toggles", () => {
  beforeEach(() => {
    mockGetAccountSettings.mockResolvedValue(MOCK_ACCOUNT_SETTINGS);
    mockSaveAccountSettings.mockResolvedValue(undefined);
  });

  it("toggling Weekly summary checkbox changes its checked state", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(SETTINGS_STRINGS.weeklySummary)).toBeInTheDocument(),
    );
    // weekly_summary starts false — find its checkbox via sr-only input
    const checkboxes = screen.getAllByRole("checkbox", { hidden: true });
    // Order matches render: streak_reminders(0), weekly_summary(1), quiz_nudges(2)
    const weeklyCb = checkboxes[1] as HTMLInputElement;
    expect(weeklyCb.checked).toBe(false);
    fireEvent.click(weeklyCb);
    expect(weeklyCb.checked).toBe(true);
  });

  it("saving after toggle calls saveAccountSettings with updated notifications", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(SETTINGS_STRINGS.weeklySummary)).toBeInTheDocument(),
    );
    const checkboxes = screen.getAllByRole("checkbox", { hidden: true });
    fireEvent.click(checkboxes[1]); // toggle weekly_summary on
    fireEvent.click(screen.getByRole("button", { name: SETTINGS_STRINGS.saveBtn }));
    await waitFor(() =>
      expect(mockSaveAccountSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          notifications: expect.objectContaining({ weekly_summary: true }),
        }),
      ),
    );
  });

  it("shows no error after successful notification save", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: SETTINGS_STRINGS.saveBtn }),
      ).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: SETTINGS_STRINGS.saveBtn }));
    await waitFor(() => expect(mockSaveAccountSettings).toHaveBeenCalled());
    expect(screen.queryByText(SETTINGS_STRINGS.saveError)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// STU-40 — Loading skeleton during fetch
// ---------------------------------------------------------------------------

describe("STU-40 — Loading skeleton during fetch", () => {
  it("shows skeleton while getAccountSettings is pending", () => {
    // Never resolves during this test
    mockGetAccountSettings.mockReturnValue(new Promise(() => {}));
    const { container } = render(<SettingsPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("hides skeleton and shows form once data resolves", async () => {
    mockGetAccountSettings.mockResolvedValue(MOCK_ACCOUNT_SETTINGS);
    const { container } = render(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByLabelText(SETTINGS_STRINGS.displayNameLabel),
      ).toBeInTheDocument(),
    );
    expect(container.querySelector("[data-slot='skeleton']")).toBeNull();
  });

  it("shows load error message when getAccountSettings rejects", async () => {
    mockGetAccountSettings.mockRejectedValue(new Error("network error"));
    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(SETTINGS_STRINGS.loadError)).toBeInTheDocument(),
    );
  });

  it("shows save error message when saveAccountSettings rejects", async () => {
    mockGetAccountSettings.mockResolvedValue(MOCK_ACCOUNT_SETTINGS);
    mockSaveAccountSettings.mockRejectedValue(new Error("save failed"));
    render(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: SETTINGS_STRINGS.saveBtn }),
      ).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: SETTINGS_STRINGS.saveBtn }));
    await waitFor(() =>
      expect(screen.getByText(SETTINGS_STRINGS.saveError)).toBeInTheDocument(),
    );
  });
});
