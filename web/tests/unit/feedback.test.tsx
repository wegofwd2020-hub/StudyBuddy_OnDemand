import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FeedbackWidget } from "@/components/feedback/FeedbackWidget";

// Mock the feedback API
vi.mock("@/lib/api/feedback", () => ({
  submitFeedback: vi.fn().mockResolvedValue(undefined),
}));

// Mock next-intl — the translator returns the key, so assertions use keys.
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

import { submitFeedback } from "@/lib/api/feedback";

const UP = "thumbs_up";
const DOWN = "thumbs_down";

describe("FeedbackWidget", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders thumbs up and down buttons", () => {
    render(<FeedbackWidget unitId="u1" contentType="lesson" />);
    expect(screen.getByLabelText(UP)).toBeTruthy();
    expect(screen.getByLabelText(DOWN)).toBeTruthy();
  });

  it("submits a thumbs up immediately — one click, no questions asked", async () => {
    render(<FeedbackWidget unitId="u1" contentType="lesson" />);
    fireEvent.click(screen.getByLabelText(UP));
    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith({
        unit_id: "u1",
        content_type: "lesson",
        rating: "up",
      });
    });
  });

  it("does not ask a happy student to explain themselves", async () => {
    render(<FeedbackWidget unitId="u1" contentType="lesson" />);
    fireEvent.click(screen.getByLabelText(UP));
    await waitFor(() => expect(submitFeedback).toHaveBeenCalled());
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  // ── Thumbs down asks why (#612) ──────────────────────────────────────────

  it("asks why on thumbs down instead of submitting straight away", () => {
    render(<FeedbackWidget unitId="u1" contentType="quiz" />);
    fireEvent.click(screen.getByLabelText(DOWN));

    expect(screen.getByRole("textbox")).toBeTruthy();
    expect(submitFeedback).not.toHaveBeenCalled();
  });

  it("sends the typed reason as the message, in a single submission", async () => {
    render(<FeedbackWidget unitId="u1" contentType="quiz" />);
    fireEvent.click(screen.getByLabelText(DOWN));
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "The second question made no sense." },
    });
    fireEvent.click(screen.getByRole("button", { name: "send" }));

    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith({
        unit_id: "u1",
        content_type: "quiz",
        rating: "down",
        comment: "The second question made no sense.",
      });
    });
    expect(submitFeedback).toHaveBeenCalledTimes(1);
  });

  it("lets the student skip the reason — the verdict still counts", async () => {
    render(<FeedbackWidget unitId="u1" contentType="quiz" />);
    fireEvent.click(screen.getByLabelText(DOWN));
    fireEvent.click(screen.getByRole("button", { name: "skip" }));

    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith({
        unit_id: "u1",
        content_type: "quiz",
        rating: "down",
      });
    });
  });

  it("does not send an empty comment as a message", async () => {
    render(<FeedbackWidget unitId="u1" contentType="quiz" />);
    fireEvent.click(screen.getByLabelText(DOWN));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "send" }));

    await waitFor(() => expect(submitFeedback).toHaveBeenCalled());
    const payload = vi.mocked(submitFeedback).mock.calls[0][0];
    expect(payload.comment).toBeUndefined();
  });

  it("caps the reason at the 500 characters the API accepts", () => {
    render(<FeedbackWidget unitId="u1" contentType="quiz" />);
    fireEvent.click(screen.getByLabelText(DOWN));
    expect(screen.getByRole("textbox").getAttribute("maxLength")).toBe("500");
  });

  // ── Outcome states ───────────────────────────────────────────────────────

  it("shows thank you message after submission", async () => {
    render(<FeedbackWidget unitId="u1" contentType="lesson" />);
    fireEvent.click(screen.getByLabelText(UP));
    await waitFor(() => {
      expect(screen.getByText("thanks")).toBeTruthy();
    });
  });

  it("disables buttons after submission", async () => {
    render(<FeedbackWidget unitId="u1" contentType="lesson" />);
    fireEvent.click(screen.getByLabelText(UP));
    await waitFor(() => {
      expect(screen.queryByLabelText(UP)).toBeNull();
    });
  });

  it("tells the student when it could not be saved, rather than failing silently", async () => {
    vi.mocked(submitFeedback).mockRejectedValueOnce(new Error("network"));
    render(<FeedbackWidget unitId="u1" contentType="lesson" />);
    fireEvent.click(screen.getByLabelText(UP));

    await waitFor(() => {
      expect(screen.getByText("error")).toBeTruthy();
    });
  });
});
