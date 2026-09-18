/**
 * Quiz answer review page (#762) — /school/content/[curriculum_id]/units/[unit_id]/answers
 *
 * What this pins, and why each one has a history:
 *
 *  - The correct option is MARKED. The page exists because a school reported a
 *    wrong answer key; showing the options without saying which one grades is
 *    the whole defect, restated.
 *  - The Correct control is HIDDEN without `curriculum.review`. The backend
 *    guard is the control (`require_review`), but a control that 403s on click
 *    is worse than no control — the same ruling that hides the "Review
 *    answers" link from teachers with no curriculum capability at all.
 *  - A correction that would FORK the curriculum is confirmed BEFORE the call,
 *    naming all three consequences, because the fork repoints the whole grade
 *    and stops platform regeneration reaching the unit. Afterwards the page
 *    says what actually happened by READING `created.fork` / `grade_repointed`
 *    off the response — inferring it from the request is how a page ends up
 *    telling a school it forked something it did not.
 *  - One question appearing in several sets is ONE row. `stable_question_id`
 *    hashes the STEM, not the set number, so a unit holds up to three bodies
 *    for one question — and both writes act on the identity, correcting every
 *    set at once (Task 4's ruling). Rendering three rows would offer the same
 *    button three times, and a tick written by one would appear on all three,
 *    which reads as a bug in the page rather than a fact about the content.
 *
 * Assertions go through `data-testid` + `toHaveTextContent` rather than
 * `getByText(/regex/)` wherever the text sits inside a card: an unanchored
 * regex matches every ANCESTOR whose textContent contains it too, so the
 * obvious spelling fails with "found multiple elements" on a page that is
 * perfectly correct.
 *
 * Run with:
 *   npx vitest run answer-review-page-762
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import AnswerReviewPage from "@/app/(school)/school/content/[curriculum_id]/units/[unit_id]/answers/page";
import UnitEditPage from "@/app/(school)/school/content/[curriculum_id]/units/[unit_id]/edit/page";
import UnitPerformancePage from "@/app/(school)/school/reports/units/page";
import type {
  AnswerReviewList,
  AnswerReviewQuestion,
  CorrectAnswerResult,
} from "@/lib/api/answers";
import type { CurriculumHealthReport } from "@/lib/api/reports";

// ── Harness ───────────────────────────────────────────────────────────────────

const CURRICULUM_ID = "default-2026-g11-commerce";
const UNIT_ID = "G11-ACC-001";
const SCHOOL_ID = "school-001";
const ANSWERS_HREF = `/school/content/${CURRICULUM_ID}/units/${UNIT_ID}/answers`;

interface TestTeacher {
  teacher_id: string;
  school_id: string;
  role: "teacher" | "school_admin";
  capabilities: string[];
  first_login: boolean;
}

let teacher: TestTeacher | null = null;

vi.mock("@/lib/hooks/useTeacher", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/hooks/useTeacher")>();
  return { ...actual, useTeacher: () => teacher };
});

vi.mock("next/navigation", () => ({
  useParams: () => ({ curriculum_id: CURRICULUM_ID, unit_id: UNIT_ID }),
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => ANSWERS_HREF,
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("recharts", () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Bar: () => null,
  Cell: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

const mockList = vi.fn();
const mockValidate = vi.fn();
const mockCorrect = vi.fn();
vi.mock("@/lib/api/answers", () => ({
  listUnitAnswers: (...args: unknown[]) => mockList(...args),
  validateAnswer: (...args: unknown[]) => mockValidate(...args),
  correctAnswer: (...args: unknown[]) => mockCorrect(...args),
  answerErrorCode: () => null,
  answerErrorMessage: (_e: unknown, fallback: string) => fallback,
}));

const mockUnitStatus = vi.fn();
vi.mock("@/lib/api/school-admin", () => ({
  listUnitOverrideStatus: (...args: unknown[]) => mockUnitStatus(...args),
  getUnitOverride: vi.fn(() => new Promise(() => {})),
  getUnitOverrideSource: vi.fn(() => new Promise(() => {})),
  saveDraft: vi.fn(),
  submitForReview: vi.fn(),
  approveUnitContent: vi.fn(),
  rejectUnitContent: vi.fn(),
  revertUnitContent: vi.fn(),
}));

const mockHealth = vi.fn();
vi.mock("@/lib/api/reports", () => ({
  getCurriculumHealth: (...args: unknown[]) => mockHealth(...args),
  UNSTREAMED: "unstreamed",
}));

function renderPage(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

/** Wait for the listing to render, without a regex that would also match every
 *  ancestor of the question text. */
