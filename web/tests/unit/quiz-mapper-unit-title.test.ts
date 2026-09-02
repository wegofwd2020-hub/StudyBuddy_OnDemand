/**
 * `getQuiz()` must carry every field the result screen renders.
 *
 * A tester asked for the unit name beside the subject on the quiz result screen.
 * #704 added `unit_title` to the API and to `QuizPlayer`, which renders
 * `{quiz.unit_title && ...}`. Both halves were correct. It still did not appear,
 * and he reported it twice — the second time after being told it could not be
 * reproduced.
 *
 * The mapper between them dropped it:
 *
 *     return {
 *       unit_id: raw.unit_id,
 *       title: `Quiz — Set ${raw.set_number}`,
 *       pass_threshold: raw.passing_score,
 *       subject: raw.subject ?? undefined,
 *       questions: ...,
 *     };                                   // unit_title never copied
 *
 * Nothing caught it. `QuizContent.unit_title` is optional, so a mapper that
 * omits it typechecks perfectly; the backend tests asserted the API response
 * (correct); the component tests supplied their own fixture (correct). No test
 * exercised the seam, which is precisely where the value was lost.
 *
 * These tests are about the SEAM. They assert what survives the transformation,
 * not what either side produces in isolation.
 *
 * Run with: docker compose exec -T web npx vitest run quiz-mapper-unit-title
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { getQuiz } from "@/lib/api/content";
import api from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  default: { get: vi.fn() },
}));

const mockGet = vi.mocked(api.get);

/** Shaped exactly like the live response — captured from the demo. */
function backendQuiz(overrides: Record<string, unknown> = {}) {
  return {
    data: {
      unit_id: "G10-TECH-004",
      set_number: 3,
      language: "en",
      total_questions: 8,
      estimated_duration_minutes: 10,
      passing_score: 60,
      generated_at: "2026-09-02T00:00:00Z",
      model: "claude-sonnet-4-6",
      content_version: 1,
      subject: "Technology",
      unit_title: "Software Development Lifecycle",
      questions: [
        {
          question_id: "q1",
          question_text: "What is a sprint?",
          question_type: "multiple_choice",
          difficulty: "easy",
          options: [
            { option_id: "A", text: "A race" },
            { option_id: "B", text: "A timeboxed iteration" },
          ],
        },
      ],
      ...overrides,
    },
  };
}

beforeEach(() => vi.clearAllMocks());

describe("getQuiz — the mapper must not drop fields the UI renders", () => {
  it("carries unit_title through to the mapped quiz", async () => {
    // The regression this file exists for.
    mockGet.mockResolvedValue(backendQuiz());

    const quiz = await getQuiz("G10-TECH-004");

    expect(quiz.unit_title).toBe("Software Development Lifecycle");
  });

  it("carries the subject too, so the result screen can show both", async () => {
    // The tester's ask was the unit name *alongside* the subject. Losing either
    // one reproduces the complaint.
    mockGet.mockResolvedValue(backendQuiz());

    const quiz = await getQuiz("G10-TECH-004");

    expect(quiz.subject).toBe("Technology");
    expect(quiz.unit_title).toBe("Software Development Lifecycle");
  });

  it("tolerates a unit that genuinely has no title", async () => {
    // The API returns null for a unit absent from curriculum_units. The screen
    // omits the line in that case — it must not render "null" or crash.
    mockGet.mockResolvedValue(backendQuiz({ unit_title: null }));

    const quiz = await getQuiz("G10-TECH-004");

    expect(quiz.unit_title).toBeUndefined();
  });

  it("still builds the set heading and threshold it always did", async () => {
    // The negative direction: a mapper "fixed" by returning the raw response
    // would satisfy the assertions above and break the page, which reads
    // `title` and `pass_threshold` under names the API does not use.
    mockGet.mockResolvedValue(backendQuiz());

    const quiz = await getQuiz("G10-TECH-004");

    expect(quiz.title).toBe("Quiz — Set 3");
    expect(quiz.pass_threshold).toBe(60);
    expect(quiz.questions).toHaveLength(1);
    expect(quiz.questions[0].question).toBe("What is a sprint?");
  });

  it("never leaks the answer key through the mapper", async () => {
    // The server strips `correct_option` before sending (pitfall #35). If a
    // future change let the raw body through, the mapper is the last place that
    // would notice — so assert the shape it produces, not just the fields added.
    mockGet.mockResolvedValue(backendQuiz());

    const quiz = await getQuiz("G10-TECH-004");

    const serialised = JSON.stringify(quiz);
    expect(serialised).not.toContain("correct_option");
    expect(serialised).not.toContain("explanation");
  });
});
