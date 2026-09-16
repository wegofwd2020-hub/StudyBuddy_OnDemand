/**
 * Date formatting (#759) — dd/mm/yyyy with 24-hour times, everywhere.
 *
 * Replaces week-date-format.test.ts (named-month format) now that the product
 * decision is a numeric day-first format instead: `formatDate`, `formatTime`,
 * `formatDateTime`, `formatDayMonth`.
 *
 * Run with:
 *   npx vitest run date-format-759
 */

import { describe, it, expect } from "vitest";
import { formatDate, formatDateTime, formatTime, formatDayMonth } from "@/lib/utils/date";

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

describe("formatDate", () => {
  it("formats a date-only string as dd/mm/yyyy", () => {
    expect(formatDate("2026-06-15")).toBe("15/06/2026");
    expect(formatDate("2026-08-03")).toBe("03/08/2026");
  });

  it("zero-pads single-digit day and month", () => {
    expect(formatDate("2026-01-05")).toBe("05/01/2026");
    expect(formatDate("2026-09-01")).toBe("01/09/2026");
  });

  it("never shifts the day for a date-only string, for any month/day combination", () => {
    // A date-only value has no timezone. Routing it through `new Date(iso)`
    // parses it as midnight UTC, so `.getDate()` west of Greenwich returns the
    // previous day — this asserts the day in the output always matches the
    // day in the input, which only holds if the string is parsed directly.
    for (const month of ["01", "02", "06", "07", "12"]) {
      for (const day of ["01", "09", "15", "28", "31"]) {
        const iso = `2026-${month}-${day}`;
        expect(formatDate(iso), iso).toBe(`${day}/${month}/2026`);
      }
    }
  });

  it("formats a full ISO timestamp in the viewer's local timezone", () => {
    const iso = "2026-08-05T06:00:00Z";
    const d = new Date(iso);
    const expected = `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
    expect(formatDate(iso)).toBe(expected);
  });

  it("formats an epoch number using local getters", () => {
    const epoch = 1765000000000;
    const d = new Date(epoch);
    const expected = `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
    expect(formatDate(epoch)).toBe(expected);
  });

  it("formats a Date instance using local getters", () => {
    const d = new Date(2026, 5, 15, 10, 30);
    expect(formatDate(d)).toBe("15/06/2026");
  });

  it("returns an empty string for null or undefined", () => {
    expect(formatDate(null)).toBe("");
    expect(formatDate(undefined)).toBe("");
  });

  it("returns an unparseable string unchanged rather than 'Invalid Date'", () => {
    expect(formatDate("not-a-date")).toBe("not-a-date");
    expect(formatDate("2026-13-01")).toBe("2026-13-01");
  });
});

describe("formatTime", () => {
  it("formats a full ISO timestamp as 24-hour HH:MM in local time", () => {
    const iso = "2026-08-05T14:05:00Z";
    const d = new Date(iso);
    const expected = `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
    expect(formatTime(iso)).toBe(expected);
  });

  it("zero-pads hour and minute", () => {
    const d = new Date(2026, 0, 1, 9, 7);
    expect(formatTime(d)).toBe("09:07");
  });

  it("falls back to formatDate output for a date-only string (no fabricated 00:00)", () => {
    expect(formatTime("2026-06-15")).toBe("15/06/2026");
  });

  it("returns an empty string for null or undefined", () => {
    expect(formatTime(null)).toBe("");
    expect(formatTime(undefined)).toBe("");
  });

  it("returns an unparseable string unchanged", () => {
    expect(formatTime("not-a-date")).toBe("not-a-date");
  });
});

describe("formatDateTime", () => {
  it("formats date + 24-hour time together as dd/mm/yyyy HH:MM", () => {
    const d = new Date(2026, 8, 14, 14, 5);
    expect(formatDateTime(d)).toBe("14/09/2026 14:05");
  });

  it("falls back to formatDate output for a date-only string (no fabricated 00:00)", () => {
    expect(formatDateTime("2026-06-15")).toBe("15/06/2026");
  });

  it("formats an ISO timestamp string using local getters for both parts", () => {
    const iso = "2026-08-05T06:09:00Z";
    const d = new Date(iso);
    const expected =
      `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()} ` +
      `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
    expect(formatDateTime(iso)).toBe(expected);
  });

  it("formats an epoch number", () => {
    const epoch = 1765000000000;
    const d = new Date(epoch);
    const expected =
      `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()} ` +
      `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
    expect(formatDateTime(epoch)).toBe(expected);
  });

  it("returns an empty string for null or undefined", () => {
    expect(formatDateTime(null)).toBe("");
    expect(formatDateTime(undefined)).toBe("");
  });

  it("returns an unparseable string unchanged", () => {
    expect(formatDateTime("not-a-date")).toBe("not-a-date");
  });
});

describe("formatDayMonth", () => {
  it("formats a date-only string as dd/mm, for chart axes", () => {
    expect(formatDayMonth("2026-06-15")).toBe("15/06");
  });

  it("zero-pads day and month", () => {
    expect(formatDayMonth("2026-01-05")).toBe("05/01");
  });

  it("never shifts the day for any date-only string", () => {
    for (const month of ["01", "06", "12"]) {
      for (const day of ["01", "09", "28", "31"]) {
        const iso = `2026-${month}-${day}`;
        expect(formatDayMonth(iso), iso).toBe(`${day}/${month}`);
      }
    }
  });

  it("returns an empty string for null or undefined", () => {
    expect(formatDayMonth(null)).toBe("");
    expect(formatDayMonth(undefined)).toBe("");
  });

  it("returns an unparseable string unchanged", () => {
    expect(formatDayMonth("not-a-date")).toBe("not-a-date");
  });
});