async function loadedQuestions(): Promise<HTMLElement[]> {
  return screen.findAllByTestId("answer-question");
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

function question(over: Partial<AnswerReviewQuestion> = {}): AnswerReviewQuestion {
  return {
    stable_question_id: "sqid-capital",
    set_number: 1,
    question_id: "q1",
    question_text: "Which account is credited when a sale is made on credit?",
    options: [
      { option_id: "A", text: "Cash" },
      { option_id: "B", text: "Sales" },
      { option_id: "C", text: "Debtors" },
      { option_id: "D", text: "Purchases" },
    ],
    correct_option: "B",
    correct_option_resolves: true,
    served_from: "store",
    validated: null,
    flag_count: 0,
    ...over,
  };
}

function listing(over: Partial<AnswerReviewList> = {}): AnswerReviewList {
  return {
    ownership: "override",
    source_curriculum_id: CURRICULUM_ID,
    owned_curriculum_id: "fork-abc",
    questions: [question()],
    ...over,
  };
}

const CORRECTED: CorrectAnswerResult = {
  ownership_before: "override",
  created: { adoption: false, fork: false, import: false },
  override_id: "ov-1",
  override_ids: ["ov-1"],
  owned_curriculum_id: "fork-abc",
  grade_repointed: false,
  sets_corrected: [1],
  old_correct_text: "Sales",
  new_correct_text: "Debtors",
  validated_at: "2026-09-18T09:30:00Z",
};

/** The option row carrying `text`, found by its own exact label. */
function optionRow(text: string): HTMLElement {
  return screen.getByText(text).closest("[data-option]") as HTMLElement;
}

beforeEach(() => {
  vi.clearAllMocks();
  teacher = {
    teacher_id: "teacher-001",
    school_id: SCHOOL_ID,
    role: "school_admin",
    capabilities: [],
    first_login: false,
  };
  mockList.mockResolvedValue(listing());
  mockValidate.mockResolvedValue({
    validated_by: "teacher-001",
    validated_at: "2026-09-18T09:30:00Z",
    correct_text: "Sales",
  });
  mockCorrect.mockResolvedValue(CORRECTED);
});

// ── What the reviewer sees ────────────────────────────────────────────────────

describe("the questions and their answers", () => {
  it("marks the correct option", async () => {
    renderPage(<AnswerReviewPage />);
    await loadedQuestions();

    expect(within(optionRow("Sales")).getByText(/^Correct answer$/)).toBeInTheDocument();
    expect(
      within(optionRow("Debtors")).queryByText(/^Correct answer$/),
    ).not.toBeInTheDocument();
  });

  it("says when a question's correct option names no option it has", async () => {
    mockList.mockResolvedValue(
      listing({
        questions: [question({ correct_option: "E", correct_option_resolves: false })],
      }),
    );
    renderPage(<AnswerReviewPage />);

    // The grader DROPS such a question, so nobody is scored on it — the exact
    // defect a reviewer opens this page to find.
    const [card] = await loadedQuestions();
    expect(card).toHaveTextContent(/no answer that can be marked/i);
  });

  it("shows who checked it and when", async () => {
    mockList.mockResolvedValue(
      listing({
        questions: [
          question({
            validated: {
              by: "teacher-002",
              by_name: "Asha Rao",
              at: "2026-09-14T14:05:00Z",
              stale: false,
            },
          }),
        ],
      }),
    );
    renderPage(<AnswerReviewPage />);

    const state = await screen.findByTestId("validation-state");
    expect(state).toHaveTextContent("Checked by Asha Rao");
    // dd/mm/yyyy through @/lib/utils/date (#759) — never the viewer's locale.
    expect(state).toHaveTextContent("14/09/2026");
  });

  it("calls a tick whose answer has since changed 'Needs re-checking'", async () => {
    mockList.mockResolvedValue(
      listing({
        questions: [
          question({
            validated: {
              by: "teacher-002",
              by_name: "Asha Rao",
              at: "2026-09-14T14:05:00Z",
              stale: true,
            },
          }),
        ],
      }),
    );
    renderPage(<AnswerReviewPage />);

    const state = await screen.findByTestId("validation-state");
    expect(state).toHaveTextContent(/needs re-checking/i);
    expect(state).not.toHaveTextContent(/^Checked by/);
  });

  it("sorts by flag count, most-flagged first, by default", async () => {
    mockList.mockResolvedValue(
      listing({
        questions: [
          question({
            stable_question_id: "sqid-quiet",
            question_id: "q1",
            question_text: "Quiet question",
            flag_count: 0,
          }),
          question({
            stable_question_id: "sqid-loud",
            question_id: "q2",
            question_text: "Loud question",
            flag_count: 7,
          }),
        ],
      }),
    );
    renderPage(<AnswerReviewPage />);

    const cards = await loadedQuestions();
    expect(cards.map((el) => el.getAttribute("data-question"))).toEqual([
      "sqid-loud",
      "sqid-quiet",
    ]);
  });
});

// ── One question, several sets ────────────────────────────────────────────────

describe("a question that appears in more than one set", () => {
  it("is one row, naming the sets it is in", async () => {
    mockList.mockResolvedValue(
      listing({
        questions: [
          question({ set_number: 1 }),
          question({ set_number: 2 }),
          question({ set_number: 3 }),
        ],
      }),
    );
    renderPage(<AnswerReviewPage />);

    const cards = await loadedQuestions();
    expect(cards).toHaveLength(1);
    expect(screen.getByTestId("answer-sets")).toHaveTextContent("Quiz sets 1, 2 and 3");
  });

  it("says so out loud when the sets disagree about the answer", async () => {
    mockList.mockResolvedValue(
      listing({
        questions: [
          question({ set_number: 1, correct_option: "B" }),
          question({ set_number: 2, correct_option: "C" }),
        ],
      }),
    );
    renderPage(<AnswerReviewPage />);

    // Still one row — but the disagreement is stated rather than resolved
    // silently, because two rows contradicting each other reads as a bug in
    // the page rather than a fact about the content.
    const cards = await loadedQuestions();
    expect(cards).toHaveLength(1);
    const notice = screen.getByTestId("sets-disagree");
    expect(notice).toHaveTextContent("set 1");
    expect(notice).toHaveTextContent("Sales");
    expect(notice).toHaveTextContent("set 2");
    expect(notice).toHaveTextContent("Debtors");
  });
});

// ── Who may correct ───────────────────────────────────────────────────────────

describe("the Correct control", () => {
  it("is absent for a teacher without the review capability", async () => {
    teacher = {
      teacher_id: "teacher-003",
      school_id: SCHOOL_ID,
      role: "teacher",
      capabilities: ["curriculum.commission"],
      first_login: false,
    };
    renderPage(<AnswerReviewPage />);
    await loadedQuestions();

    // A `curriculum.commission` holder clears the READ guard and not the write
    // one — the discriminating case, not a teacher with no capability at all,
    // who would be refused by either.
    expect(screen.queryAllByRole("radio")).toHaveLength(0);
    expect(
      screen.queryByRole("button", { name: /mark as checked/i }),
    ).not.toBeInTheDocument();
    // They still see the answer — looking is the point of the read gate.
    expect(within(optionRow("Sales")).getByText(/^Correct answer$/)).toBeInTheDocument();
  });

  it("is present for a curriculum.review teacher", async () => {
    teacher = {
      teacher_id: "teacher-004",
      school_id: SCHOOL_ID,
      role: "teacher",
      capabilities: ["curriculum.review"],
      first_login: false,
    };
    renderPage(<AnswerReviewPage />);
    await loadedQuestions();

    expect(screen.getByRole("radio", { name: "Debtors" })).toBeInTheDocument();
  });
});

// ── Correcting ────────────────────────────────────────────────────────────────

describe("choosing a different correct option", () => {
  it("sends that option letter", async () => {
    renderPage(<AnswerReviewPage />);
    await loadedQuestions();

    fireEvent.click(screen.getByRole("radio", { name: "Debtors" }));

    await waitFor(() =>
      expect(mockCorrect).toHaveBeenCalledWith(
        SCHOOL_ID,
        CURRICULUM_ID,
        UNIT_ID,
        "sqid-capital",
        "C",
        false,
        "en",
      ),
    );
  });

  it("reports what the server says happened, rather than inferring it", async () => {
    mockCorrect.mockResolvedValue({
      ...CORRECTED,
      ownership_before: "none",
      created: { adoption: true, fork: true, import: true },
      grade_repointed: true,
      sets_corrected: [1, 2, 3],
    });
    renderPage(<AnswerReviewPage />);
    await loadedQuestions();

    fireEvent.click(screen.getByRole("radio", { name: "Debtors" }));

    const banner = await screen.findByTestId("correction-result");
    expect(banner).toHaveTextContent(/own copy of this unit/i);
    expect(banner).toHaveTextContent(/points at your copy/i);
    expect(banner).toHaveTextContent(/quiz sets 1, 2 and 3/i);
  });

  it("does not claim a fork when the response says none was created", async () => {
    renderPage(<AnswerReviewPage />);
    await loadedQuestions();

    fireEvent.click(screen.getByRole("radio", { name: "Debtors" }));

    const banner = await screen.findByTestId("correction-result");
    expect(banner).toHaveTextContent(/answer updated/i);
    expect(banner).not.toHaveTextContent(/own copy of this unit/i);
    expect(banner).not.toHaveTextContent(/points at your copy/i);
  });
});

describe("a correction that would fork the curriculum", () => {
  beforeEach(() => {
    mockList.mockResolvedValue(listing({ ownership: "none", owned_curriculum_id: null }));
  });

  it("asks first, naming the consequence, and calls nothing until confirmed", async () => {
    renderPage(<AnswerReviewPage />);
    await loadedQuestions();

    fireEvent.click(screen.getByRole("radio", { name: "Debtors" }));

    const confirmation = await screen.findByRole("dialog");
    expect(confirmation).toHaveTextContent(/own copy of this unit/i);
    expect(confirmation).toHaveTextContent(/no longer reach it/i);
    expect(confirmation).toHaveTextContent(/point at your copy/i);
    expect(mockCorrect).not.toHaveBeenCalled();
  });

  it("sends confirm_fork only after the reviewer accepts", async () => {
    renderPage(<AnswerReviewPage />);
    await loadedQuestions();

    fireEvent.click(screen.getByRole("radio", { name: "Debtors" }));
    await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: /keep our own copy/i }));

    await waitFor(() =>
      expect(mockCorrect).toHaveBeenCalledWith(
        SCHOOL_ID,
        CURRICULUM_ID,
        UNIT_ID,
        "sqid-capital",
        "C",
        true,
        "en",
      ),
    );
  });

  it("calls nothing at all when the reviewer declines", async () => {
    renderPage(<AnswerReviewPage />);
    await loadedQuestions();

    fireEvent.click(screen.getByRole("radio", { name: "Debtors" }));
    await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: /^cancel$/i }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(mockCorrect).not.toHaveBeenCalled();
  });
});

