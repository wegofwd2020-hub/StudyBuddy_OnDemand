/**
 * Unit tests for QuizPlayer scoring (#504).
 *
 * Two regressions live here:
 *
 * 1. The final question was counted twice when answered correctly: `correctCount`
 *    had already been incremented by the REVIEWED reducer before `handleNext`
 *    added `answerResult.correct` again. A student who got 3/5 right (last one
 *    correct) saw 4/5. At full marks it sent score=6 for a 5-question quiz, which
 *    the clamps quietly rewrote to 5 — that was the real cause of #460.
 *
 * 2. Scoring was client-side entirely. The quiz payload shipped the answer key and
 *    the browser told the backend both `correct` per answer and the final `score`.
 *    Grading is now the server's job: the player sends only the picked option, and
 *    the result screen renders the score the server reports.
 *
 * Run with:
 *   npm test -- quiz-player-scoring
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QuizPlayer } from "@/components/content/QuizPlayer";
import type { QuizContent } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockSubmitAnswer = vi.fn();
const mockEndSession = vi.fn();

vi.mock("@/lib/api/progress", () => ({
  submitAnswer: (...args: unknown[]) => mockSubmitAnswer(...args),
  endSession: (...args: unknown[]) => mockEndSession(...args),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, vals?: Record<string, unknown>) =>
    vals ? `${key}:${JSON.stringify(vals)}` : key,
}));

vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQueryClient: () => ({ invalidateQueries: vi.fn() }) };
});

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/**
 * 5 questions. Note there is NO correct_index here — the browser is not given the
 * answer key. The server decides; option 0 is "Right" only by the mock's grading.
 */
const QUIZ: QuizContent = {
  unit_id: "G8-SCI-001",
  title: "Quiz — Set 1",
  pass_threshold: 3,
  subject: "Science",
  questions: Array.from({ length: 5 }, (_, i) => ({
    index: i,
    question_id: `q${i + 1}`,
    question: `Question ${i + 1}?`,
    options: ["Right", "Wrong A", "Wrong B", "Wrong C"],
  })),
};

const CORRECT = 0;
const WRONG = 1;

/** Server-side grading, simulated: option 0 is the correct one. */
const SERVER_CORRECT_INDEX = 0;

async function playQuiz(answers: number[]) {
  for (let i = 0; i < answers.length; i++) {
    const isLast = i === answers.length - 1;
    const nextLabel = isLast ? /see results/i : /next question/i;

    fireEvent.click(await screen.findByText(QUIZ.questions[i].options[answers[i]]));
    fireEvent.click(screen.getByRole("button", { name: /submit answer/i }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: nextLabel })).toBeTruthy(),
    );
    fireEvent.click(screen.getByRole("button", { name: nextLabel }));
  }
}

// ---------------------------------------------------------------------------

describe("QuizPlayer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // The server grades and returns the verdict + the reveal.
    mockSubmitAnswer.mockImplementation(async ({ answer_index }) => ({
      correct: answer_index === SERVER_CORRECT_INDEX,
      correct_index: SERVER_CORRECT_INDEX,
      explanation: "Because that is the right one.",
    }));
    mockEndSession.mockResolvedValue({
      score: 3,
      total: 5,
      passed: true,
      attempt_number: 1,
    });
  });

  describe("server-side grading contract", () => {
    it("submits only the picked option — never a correctness claim", async () => {
      render(<QuizPlayer quiz={QUIZ} sessionId="s1" curriculumId="default-2026-g8" />);
      await playQuiz([CORRECT, WRONG, WRONG, CORRECT, CORRECT]);

      const firstCall = mockSubmitAnswer.mock.calls[0][0];
      expect(firstCall).toEqual({
        session_id: "s1",
        question_id: "q1", // the content's own id, not a synthesised one
        answer_index: 0,
      });
      // The client must not be asserting correctness or shipping the key back.
      expect(firstCall).not.toHaveProperty("correct");
      expect(firstCall).not.toHaveProperty("correct_index");
    });

    it("ends the session without sending a score", async () => {
      render(<QuizPlayer quiz={QUIZ} sessionId="s1" curriculumId="default-2026-g8" />);
      await playQuiz([CORRECT, WRONG, WRONG, CORRECT, CORRECT]);

      await waitFor(() => expect(mockEndSession).toHaveBeenCalledTimes(1));
      expect(mockEndSession).toHaveBeenCalledWith("s1");
    });

    it("renders the score the SERVER reports, not a locally counted one", async () => {
      // Server says 2/5 even though the player locally saw 3 correct. The server wins.
      mockEndSession.mockResolvedValue({
        score: 2,
        total: 5,
        passed: false,
        attempt_number: 1,
      });

      render(<QuizPlayer quiz={QUIZ} sessionId="s1" curriculumId="default-2026-g8" />);
      await playQuiz([CORRECT, WRONG, WRONG, CORRECT, CORRECT]);

      expect(await screen.findByText(/"score":2/)).toBeTruthy();
    });
  });

  describe("reveal comes from the server response", () => {
    it("shows the explanation returned with the verdict", async () => {
      render(<QuizPlayer quiz={QUIZ} sessionId="s1" curriculumId="default-2026-g8" />);

      fireEvent.click(await screen.findByText("Wrong A"));
      fireEvent.click(screen.getByRole("button", { name: /submit answer/i }));

      expect(await screen.findByText("Because that is the right one.")).toBeTruthy();
    });
  });
});
