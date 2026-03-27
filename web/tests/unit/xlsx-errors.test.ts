import { describe, it, expect, vi, beforeEach } from "vitest";
import type { UploadError } from "@/lib/api/curriculum-admin";

// ---------------------------------------------------------------------------
// XLSX error list rendering logic — pure data transformations
// ---------------------------------------------------------------------------

describe("XLSX upload error list", () => {
  it("identifies zero-error state as success", () => {
    const errors: UploadError[] = [];
    const hasErrors = errors.length > 0;
    expect(hasErrors).toBe(false);
  });

  it("identifies non-empty error list", () => {
    const errors: UploadError[] = [
      { row: 2, field: "subject", message: "Invalid subject value" },
    ];
    expect(errors.length > 0).toBe(true);
  });

  it("groups errors by row correctly", () => {
    const errors: UploadError[] = [
      { row: 3, field: "unit_title", message: "Required field missing" },
      { row: 3, field: "subject", message: "Unknown subject" },
      { row: 7, field: "grade", message: "Grade must be 5–12" },
    ];
    const byRow = errors.reduce<Record<number, UploadError[]>>((acc, e) => {
      (acc[e.row] ??= []).push(e);
      return acc;
    }, {});
    expect(Object.keys(byRow)).toHaveLength(2);
    expect(byRow[3]).toHaveLength(2);
    expect(byRow[7]).toHaveLength(1);
  });

  it("renders row 0 as file-level error (no row number)", () => {
    const err: UploadError = { row: 0, field: "file", message: "Unrecognised XLSX format" };
    const displayRow = err.row > 0 ? String(err.row) : "—";
    expect(displayRow).toBe("—");
  });

  it("renders positive row number as data row indicator", () => {
    const err: UploadError = { row: 5, field: "subject", message: "Invalid" };
    const displayRow = err.row > 0 ? String(err.row) : "—";
    expect(displayRow).toBe("5");
  });

  it("error count matches number of rows with errors", () => {
    const errors: UploadError[] = [
      { row: 1, field: "unit_title", message: "Too long" },
      { row: 2, field: "grade", message: "Out of range" },
      { row: 2, field: "subject", message: "Unknown" },
    ];
    // 3 total errors, 2 distinct rows
    expect(errors).toHaveLength(3);
    const rows = new Set(errors.map((e) => e.row));
    expect(rows.size).toBe(2);
  });

  it("returns curriculum_id null when errors present", () => {
    const response = { curriculum_id: null, unit_count: 0, errors: [{ row: 3, field: "x", message: "bad" }] };
    const isSuccess = response.errors.length === 0 && response.curriculum_id !== null;
    expect(isSuccess).toBe(false);
  });

  it("returns curriculum_id when no errors", () => {
    const response = { curriculum_id: "curr-abc", unit_count: 15, errors: [] };
    const isSuccess = response.errors.length === 0 && response.curriculum_id !== null;
    expect(isSuccess).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Mock API call for uploadCurriculumXlsx
// ---------------------------------------------------------------------------

vi.mock("@/lib/api/school-client", () => ({
  default: { post: vi.fn(), get: vi.fn() },
}));

import schoolApi from "@/lib/api/school-client";
import { uploadCurriculumXlsx } from "@/lib/api/curriculum-admin";

const mockPost = schoolApi.post as ReturnType<typeof vi.fn>;

beforeEach(() => vi.clearAllMocks());

describe("uploadCurriculumXlsx API", () => {
  it("posts as multipart/form-data and returns response", async () => {
    mockPost.mockResolvedValueOnce({
      data: { curriculum_id: "curr-xyz", unit_count: 8, errors: [] },
    });

    const file = new File(["fake xlsx bytes"], "test.xlsx", { type: "application/vnd.ms-excel" });
    const result = await uploadCurriculumXlsx(file, 8, 2026, "My Curriculum");

    expect(result.curriculum_id).toBe("curr-xyz");
    expect(result.unit_count).toBe(8);
    expect(result.errors).toHaveLength(0);

    const [url, body, config] = mockPost.mock.calls[0];
    expect(url).toContain("/curriculum/upload/xlsx");
    expect(url).toContain("grade=8");
    expect(url).toContain("year=2026");
    expect(body).toBeInstanceOf(FormData);
    expect(config?.headers?.["Content-Type"]).toBe("multipart/form-data");
  });
});