// ── Marking as checked ────────────────────────────────────────────────────────

describe("marking an answer as checked", () => {
  it("validates the question by its stable id", async () => {
    renderPage(<AnswerReviewPage />);
    await loadedQuestions();

    fireEvent.click(screen.getByRole("button", { name: /mark as checked/i }));

    await waitFor(() =>
      expect(mockValidate).toHaveBeenCalledWith(
        SCHOOL_ID,
        CURRICULUM_ID,
        UNIT_ID,
        "sqid-capital",
        "en",
      ),
    );
  });
});

// ── The links that make the page reachable ────────────────────────────────────

const HEALTH: CurriculumHealthReport = {
  school_id: SCHOOL_ID,
  total_units: 1,
  healthy_count: 0,
  watch_count: 0,
  struggling_count: 1,
  no_activity_count: 0,
  general_feedback_count: 0,
  available_grades: [11],
  selected_grade: null,
  available_streams: [],
  selected_stream: null,
  units: [
    {
      unit_id: UNIT_ID,
      unit_name: "Recording Transactions",
      subject: "accountancy",
      grade: 11,
      stream: "commerce",
      curriculum_id: CURRICULUM_ID,
      health_tier: "struggling",
      first_attempt_pass_rate_pct: 38,
      avg_attempts_to_pass: 2.4,
      avg_score_pct: 51,
      feedback_count: 4,
      avg_rating: 2.5,
      recommended_action: "Review lesson content.",
    },
  ],
};

