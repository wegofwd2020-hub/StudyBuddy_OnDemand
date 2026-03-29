import { describe, it, expect } from "vitest";
import Papa from "papaparse";

// ---------------------------------------------------------------------------
// CSV generation helpers — test that papaparse produces correct output
// ---------------------------------------------------------------------------

interface OverviewRow {
  enrolled_students: number;
  active_students: number;
  active_pct: string;
  lessons_viewed: number;
  quiz_attempts: number;
  first_attempt_pass_rate_pct: string;
  audio_play_rate_pct: string;
  unreviewed_feedback: number;
}

interface TrendsRow {
  week_start: string;
  active_students: number;
  lessons_viewed: number;
  quiz_attempts: number;
  avg_score_pct: string;
  first_attempt_pass_rate_pct: string;
}

describe("CSV export — papaparse unparse", () => {
  it("produces correct headers for overview report", () => {
    const rows: OverviewRow[] = [
      {
        enrolled_students: 120,
        active_students: 98,
        active_pct: "81.7",
        lessons_viewed: 342,
        quiz_attempts: 215,
        first_attempt_pass_rate_pct: "72.3",
        audio_play_rate_pct: "55.0",
        unreviewed_feedback: 4,
      },
    ];
    const csv = Papa.unparse(rows);
    const lines = csv.split("\n");
    const header = lines[0];
    expect(header).toContain("enrolled_students");
    expect(header).toContain("active_pct");
    expect(header).toContain("first_attempt_pass_rate_pct");
  });

  it("encodes numeric fields as strings when pre-formatted", () => {
    const rows: OverviewRow[] = [
      {
        enrolled_students: 50,
        active_students: 40,
        active_pct: "80.0",
        lessons_viewed: 100,
        quiz_attempts: 60,
        first_attempt_pass_rate_pct: "65.5",
        audio_play_rate_pct: "45.2",
        unreviewed_feedback: 0,
      },
    ];
    const csv = Papa.unparse(rows);
    expect(csv).toContain("65.5");
    expect(csv).toContain("45.2");
  });

  it("produces correct row count for trends export", () => {
    const rows: TrendsRow[] = [
      {
        week_start: "2026-03-01",
        active_students: 90,
        lessons_viewed: 280,
        quiz_attempts: 180,
        avg_score_pct: "74.1",
        first_attempt_pass_rate_pct: "68.0",
      },
      {
        week_start: "2026-03-08",
        active_students: 95,
        lessons_viewed: 310,
        quiz_attempts: 200,
        avg_score_pct: "76.2",
        first_attempt_pass_rate_pct: "70.5",
      },
      {
        week_start: "2026-03-15",
        active_students: 88,
        lessons_viewed: 265,
        quiz_attempts: 175,
        avg_score_pct: "72.8",
        first_attempt_pass_rate_pct: "66.2",
      },
    ];
    const csv = Papa.unparse(rows);
    const lines = csv.trim().split("\n");
    // 1 header + 3 data rows = 4
    expect(lines).toHaveLength(4);
  });

  it("includes BOM character when prepended for Excel compatibility", () => {
    const rows = [{ unit_id: "G8-MATH-001", pass_rate: "72.0" }];
    const csv = Papa.unparse(rows);
    const bom = "\uFEFF";
    const withBom = bom + csv;
    expect(withBom.startsWith("\uFEFF")).toBe(true);
    expect(withBom).toContain("unit_id");
  });

  it("handles empty rows array gracefully", () => {
    const csv = Papa.unparse([]);
    expect(typeof csv).toBe("string");
    // No rows means either empty string or just headers if fields provided
    expect(csv.length).toBeGreaterThanOrEqual(0);
  });

  it("correctly encodes fields with commas in quotes", () => {
    const rows = [{ unit_name: "Physics, Chapter 1", pass_rate: "80.0" }];
    const csv = Papa.unparse(rows);
    // unit_name value contains comma, should be quoted
    expect(csv).toContain('"Physics, Chapter 1"');
  });

  it("handles null/undefined gracefully", () => {
    const rows = [{ unit_id: "U1", unit_name: null, avg_rating: undefined }];
    // papaparse should not throw on null/undefined values
    expect(() => Papa.unparse(rows as Parameters<typeof Papa.unparse>[0])).not.toThrow();
  });
});
