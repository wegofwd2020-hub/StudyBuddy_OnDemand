/**
 * Unit tests for section 4.5 — Pipeline List (`/admin/pipeline`)
 * Covers TC-IDs: ADM-15, ADM-16, ADM-17, ADM-18, ADM-19
 *
 * Run with:
 *   npm test -- admin-pipeline-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import AdminPipelinePage from "@/app/(admin)/admin/pipeline/page";
import {
  MOCK_JOBS,
  PIPELINE_LIST_STRINGS,
} from "../e2e/data/admin-pipeline-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

beforeEach(() => {
  vi.clearAllMocks();
  mockUseQuery.mockReturnValue({ data: MOCK_JOBS, isLoading: false, refetch: vi.fn() });
});

// ---------------------------------------------------------------------------
// ADM-15 — Pipeline page heading renders
// ---------------------------------------------------------------------------

describe("ADM-15 — Pipeline page heading renders", () => {
  it("renders 'Pipeline Jobs' heading", () => {
    render(<AdminPipelinePage />);
    expect(
      screen.getByRole("heading", { name: PIPELINE_LIST_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-16 — Trigger job button/link visible
// ---------------------------------------------------------------------------

describe("ADM-16 — Trigger job link visible", () => {
  it("renders the 'Trigger job' link", () => {
    render(<AdminPipelinePage />);
    expect(
      screen.getByRole("link", { name: /Trigger job/i }),
    ).toBeInTheDocument();
  });

  it("Trigger job link points to /admin/pipeline/trigger", () => {
    render(<AdminPipelinePage />);
    const link = screen.getByRole("link", { name: /Trigger job/i });
    expect(link).toHaveAttribute("href", "/admin/pipeline/trigger");
  });
});

// ---------------------------------------------------------------------------
// ADM-17 — Jobs table columns render
// ---------------------------------------------------------------------------

describe("ADM-17 — Jobs table renders with correct columns", () => {
  it("renders Job ID column header", () => {
    render(<AdminPipelinePage />);
    expect(screen.getByText(PIPELINE_LIST_STRINGS.colJobId)).toBeInTheDocument();
  });

  it("renders Curriculum column header", () => {
    render(<AdminPipelinePage />);
    expect(screen.getByText(PIPELINE_LIST_STRINGS.colCurriculum)).toBeInTheDocument();
  });

  it("renders Status column header", () => {
    render(<AdminPipelinePage />);
    expect(screen.getByText(PIPELINE_LIST_STRINGS.colStatus)).toBeInTheDocument();
  });

  it("renders Progress column header", () => {
    render(<AdminPipelinePage />);
    expect(screen.getByText(PIPELINE_LIST_STRINGS.colProgress)).toBeInTheDocument();
  });

  it("renders curriculum_id value in table", () => {
    render(<AdminPipelinePage />);
    expect(screen.getByText(MOCK_JOBS.jobs[0].curriculum_id)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-18 — Status badges are colour-coded
// ---------------------------------------------------------------------------

describe("ADM-18 — Status badge colour classes", () => {
  it("running badge has blue colour class", () => {
    const { container } = render(<AdminPipelinePage />);
    const badge = Array.from(container.querySelectorAll("span")).find(
      (el) => el.textContent === PIPELINE_LIST_STRINGS.statusRunning,
    );
    expect(badge?.className).toContain("text-blue");
  });

  it("done badge has green colour class", () => {
    const { container } = render(<AdminPipelinePage />);
    const badge = Array.from(container.querySelectorAll("span")).find(
      (el) => el.textContent === PIPELINE_LIST_STRINGS.statusDone,
    );
    expect(badge?.className).toContain("text-green");
  });

  it("failed badge has red colour class", () => {
    const { container } = render(<AdminPipelinePage />);
    const badge = Array.from(container.querySelectorAll("span")).find(
      (el) => el.textContent === PIPELINE_LIST_STRINGS.statusFailed,
    );
    expect(badge?.className).toContain("text-red");
  });

  it("queued badge has gray colour class", () => {
    const { container } = render(<AdminPipelinePage />);
    const badge = Array.from(container.querySelectorAll("span")).find(
      (el) => el.textContent === PIPELINE_LIST_STRINGS.statusQueued,
    );
    expect(badge?.className).toContain("text-gray");
  });
});

// ---------------------------------------------------------------------------
// ADM-19 — Job ID link navigates to detail page
// ---------------------------------------------------------------------------

describe("ADM-19 — Job ID links navigate to detail", () => {
  it("job ID link points to /admin/pipeline/{job_id}", () => {
    render(<AdminPipelinePage />);
    const job = MOCK_JOBS.jobs[0];
    const shortId = job.job_id.slice(0, 8);
    const link = screen.getByRole("link", { name: new RegExp(shortId) });
    expect(link).toHaveAttribute("href", `/admin/pipeline/${job.job_id}`);
  });
});