describe("the Unit Performance row's link", () => {
  beforeEach(() => {
    mockHealth.mockResolvedValue(HEALTH);
  });

  it("carries both the curriculum and the unit", async () => {
    renderPage(<UnitPerformancePage />);

    const link = await screen.findByRole("link", { name: /review answers/i });
    // Both ids: the report is the ONLY workable entry point on the demo, where
    // no curriculum any class uses is adopted — and a unit id alone is
    // ambiguous once a school has a fork.
    expect(link).toHaveAttribute("href", ANSWERS_HREF);
  });

  it("is hidden from a teacher with no curriculum capability", async () => {
    teacher = {
      teacher_id: "teacher-005",
      school_id: SCHOOL_ID,
      role: "teacher",
      capabilities: [],
      first_login: false,
    };
    renderPage(<UnitPerformancePage />);
    await screen.findByText("Recording Transactions");

    // The read is gated by `require_curriculum_view`, so this teacher would be
    // 403'd — and a link that 403s is worse than no link.
    expect(
      screen.queryByRole("link", { name: /review answers/i }),
    ).not.toBeInTheDocument();
  });

  it("is absent on a row whose curriculum could not be resolved", async () => {
    mockHealth.mockResolvedValue({
      ...HEALTH,
      units: [{ ...HEALTH.units[0], curriculum_id: null }],
    });
    renderPage(<UnitPerformancePage />);
    await screen.findByText("Recording Transactions");

    expect(
      screen.queryByRole("link", { name: /review answers/i }),
    ).not.toBeInTheDocument();
  });

  it("is on the unit editor too, with both ids", async () => {
    // The spec promises both entry points: a school that HAS adoptions reaches
    // its units through the editor, not through the report.
    mockUnitStatus.mockResolvedValue({
      adoption_id: "adopt-1",
      units: [{ unit_id: UNIT_ID, title: "Recording Transactions", overrides: [] }],
    });
    renderPage(<UnitEditPage />);

    const link = await screen.findByRole("link", { name: /review answers/i });
    expect(link).toHaveAttribute("href", ANSWERS_HREF);
  });
});
