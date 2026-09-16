import { describe, it, expect } from "vitest";
import type { CurriculumHealthReport, CurriculumHealthUnit } from "@/lib/api/reports";
import {
  buildUnitPerformanceCsv,
  unitPerformanceFilename,
} from "@/lib/reports/unit-performance-csv";

// #772 — "CSV export should group data by Grade/Stream". The export is built in
// the browser, so grouping is columns + a deterministic order: every row names
// its own grade and stream, which keeps spreadsheet filters and pivots working.

function unit(over: Partial<CurriculumHealthUnit>): CurriculumHealthUnit {
  return {
    unit_id: "U",
    unit_name: "Unit",
    subject: "Subject",
    grade: 11,
    stream: "commerce",
    health_tier: "healthy",
    first_attempt_pass_rate_pct: 80,
    avg_attempts_to_pass: 1.25,
    avg_score_pct: 75,
    feedback_count: 0,
    avg_rating: null,
    recommended_action: "",
    ...over,
  };
}

function report(units: CurriculumHealthUnit[], general = 0): CurriculumHealthReport {
  return {
    school_id: "sch-1",
    total_units: units.length,
    healthy_count: 0,
    watch_count: 0,
    struggling_count: 0,
    no_activity_count: 0,
    general_feedback_count: general,
    units,
  };
}

describe("#772 — Unit Performance CSV", () => {
  it("leads with Grade and Stream columns", () => {
    const { fields } = buildUnitPerformanceCsv(report([]));
    expect(fields.slice(0, 3)).toEqual(["Grade", "Stream", "Subject"]);
    // The existing columns are all still there.
    expect(fields).toContain("Health tier");
    expect(fields).toContain("Recommended action");
  });

  it("sorts Grade, then Stream, then Subject, then unit name", () => {
    const { rows } = buildUnitPerformanceCsv(
      report([
        unit({ unit_id: "a", grade: 12, stream: "commerce", subject: "Accountancy" }),
        unit({ unit_id: "b", grade: 11, stream: "science", subject: "Physics" }),
        unit({ unit_id: "c", grade: 11, stream: "commerce", subject: "Economics" }),
        unit({
          unit_id: "d",
          grade: 11,
          stream: "commerce",
          subject: "Accountancy",
          unit_name: "Z",
        }),
        unit({
          unit_id: "e",
          grade: 11,
          stream: "commerce",
          subject: "Accountancy",
          unit_name: "A",
        }),
      ]),
    );
    expect(rows.map((r) => r["Unit ID"])).toEqual(["e", "d", "c", "b", "a"]);
  });

  it("orders grades numerically, not as text", () => {
    const { rows } = buildUnitPerformanceCsv(
      report([unit({ unit_id: "g10", grade: 10 }), unit({ unit_id: "g9", grade: 9 })]),
    );
    expect(rows.map((r) => r["Unit ID"])).toEqual(["g9", "g10"]);
  });

  it("prints the stream as the reports label it", () => {
    const { rows } = buildUnitPerformanceCsv(
      report([
        unit({ unit_id: "c", stream: "commerce" }),
        unit({ unit_id: "u", stream: "unstreamed", grade: 12 }),
      ]),
    );
    expect(rows.map((r) => r.Stream)).toEqual(["Commerce", "No stream"]);
  });

  it("keeps units with no grade, last, with an empty Grade cell", () => {
    const { rows } = buildUnitPerformanceCsv(
      report([unit({ unit_id: "none", grade: null }), unit({ unit_id: "g5", grade: 5 })]),
    );
    expect(rows.map((r) => r["Unit ID"])).toEqual(["g5", "none"]);
    expect(rows[1].Grade).toBe("");
  });

  it("keeps the general-feedback row at the very end", () => {
    const { rows } = buildUnitPerformanceCsv(
      report([unit({ unit_id: "x", grade: null }), unit({ unit_id: "y" })], 4),
    );
    const last = rows[rows.length - 1];
    expect(last["Unit name"]).toBe("General feedback (not tied to a unit)");
    expect(last["Feedback count"]).toBe(4);
  });

  it("names the file after both filters", () => {
    expect(unitPerformanceFilename(null, null)).toBe("unit_performance.csv");
    expect(unitPerformanceFilename(11, null)).toBe("unit_performance_grade_11.csv");
    expect(unitPerformanceFilename(null, "commerce")).toBe(
      "unit_performance_commerce.csv",
    );
    expect(unitPerformanceFilename(11, "commerce")).toBe(
      "unit_performance_grade_11_commerce.csv",
    );
  });
});
