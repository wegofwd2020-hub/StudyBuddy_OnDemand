/**
 * Week date formatting (Venki, 2 Sep):
 *
 *   "Weekly break down – Date is in yyyy/mm/dd format in the screen whereas in
 *    download Excel it is in dd/mm/yyyy – Is it OK ?"
 *
 * Nothing in the export converts anything: we write ISO 8601 in both places and
 * Excel re-types it, rendering per the reader's regional settings. What was
 * actually wrong is that a reader could not tell WHICH convention any of the
 * three renderings used — the chart axis said `06-15`, which is 15 June or
 * 6 December depending on who is looking.
 *
 * These pin the property that fixes it: a named month, identical for every
 * reader, and no route through `new Date()` that could shift the day.
 *
 * Run with:
 *   npm test -- week-date-format
 */

import { describe, it, expect } from "vitest";
import { formatWeekStart, formatWeekShort } from "@/lib/utils/date";

describe("week date formatting", () => {
  it("names the month so no locale can reinterpret the day", () => {
    expect(formatWeekStart("2026-06-15")).toBe("15 Jun 2026");
    expect(formatWeekShort("2026-06-15")).toBe("15 Jun");
  });

  it("is unambiguous for the date that actually reads two ways", () => {
    // From his own screenshot. `03-08-2026` is 3 August in his locale and
    // 8 March in a US one — the whole reason a bare numeric format is unsafe.
    expect(formatWeekStart("2026-08-03")).toBe("03 Aug 2026");
  });

  it("renders the day it was given, never a neighbouring one", () => {
    // The invariant that keeps a timezone out of a date-only value. Reassigning
    // `process.env.TZ` mid-process does NOT reliably re-arm Node's Date, so a
    // test that flipped TZ and asserted a string would pass without exercising
    // anything. This asserts the property instead: the day in the output is
    // always the day in the input.
    //
    // `new Date("2026-01-01")` is midnight UTC — `.getDate()` west of Greenwich
    // gives the 31st — so an implementation routed through Date breaks this for
    // every date, in exactly the offsets where nobody testing in UTC would see
    // it. Ours parses the string and cannot.
    for (const month of ["01", "02", "06", "07", "12"]) {
      for (const day of ["01", "09", "15", "28", "31"]) {
        const iso = `2026-${month}-${day}`;
        const [renderedDay, , renderedYear] = formatWeekStart(iso).split(" ");
        expect(renderedDay, iso).toBe(day);
        expect(renderedYear, iso).toBe("2026");
        expect(formatWeekShort(iso).split(" ")[0], iso).toBe(day);
      }
    }
  });

  it("handles both ends of the month table", () => {
    expect(formatWeekStart("2026-01-05")).toBe("05 Jan 2026");
    expect(formatWeekStart("2026-12-28")).toBe("28 Dec 2026");
  });

  it("returns anything it cannot parse unchanged", () => {
    // Degrading to the raw value beats rendering "Invalid Date" or a blank
    // cell — the reader can still see what the server sent.
    expect(formatWeekStart("not-a-date")).toBe("not-a-date");
    expect(formatWeekStart("2026-13-01")).toBe("2026-13-01");
    expect(formatWeekShort("")).toBe("");
  });
});
