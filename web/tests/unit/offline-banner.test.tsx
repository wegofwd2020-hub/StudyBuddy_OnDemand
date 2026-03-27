import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { OfflineBanner } from "@/components/student/OfflineBanner";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) =>
    key === "network"
      ? "No internet connection. Your progress will sync when you're back online."
      : key,
}));

describe("OfflineBanner", () => {
  const mockOnlineGetter = (value: boolean) => {
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value,
    });
  };

  beforeEach(() => {
    mockOnlineGetter(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing when online", () => {
    mockOnlineGetter(true);
    const { container } = render(<OfflineBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("shows banner when offline", async () => {
    mockOnlineGetter(false);
    render(<OfflineBanner />);
    expect(
      screen.getByText(/No internet connection/i)
    ).toBeTruthy();
  });

  it("shows banner when offline event fires", async () => {
    mockOnlineGetter(true);
    render(<OfflineBanner />);
    mockOnlineGetter(false);
    await act(async () => {
      window.dispatchEvent(new Event("offline"));
    });
    expect(screen.getByRole("alert")).toBeTruthy();
  });

  it("hides banner when online event fires", async () => {
    mockOnlineGetter(false);
    render(<OfflineBanner />);
    mockOnlineGetter(true);
    await act(async () => {
      window.dispatchEvent(new Event("online"));
    });
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
