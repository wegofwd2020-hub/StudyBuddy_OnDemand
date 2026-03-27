import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FeedbackWidget } from "@/components/feedback/FeedbackWidget";

// Mock the feedback API
vi.mock("@/lib/api/feedback", () => ({
  submitFeedback: vi.fn().mockResolvedValue(undefined),
}));

// Mock next-intl
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

import { submitFeedback } from "@/lib/api/feedback";

describe("FeedbackWidget", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders thumbs up and down buttons", () => {
    render(<FeedbackWidget unitId="u1" contentType="lesson" />);
    expect(screen.getByLabelText("Thumbs up")).toBeTruthy();
    expect(screen.getByLabelText("Thumbs down")).toBeTruthy();
  });

  it("calls submitFeedback with 'up' when thumbs up clicked", async () => {
    render(<FeedbackWidget unitId="u1" contentType="lesson" />);
    fireEvent.click(screen.getByLabelText("Thumbs up"));
    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith({
        unit_id: "u1",
        content_type: "lesson",
        rating: "up",
      });
    });
  });

  it("calls submitFeedback with 'down' when thumbs down clicked", async () => {
    render(<FeedbackWidget unitId="u1" contentType="quiz" />);
    fireEvent.click(screen.getByLabelText("Thumbs down"));
    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith({
        unit_id: "u1",
        content_type: "quiz",
        rating: "down",
      });
    });
  });

  it("shows thank you message after submission", async () => {
    render(<FeedbackWidget unitId="u1" contentType="lesson" />);
    fireEvent.click(screen.getByLabelText("Thumbs up"));
    await waitFor(() => {
      expect(screen.getByText("Thanks for your feedback!")).toBeTruthy();
    });
  });

  it("disables buttons after submission", async () => {
    render(<FeedbackWidget unitId="u1" contentType="lesson" />);
    fireEvent.click(screen.getByLabelText("Thumbs up"));
    await waitFor(() => {
      expect(screen.queryByLabelText("Thumbs up")).toBeNull();
    });
  });
});
