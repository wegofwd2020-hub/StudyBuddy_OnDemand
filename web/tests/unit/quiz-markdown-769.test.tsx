/**
 * Quiz questions must be FORMATTED, not printed raw (#769).
 *
 * The content has carried markup all along — measured on the demo, 2026-09-17,
 * across the 6,504 real platform quiz questions:
 *
 *   question_text : 5,181 with **bold**, 2,643 with $math$, 1,036 with a GFM table
 *   options       : 8,984 of 26,016 with $math$, 1,286 with **bold**
 *   explanation   : 5,300 with **bold**, 3,620 with $math$, 361 with a table
 *
 * `QuizPlayer` was the ONLY viewer that rendered any of it as a bare string —
 * the authoring panel and both content-review viewers already format it. So a
 * Grade 11 Accounting question shipped its debit/credit table to the student as
 * literal pipes. That is what #769 reported as "please format these as tables":
 * the tables were already written, and had never once been rendered.
 *
 * The a11y invariant below is the load-bearing one. Options are rendered inside
 * <button>, whose content model is PHRASING content — a <p>, <table> or <div>
 * in there is invalid HTML and breaks activation in some assistive tech. 89 of
 * the 26,016 options do contain a block construct (61 code fences, 18 lists,
 * 5 tables, 5 headings), so "the content never has blocks" is not a defence
 * that holds. Options therefore render through the INLINE variant, which is
 * required to emit no block element regardless of its input.
 *
 * Run with:
 *   npm test -- quiz-markdown-769
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QuizPlayer } from "@/components/content/QuizPlayer";
import type { QuizContent } from "@/lib/types/api";

const mockSubmitAnswer = vi.fn();
const mockEndSession = vi.fn();
const mockGetSessionAnswers = vi.fn(
  async () => [] as { question_id: string; answer_index: number }[],
);

vi.mock("@/lib/api/progress", () => ({
  submitAnswer: (...args: unknown[]) => mockSubmitAnswer(...args),
  endSession: (...args: unknown[]) => mockEndSession(...args),
  getSessionAnswers: (...args: unknown[]) => mockGetSessionAnswers(...args),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, vals?: Record<string, unknown>) =>
    vals ? `${key}:${JSON.stringify(vals)}` : key,
}));

vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQueryClient: () => ({ invalidateQueries: vi.fn() }) };
});

// Abridged from the real G11-ACC-001 / quiz_set_1 / q3 and q4 on the demo.
const ACCOUNTING_STEM = `A business purchases office equipment worth **CAD 12,000** on credit. Using the fundamental accounting equation, identify the **correct effect** of this transaction.

| Element | Change |
|:--------|-------:|
| Assets | ? |
| Liabilities | ? |
| Owner's Equity | ? |`;

const QUIZ: QuizContent = {
  unit_id: "G11-ACC-001",
  title: "Quiz — Set 1",
  pass_threshold: 1,
  subject: "Accountancy",
  questions: [
    {
      question_id: "q1",
      question: ACCOUNTING_STEM,
      options: [
        "**Internal:** Management and the board.",
        "Assets increase by $12{,}000$; Liabilities increase by the same amount.",
        // A block construct in an option: rare (89 of 26,016) but real, and the
        // reason options cannot simply use the block renderer.
        "- Assets up\n- Liabilities up",
        "Owner's Equity is unchanged.",
      ],
    },
  ],
} as unknown as QuizContent;

beforeEach(() => {
  vi.clearAllMocks();
  mockSubmitAnswer.mockResolvedValue({ recorded: true });
  mockGetSessionAnswers.mockResolvedValue([]);
});

describe("QuizPlayer markdown rendering (#769)", () => {
  it("renders a GFM table in the question stem instead of raw pipes", () => {
    const { container } = render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);

    expect(container.querySelector("table")).not.toBeNull();
    const headers = Array.from(container.querySelectorAll("th")).map(
      (th) => th.textContent,
    );
    expect(headers).toContain("Element");
    expect(headers).toContain("Change");
    // The literal markup must be gone, not merely supplemented.
    expect(container.textContent).not.toContain("|:--------|");
  });

  it("renders **bold** in the stem as emphasis, not asterisks", () => {
    const { container } = render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);

    const strongs = Array.from(container.querySelectorAll("strong")).map(
      (s) => s.textContent,
    );
    expect(strongs).toContain("CAD 12,000");
    expect(container.textContent).not.toContain("**CAD 12,000**");
  });

  it("renders math in an option through KaTeX rather than raw dollar signs", () => {
    const { container } = render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);

    // 35% of all options carry math — the single biggest slice of #769.
    expect(container.querySelector(".katex")).not.toBeNull();
    expect(container.textContent).not.toContain("$12{,}000$");
  });

  it("emits no block element inside an option <button> (a11y invariant)", () => {
    const { container } = render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);

    const optionButtons = Array.from(container.querySelectorAll("button")).filter(
      (b) => b.getAttribute("aria-pressed") !== null,
    );
    expect(optionButtons.length).toBe(4);

    for (const button of optionButtons) {
      // <button> takes phrasing content only. A <p> here is invalid HTML and
      // breaks activation in some assistive tech.
      expect(
        button.querySelector("p, div, table, ul, ol, li, pre, blockquote"),
      ).toBeNull();
    }
  });

  it("still formats the option's inline markup despite the block ban", () => {
    const { container } = render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);

    const optionButtons = Array.from(container.querySelectorAll("button")).filter(
      (b) => b.getAttribute("aria-pressed") !== null,
    );
    expect(optionButtons[0].querySelector("strong")?.textContent).toBe("Internal:");
    expect(container.textContent).not.toContain("**Internal:**");
  });

  it("formats the stem and the explanation on the results summary", async () => {
    mockEndSession.mockResolvedValue({
      score: 1,
      total: 1,
      passed: true,
      attempt_number: 1,
      reveal: [
        {
          question_id: "q1",
          correct_index: 3,
          explanation: "The **accounting equation** stays balanced: $A = L + E$.",
        },
      ],
    });

    const { container } = render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);

    const optionButtons = Array.from(container.querySelectorAll("button")).filter(
      (b) => b.getAttribute("aria-pressed") !== null,
    );
    fireEvent.click(optionButtons[3]);
    await waitFor(() => expect(mockSubmitAnswer).toHaveBeenCalled());

    fireEvent.click(screen.getByText("finish"));
    await waitFor(() => expect(mockEndSession).toHaveBeenCalled());

    // The summary repeats the stem — it must be formatted there too, not only
    // during the attempt.
    await waitFor(() => expect(container.querySelector("table")).not.toBeNull());

    const strongs = Array.from(container.querySelectorAll("strong")).map(
      (s) => s.textContent,
    );
    expect(strongs).toContain("accounting equation");
    expect(container.textContent).not.toContain("**accounting equation**");
    // Every one of the 6,504 questions has an explanation; 3,620 carry math.
    expect(container.querySelector(".katex")).not.toBeNull();
  });
});
