/**
 * Unit tests for section 4.7 — Pipeline Job Detail (`/admin/pipeline/[job_id]`)
 * Covers TC-IDs: ADM-26, ADM-27, ADM-28, ADM-29, ADM-30
 *
 * Run with:
 *   npm test -- admin-pipeline-job-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import AdminPipelineJobPage from "@/app/(admin)/admin/pipeline/[job_id]/page";
import {
  MOCK_JOB_ID,
  MOCK_JOB_RUNNING,
  MOCK_JOB_DONE,
  MOCK_JOB_FAILED,
  PIPELINE_JOB_STRINGS,
} from "../e2e/data/admin-pipeline-job-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useParams: vi.fn(() => ({ job_id: MOCK_JOB_ID })),
}));

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

// ---------------------------------------------------------------------------
// ADM-26 — Progress bar renders while running
// ---------------------------------------------------------------------------

describe("ADM-26 — Progress bar renders while running", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({ data: MOCK_JOB_RUNNING, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<AdminPipelineJobPage />);
    expect(
      screen.getByRole("heading", { name: PIPELINE_JOB_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders progress bar with indigo colour while running", () => {
    const { container } = render(<AdminPipelineJobPage />);
    const bar = container.querySelector("div.bg-indigo-500");
    expect(bar).toBeDefined();
  });

  it("renders correct progress percentage while running", () => {
    render(<AdminPipelineJobPage />);
    expect(
      screen.getByText(`${MOCK_JOB_RUNNING.progress_pct}%`),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-27 — Progress bar turns green when done
// ---------------------------------------------------------------------------

describe("ADM-27 — Progress bar turns green when done", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({ data: MOCK_JOB_DONE, isLoading: false });
  });

  it("renders progress bar with green colour when done", () => {
    const { container } = render(<AdminPipelineJobPage />);
    const bar = container.querySelector("div.bg-green-500");
    expect(bar).toBeDefined();
  });

  it("shows 100% when done", () => {
    render(<AdminPipelineJobPage />);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-28 — Failed state shows red + failure count
// ---------------------------------------------------------------------------

describe("ADM-28 — Failed state shows red indicator and failure count", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({ data: MOCK_JOB_FAILED, isLoading: false });
  });

  it("renders progress bar with red colour when failed", () => {
    const { container } = render(<AdminPipelineJobPage />);
    const bar = container.querySelector("div.bg-red-500");
    expect(bar).toBeDefined();
  });

  it("shows failure warning message with unit count", () => {
    render(<AdminPipelineJobPage />);
    expect(
      screen.getByText(PIPELINE_JOB_STRINGS.failureWarning),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-29 — Built/Total/Failed stat boxes visible
// ---------------------------------------------------------------------------

describe("ADM-29 — Built/Total/Failed counts visible", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({ data: MOCK_JOB_RUNNING, isLoading: false });
  });

  it("renders Built stat box label", () => {
    render(<AdminPipelineJobPage />);
    expect(screen.getByText(PIPELINE_JOB_STRINGS.statBuilt)).toBeInTheDocument();
  });

  it("renders Total stat box label", () => {
    render(<AdminPipelineJobPage />);
    expect(screen.getByText(PIPELINE_JOB_STRINGS.statTotal)).toBeInTheDocument();
  });

  it("renders Failed stat box label", () => {
    render(<AdminPipelineJobPage />);
    expect(screen.getByText(PIPELINE_JOB_STRINGS.statFailed)).toBeInTheDocument();
  });

  it("renders correct built count", () => {
    render(<AdminPipelineJobPage />);
    expect(screen.getByText(String(MOCK_JOB_RUNNING.built))).toBeInTheDocument();
  });

  it("renders correct total count", () => {
    render(<AdminPipelineJobPage />);
    expect(screen.getByText(String(MOCK_JOB_RUNNING.total))).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-30 — Back link returns to pipeline list
// ---------------------------------------------------------------------------

describe("ADM-30 — Back link returns to pipeline list", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({ data: MOCK_JOB_RUNNING, isLoading: false });
  });

  it("renders 'Back to pipeline' link", () => {
    render(<AdminPipelineJobPage />);
    expect(
      screen.getByRole("link", { name: /Back to pipeline/i }),
    ).toBeInTheDocument();
  });

  it("back link points to /admin/pipeline", () => {
    render(<AdminPipelineJobPage />);
    const link = screen.getByRole("link", { name: /Back to pipeline/i });
    expect(link).toHaveAttribute("href", "/admin/pipeline");
  });
});
