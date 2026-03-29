/**
 * Unit tests for section 4.6 — Pipeline Trigger (`/admin/pipeline/trigger`)
 * Covers TC-IDs: ADM-21, ADM-22, ADM-23, ADM-24, ADM-25
 *
 * Run with:
 *   npm test -- admin-pipeline-trigger-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdminPipelineTriggerPage from "@/app/(admin)/admin/pipeline/trigger/page";
import {
  MOCK_PRODUCT_ADMIN,
  MOCK_DEVELOPER,
  MOCK_NEW_JOB,
  TRIGGER_STRINGS,
} from "../e2e/data/admin-pipeline-trigger-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockPush = vi.fn();
const mockBack = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({ push: mockPush, back: mockBack })),
}));

const mockUseAdmin = vi.fn();
vi.mock("@/lib/hooks/useAdmin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/hooks/useAdmin")>();
  return { ...actual, useAdmin: vi.fn(() => mockUseAdmin()) };
});

const mockTrigger = vi.fn();
vi.mock("@/lib/api/admin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/admin")>();
  return {
    ...actual,
    triggerAdminPipeline: (...args: unknown[]) => mockTrigger(...args),
  };
});

// ---------------------------------------------------------------------------
// ADM-21 — Trigger form renders for product_admin
// ---------------------------------------------------------------------------

describe("ADM-21 — Trigger form renders for product_admin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
  });

  it("renders the page heading", () => {
    render(<AdminPipelineTriggerPage />);
    expect(
      screen.getByRole("heading", { name: TRIGGER_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders the Grade dropdown", () => {
    render(<AdminPipelineTriggerPage />);
    expect(screen.getByText(TRIGGER_STRINGS.gradeLabel)).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("renders the Languages input", () => {
    render(<AdminPipelineTriggerPage />);
    expect(screen.getByText(TRIGGER_STRINGS.languagesLabel)).toBeInTheDocument();
  });

  it("renders the Force regenerate checkbox", () => {
    render(<AdminPipelineTriggerPage />);
    expect(screen.getByLabelText(TRIGGER_STRINGS.forceLabel)).toBeInTheDocument();
  });

  it("renders the Trigger Job button", () => {
    render(<AdminPipelineTriggerPage />);
    expect(
      screen.getByRole("button", { name: TRIGGER_STRINGS.triggerBtn }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-22 — Access denied for developer role
// ---------------------------------------------------------------------------

describe("ADM-22 — Access denied for developer role", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
  });

  it("shows 'Access denied' message for developer role", () => {
    render(<AdminPipelineTriggerPage />);
    expect(screen.getByText(TRIGGER_STRINGS.accessDenied)).toBeInTheDocument();
  });

  it("does NOT render the trigger form for developer role", () => {
    render(<AdminPipelineTriggerPage />);
    expect(screen.queryByRole("button", { name: TRIGGER_STRINGS.triggerBtn })).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// ADM-23 — Successful trigger redirects to job detail
// ---------------------------------------------------------------------------

describe("ADM-23 — Successful trigger redirects to job", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockTrigger.mockResolvedValue(MOCK_NEW_JOB);
  });

  it("redirects to /admin/pipeline/{job_id} after successful trigger", async () => {
    render(<AdminPipelineTriggerPage />);
    fireEvent.click(screen.getByRole("button", { name: TRIGGER_STRINGS.triggerBtn }));
    await waitFor(() =>
      expect(mockPush).toHaveBeenCalledWith(`/admin/pipeline/${MOCK_NEW_JOB.job_id}`),
    );
  });
});

// ---------------------------------------------------------------------------
// ADM-24 — Error shown on trigger failure
// ---------------------------------------------------------------------------

describe("ADM-24 — Error shown on trigger failure", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockTrigger.mockRejectedValue(new Error("500 Server Error"));
  });

  it("shows error message when trigger API fails", async () => {
    render(<AdminPipelineTriggerPage />);
    fireEvent.click(screen.getByRole("button", { name: TRIGGER_STRINGS.triggerBtn }));
    expect(await screen.findByText(TRIGGER_STRINGS.errorMsg)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-25 — Force checkbox overrides existing content
// ---------------------------------------------------------------------------

describe("ADM-25 — Force regenerate checkbox", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockTrigger.mockResolvedValue(MOCK_NEW_JOB);
  });

  it("calls triggerAdminPipeline with force=true when checkbox checked", async () => {
    render(<AdminPipelineTriggerPage />);
    fireEvent.click(screen.getByLabelText(TRIGGER_STRINGS.forceLabel));
    fireEvent.click(screen.getByRole("button", { name: TRIGGER_STRINGS.triggerBtn }));
    await waitFor(() => expect(mockTrigger).toHaveBeenCalledTimes(1));
    expect(mockTrigger).toHaveBeenCalledWith(
      expect.any(Number),
      expect.any(String),
      true, // force=true
    );
  });

  it("calls triggerAdminPipeline with force=false when checkbox unchecked", async () => {
    render(<AdminPipelineTriggerPage />);
    // Do NOT click the checkbox (default is unchecked)
    fireEvent.click(screen.getByRole("button", { name: TRIGGER_STRINGS.triggerBtn }));
    await waitFor(() => expect(mockTrigger).toHaveBeenCalledTimes(1));
    expect(mockTrigger).toHaveBeenCalledWith(
      expect.any(Number),
      expect.any(String),
      false,
    );
  });
});
