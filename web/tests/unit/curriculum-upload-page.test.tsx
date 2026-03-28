/**
 * Unit tests for section 3.14 — Curriculum Upload (`/school/curriculum`)
 * Covers TC-IDs: SCH-24, SCH-25, SCH-26, SCH-27, SCH-28, SCH-29
 *
 * Run with:
 *   npm test -- curriculum-upload-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CurriculumPage from "@/app/(school)/school/curriculum/page";
import {
  MOCK_TEACHER,
  MOCK_UPLOAD_SUCCESS,
  MOCK_UPLOAD_ERRORS,
  MOCK_UPLOAD_FILE_ERROR,
  MOCK_PIPELINE_RESPONSE,
  CURRICULUM_STRINGS,
} from "../e2e/data/curriculum-upload-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({ push: mockPush })),
}));

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => MOCK_TEACHER),
}));

const mockUploadCurriculumXlsx = vi.fn();
const mockTriggerPipeline      = vi.fn();
const mockDownloadXlsxTemplate = vi.fn();

vi.mock("@/lib/api/curriculum-admin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/curriculum-admin")>();
  return {
    ...actual,
    uploadCurriculumXlsx: (...args: unknown[]) => mockUploadCurriculumXlsx(...args),
    triggerPipeline:      (...args: unknown[]) => mockTriggerPipeline(...args),
    downloadXlsxTemplate: (...args: unknown[]) => mockDownloadXlsxTemplate(...args),
  };
});

// Mock URL for template download anchor
const _origCreateElement = document.createElement.bind(document);
vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
  if (tag === "a") {
    const el = _origCreateElement("a");
    el.click = vi.fn();
    return el;
  }
  return _origCreateElement(tag as keyof HTMLElementTagNameMap);
});
vi.stubGlobal("URL", {
  createObjectURL: vi.fn(() => "blob:template"),
  revokeObjectURL: vi.fn(),
});

beforeEach(() => {
  vi.clearAllMocks();
  mockTriggerPipeline.mockResolvedValue(MOCK_PIPELINE_RESPONSE);
  mockDownloadXlsxTemplate.mockResolvedValue(new Blob(["fake xlsx"], { type: "application/vnd.ms-excel" }));
});

// Helper: attach a fake file to the hidden input
function attachFile() {
  const fileInput = document.querySelector<HTMLInputElement>('input[type="file"]')!;
  const file = new File(["unit,subject\nCell Biology,science"], "curriculum.xlsx", { type: "application/vnd.ms-excel" });
  Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
}

// ---------------------------------------------------------------------------
// SCH-24 — Upload form renders
// ---------------------------------------------------------------------------

describe("SCH-24 — Upload form renders", () => {
  it("renders the page heading", () => {
    render(<CurriculumPage />);
    expect(
      screen.getByRole("heading", { name: CURRICULUM_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders Step 1 — Download the template card", () => {
    render(<CurriculumPage />);
    expect(screen.getByText(CURRICULUM_STRINGS.step1Heading)).toBeInTheDocument();
  });

  it("renders Step 2 — Upload curriculum card", () => {
    render(<CurriculumPage />);
    expect(screen.getByText(CURRICULUM_STRINGS.step2Heading)).toBeInTheDocument();
  });

  it("renders the Grade dropdown", () => {
    render(<CurriculumPage />);
    expect(screen.getByLabelText(CURRICULUM_STRINGS.gradeLabel)).toBeInTheDocument();
  });

  it("renders the Academic year input", () => {
    render(<CurriculumPage />);
    expect(screen.getByLabelText(CURRICULUM_STRINGS.yearLabel)).toBeInTheDocument();
  });

  it("renders the XLSX file picker", () => {
    render(<CurriculumPage />);
    expect(document.querySelector('input[type="file"]')).toBeTruthy();
  });

  it("renders the Upload & generate content button", () => {
    render(<CurriculumPage />);
    expect(screen.getByRole("button", { name: /Upload & generate content/ })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SCH-25 — Template download button works
// ---------------------------------------------------------------------------

describe("SCH-25 — Template download works", () => {
  it("clicking Download XLSX template calls downloadXlsxTemplate", async () => {
    render(<CurriculumPage />);
    fireEvent.click(screen.getByRole("button", { name: CURRICULUM_STRINGS.downloadTemplateBtn }));
    await waitFor(() => expect(mockDownloadXlsxTemplate).toHaveBeenCalledTimes(1));
  });
});

// ---------------------------------------------------------------------------
// SCH-26 — Successful upload triggers pipeline
// ---------------------------------------------------------------------------

describe("SCH-26 — Successful upload triggers pipeline and redirects", () => {
  beforeEach(() => {
    mockUploadCurriculumXlsx.mockResolvedValue(MOCK_UPLOAD_SUCCESS);
  });

  it("redirects to pipeline status page after successful upload", async () => {
    render(<CurriculumPage />);
    attachFile();
    fireEvent.click(screen.getByRole("button", { name: /Upload & generate content/ }));
    await waitFor(() =>
      expect(mockPush).toHaveBeenCalledWith(
        `/school/curriculum/pipeline/${MOCK_PIPELINE_RESPONSE.job_id}`,
      ),
    );
  });

  it("calls triggerPipeline with curriculum_id after upload", async () => {
    render(<CurriculumPage />);
    attachFile();
    fireEvent.click(screen.getByRole("button", { name: /Upload & generate content/ }));
    await waitFor(() => expect(mockTriggerPipeline).toHaveBeenCalledTimes(1));
    expect(mockTriggerPipeline).toHaveBeenCalledWith(MOCK_UPLOAD_SUCCESS.curriculum_id);
  });
});

// ---------------------------------------------------------------------------
// SCH-27 — Per-row error table on bad file
// ---------------------------------------------------------------------------

describe("SCH-27 — Per-row error table renders on upload errors", () => {
  beforeEach(() => {
    mockUploadCurriculumXlsx.mockResolvedValue(MOCK_UPLOAD_ERRORS);
  });

  it("renders error table headers", async () => {
    render(<CurriculumPage />);
    attachFile();
    fireEvent.click(screen.getByRole("button", { name: /Upload & generate content/ }));
    await waitFor(() =>
      expect(screen.getByText(CURRICULUM_STRINGS.errorRowHeader)).toBeInTheDocument(),
    );
    expect(screen.getByText(CURRICULUM_STRINGS.errorFieldHeader)).toBeInTheDocument();
    expect(screen.getByText(CURRICULUM_STRINGS.errorMessageHeader)).toBeInTheDocument();
  });

  it("renders each error's field and message", async () => {
    render(<CurriculumPage />);
    attachFile();
    fireEvent.click(screen.getByRole("button", { name: /Upload & generate content/ }));
    await waitFor(() =>
      expect(screen.getByText(MOCK_UPLOAD_ERRORS.errors[0].message)).toBeInTheDocument(),
    );
    expect(screen.getByText(MOCK_UPLOAD_ERRORS.errors[1].message)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SCH-28 — Row 0 errors shown as "—"
// ---------------------------------------------------------------------------

describe("SCH-28 — Row 0 errors show dash in error table", () => {
  it("displays '—' for row = 0 file-level errors", async () => {
    mockUploadCurriculumXlsx.mockResolvedValue(MOCK_UPLOAD_FILE_ERROR);
    render(<CurriculumPage />);
    attachFile();
    fireEvent.click(screen.getByRole("button", { name: /Upload & generate content/ }));
    await waitFor(() =>
      expect(screen.getByText(CURRICULUM_STRINGS.rowDash)).toBeInTheDocument(),
    );
  });
});

// ---------------------------------------------------------------------------
// SCH-29 — Upload button disabled during submit
// ---------------------------------------------------------------------------

describe("SCH-29 — Upload button disabled during submit", () => {
  it("shows 'Uploading…' and button is disabled while upload is in progress", async () => {
    mockUploadCurriculumXlsx.mockReturnValue(new Promise(() => {}));
    render(<CurriculumPage />);
    attachFile();
    fireEvent.click(screen.getByRole("button", { name: /Upload & generate content/ }));
    const uploadingBtn = await screen.findByText(CURRICULUM_STRINGS.uploadingBtn);
    expect(uploadingBtn.closest("button")).toBeDisabled();
  });
});
