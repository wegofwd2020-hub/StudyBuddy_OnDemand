/**
 * The quiz page when the lesson has not been read — product decision 2026-09-01.
 *
 * The backend now refuses the quiz until the student has opened the lesson. The
 * page has to turn that refusal into a way forward, and there is one failure mode
 * that matters more than the wording:
 *
 * The page opens the SESSION first and fetches the quiz for it (#567), and that
 * call's rejection used to be swallowed by `.catch(() => {})`. A swallowed 403
 * leaves `sessionId` null forever, which renders the loading skeleton — a screen
 * that never resolves and never explains itself. A dead end is worse than an
 * error message, so the first test here is about that, not about copy.
 *
 * Run with: docker compose exec -T web npx vitest run quiz-lesson-gate
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { AxiosError, AxiosHeaders } from "axios";
import QuizPage from "@/app/(student)/quiz/[unit_id]/page";
import * as progressApi from "@/lib/api/progress";
import { contentErrorMessage } from "@/lib/content-error";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({ push: vi.fn(), replace: vi.fn() })),
  useSearchParams: vi.fn(() => new URLSearchParams()),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api/progress", async (importOriginal) => {
  const actual = await importOriginal<typeof progressApi>();
  return { ...actual, startSession: vi.fn() };
});

const mockUseQuiz = vi.fn();
vi.mock("@/lib/hooks/useQuiz", () => ({
  useQuiz: (...args: unknown[]) => mockUseQuiz(...args),
}));

vi.mock("@/components/student/OfflineBanner", () => ({
  OfflineBanner: () => null,
}));

const startSession = vi.mocked(progressApi.startSession);

/** A 403 shaped exactly like the one the API returns for this gate. */
function lessonRequiredError(): AxiosError {
  const err = new AxiosError("Forbidden");
  err.response = {
    status: 403,
    statusText: "Forbidden",
    data: {
      error: "lesson_required",
      detail: "Read the lesson first, then come back for the quiz.",
    },
    headers: new AxiosHeaders(),
    config: { headers: new AxiosHeaders() },
  };
  return err;
}

const UNIT = "G10-MATH-001";

/** The page reads its params with `use()`, which SUSPENDS on first read.
 *
 *  Two things this has to get right, both learned by getting them wrong:
 *  a Suspense boundary, or the first test in the file renders an empty tree
 *  while the rest pass on the already-settled promise (an order-dependent
 *  green); and ONE promise per render tree rather than one per render — a fresh
 *  `Promise.resolve()` inside the JSX is a new promise on every re-render, so
 *  `use()` suspends forever and nothing ever appears. */
/** A promise React can read WITHOUT suspending.
 *
 *  `use()` checks for the `status`/`value` fields React itself attaches to a
 *  tracked promise and returns synchronously when they are present. A plain
 *  `Promise.resolve()` has neither, so the first render in the file suspends —
 *  and with no boundary that is an empty tree, while a boundary with a null
 *  fallback never recovered here at all. Pre-marking it settled sidesteps the
 *  whole question: the page renders on the first pass, which is what these tests
 *  are actually about. */
function settledParams(unit_id: string): Promise<{ unit_id: string }> {
  const p = Promise.resolve({ unit_id }) as Promise<{ unit_id: string }> & {
    status?: string;
    value?: { unit_id: string };
  };
  p.status = "fulfilled";
  p.value = { unit_id };
  return p;
}

function renderPage() {
  return render(<QuizPage params={settledParams(UNIT)} />);
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseQuiz.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
  });
});

describe("quiz page — lesson gate", () => {
  it("explains the gate instead of leaving a skeleton that never resolves", async () => {
    // The regression this file exists for. `.catch(() => {})` on the session
    // start would leave the page loading forever with nothing on screen.
    startSession.mockRejectedValue(lessonRequiredError());

    renderPage();

    expect(await screen.findByText(/lesson first/i)).toBeInTheDocument();
  });

  it("offers a route to the lesson, not just a message", async () => {
    // A student who lands here has not made a mistake — they arrived in the
    // wrong order. Telling them so without a way onward is a cul-de-sac.
    startSession.mockRejectedValue(lessonRequiredError());

    renderPage();

    const link = await screen.findByRole("link", { name: /go to the lesson/i });
    expect(link).toHaveAttribute("href", `/lesson/${UNIT}`);
  });

  it("also catches the gate when it fires from the quiz fetch", async () => {
    // The gate is enforced on BOTH endpoints, so the page must recognise it from
    // either. Handling only the session path would leave a client that already
    // holds a session showing a raw error.
    startSession.mockResolvedValue({
      session_id: "s-1",
      attempt_number: 1,
    } as Awaited<ReturnType<typeof progressApi.startSession>>);
    mockUseQuiz.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: lessonRequiredError(),
    });

    renderPage();

    expect(await screen.findByText(/lesson first/i)).toBeInTheDocument();
  });

  it("does not show the gate for an ordinary failure", async () => {
    // The negative direction: a page that showed "read the lesson first" for
    // every error would pass all three tests above and mislead every student
    // who hits a real outage.
    startSession.mockRejectedValue(new AxiosError("Network Error"));

    renderPage();

    expect(await screen.findByText(/something went wrong/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /go to the lesson/i })).toBeNull();
  });
});

describe("contentErrorMessage", () => {
  it("recognises the gate only on its own error code", () => {
    expect(contentErrorMessage(lessonRequiredError()).lessonRequired).toBe(true);

    // A 403 that is NOT this gate (a blocked unit, say) must not be dressed up
    // as one — that would send a student to a lesson that will not help.
    const blocked = new AxiosError("Forbidden");
    blocked.response = {
      status: 403,
      statusText: "Forbidden",
      data: { error: "content_blocked", detail: "Blocked." },
      headers: new AxiosHeaders(),
      config: { headers: new AxiosHeaders() },
    };
    expect(contentErrorMessage(blocked).lessonRequired).toBeUndefined();
  });
});
