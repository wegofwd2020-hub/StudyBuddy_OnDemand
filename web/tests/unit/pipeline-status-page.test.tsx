/**
 * Unit tests for section 3.15 — Pipeline Status (`/school/curriculum/pipeline/[job_id]`)
 * Covers TC-IDs: SCH-30, SCH-31, SCH-32, SCH-33, SCH-34
 *
 * Run with:
 *   npm test -- pipeline-status-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import PipelineStatusPage from "@/app/(school)/school/curriculum/pipeline/[job_id]/page";
import {
  MOCK_JOB_ID,
  MOCK_JOB_RUNNING,
  MOCK_JOB_DONE,
  MOCK_JOB_FAILED,
  PIPELINE_STRINGS,
} from "../e2e/data/pipeline-status-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  useParams: vi.fn(() => ({ job_id: MOCK_JOB_ID })),
}));

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

// ---------------------------------------------------------------------------
// SCH-30 — Progress bar renders while running
// ---------------------------------------------------------------------------

describe("SCH-30 — Progress bar renders", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_JOB_RUNNING, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<PipelineStatusPage />);
    expect(
      screen.getByRole("heading", { name: PIPELINE_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders the back link to curriculum", () => {
    render(<PipelineStatusPage />);
    const link = screen.getByRole("link", { name: PIPELINE_STRINGS.backLink });
    expect(link).toBeInTheDocument();
    expect(link.getAttribute("href")).toBe("/school/curriculum");
  });

  it("renders the built/failed/total summary", () => {
    render(<PipelineStatusPage />);
    expect(
      screen.getByText(
        PIPELINE_STRINGS.builtSummary(
          MOCK_JOB_RUNNING.built,
          MOCK_JOB_RUNNING.failed,
          MOCK_JOB_RUNNING.total,
        ),
      ),
    ).toBeInTheDocument();
  });

  it("renders the progress percentage", () => {
    render(<PipelineStatusPage />);
    expect(
      screen.getByText(PIPELINE_STRINGS.progressPct(MOCK_JOB_RUNNING.progress_pct)),
    ).toBeInTheDocument();
  });

  it("renders a progress bar with blue colour while running", () => {
    const { container } = render(<PipelineStatusPage />);
    const bar = container.querySelector("div.bg-blue-500");
    expect(bar).toBeTruthy();
  });

  it("renders the job_id in monospace font", () => {
    render(<PipelineStatusPage />);
    expect(screen.getByText(MOCK_JOB_ID)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SCH-31 — Progress bar auto-updates (refetchInterval configured)
// ---------------------------------------------------------------------------

describe("SCH-31 — Polling configured for running job", () => {
  it("passes refetchInterval option that returns 5000 for running status", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_JOB_RUNNING, isLoading: false });
    render(<PipelineStatusPage />);
    const callArgs = mockUseQuery.mock.calls[0][0];
    // refetchInterval is a function in the page
    expect(typeof callArgs.refetchInterval).toBe("function");
    // Simulate a running state query object
    const fakeQuery = { state: { data: MOCK_JOB_RUNNING } };
    expect(callArgs.refetchInterval(fakeQuery)).toBe(5_000);
  });

  it("shows 'Refreshing every 5 seconds…' while job is running", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_JOB_RUNNING, isLoading: false });
    render(<PipelineStatusPage />);
    expect(screen.getByText(PIPELINE_STRINGS.pollingMsg)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SCH-32 — Done state shows green bar + success message
// ---------------------------------------------------------------------------

describe("SCH-32 — Done state shows green progress bar", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_JOB_DONE, isLoading: false });
  });

  it("renders progress bar with green colour when done", () => {
    const { container } = render(<PipelineStatusPage />);
    const bar = container.querySelector("div.bg-green-500");
    expect(bar).toBeTruthy();
  });

  it("shows content generation complete message", () => {
    render(<PipelineStatusPage />);
    expect(screen.getByText(PIPELINE_STRINGS.doneMsg)).toBeInTheDocument();
  });

  it("renders Back to curriculum link after job is done", () => {
    render(<PipelineStatusPage />);
    const links = screen.getAllByRole("link", { name: "Back to curriculum" });
    expect(links.length).toBeGreaterThanOrEqual(1);
  });

  it("does NOT show refreshing message when done", () => {
    render(<PipelineStatusPage />);
    expect(screen.queryByText(PIPELINE_STRINGS.pollingMsg)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// SCH-33 — Failed state shows red indicator + failure count
// ---------------------------------------------------------------------------

describe("SCH-33 — Failed state shows red indicator", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_JOB_FAILED, isLoading: false });
  });

  it("renders progress bar with red colour when failed", () => {
    const { container } = render(<PipelineStatusPage />);
    const bar = container.querySelector("div.bg-red-400");
    expect(bar).toBeTruthy();
  });

  it("shows pipeline failed message", () => {
    render(<PipelineStatusPage />);
    expect(screen.getByText(PIPELINE_STRINGS.failedMsg)).toBeInTheDocument();
  });

  it("shows the failure count", () => {
    render(<PipelineStatusPage />);
    expect(
      screen.getByText(
        PIPELINE_STRINGS.builtSummary(
          MOCK_JOB_FAILED.built,
          MOCK_JOB_FAILED.failed,
          MOCK_JOB_FAILED.total,
        ),
      ),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SCH-34 — Polling stops on done/failed
// ---------------------------------------------------------------------------

describe("SCH-34 — Polling stops on terminal state", () => {
  it("refetchInterval returns false for done status", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_JOB_DONE, isLoading: false });
    render(<PipelineStatusPage />);
    const callArgs = mockUseQuery.mock.calls[0][0];
    const fakeQuery = { state: { data: MOCK_JOB_DONE } };
    expect(callArgs.refetchInterval(fakeQuery)).toBe(false);
  });

  it("refetchInterval returns false for failed status", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_JOB_FAILED, isLoading: false });
    render(<PipelineStatusPage />);
    const callArgs = mockUseQuery.mock.calls[0][0];
    const fakeQuery = { state: { data: MOCK_JOB_FAILED } };
    expect(callArgs.refetchInterval(fakeQuery)).toBe(false);
  });
});
