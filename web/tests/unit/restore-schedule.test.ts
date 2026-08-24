import { describe, it, expect } from "vitest";
import {
  validateScheduledAt,
  describeSchedule,
  RESTORE_SCHEDULE_MAX_HORIZON_DAYS,
} from "@/lib/school/restore-schedule";

const NOW = new Date("2026-08-17T12:00:00.000Z");

function isoLocal(d: Date): string {
  // Mirrors what a <input type="datetime-local"> value looks like.
  return d.toISOString().slice(0, 16);
}

describe("validateScheduledAt (restore request 'Preferred time', issue #589)", () => {
  it("accepts an empty value — blank means ASAP", () => {
    expect(validateScheduledAt("", NOW)).toBeNull();
  });

  it("rejects a value in the past", () => {
    const past = new Date(NOW.getTime() - 24 * 60 * 60 * 1000);
    const msg = validateScheduledAt(isoLocal(past), NOW);
    expect(msg).not.toBeNull();
    expect(msg).toMatch(/past/i);
  });

  it("rejects a value beyond the max horizon (mirrors the 2030 report in #589)", () => {
    const farFuture = new Date(NOW.getTime() + 365 * 4 * 24 * 60 * 60 * 1000);
    const msg = validateScheduledAt(isoLocal(farFuture), NOW);
    expect(msg).not.toBeNull();
    expect(msg).toMatch(/administrator/i);
  });

  it("accepts a reasonable near-term value", () => {
    const soon = new Date(NOW.getTime() + 3 * 24 * 60 * 60 * 1000);
    expect(validateScheduledAt(isoLocal(soon), NOW)).toBeNull();
  });

  it("accepts a value exactly at the horizon boundary", () => {
    const atBoundary = new Date(
      NOW.getTime() + RESTORE_SCHEDULE_MAX_HORIZON_DAYS * 24 * 60 * 60 * 1000,
    );
    expect(validateScheduledAt(isoLocal(atBoundary), NOW)).toBeNull();
  });

  it("rejects an unparseable value", () => {
    expect(validateScheduledAt("not-a-date", NOW)).toMatch(/valid date/i);
  });
});

/**
 * describeSchedule — displaying an EXISTING request (issue #589 residue).
 *
 * validateScheduledAt above stops new requests being created beyond the
 * horizon. It cannot help rows created before it landed: the demo holds one
 * asking for 17 Nov 2030, created 3h16m before the validator merged, still
 * shown as "awaiting admin action". These pin the clamp — keep the value the
 * school stated, withdraw the promise around it.
 */
describe("describeSchedule (existing request display, issue #589)", () => {
  const AT = new Date("2026-08-24T12:00:00.000Z");

  function daysFrom(n: number): string {
    return new Date(AT.getTime() + n * 86_400_000).toISOString();
  }

  it("says ASAP when no time was given", () => {
    const d = describeSchedule(null, "submitted", AT);
    expect(d.kind).toBe("asap");
    expect(d.date).toBeNull();
    expect(d.note).toBeNull();
  });

  it("marks the real 2030 row from the demo as unschedulable", () => {
    const d = describeSchedule("2030-11-17T13:33:00Z", "submitted", AT);
    expect(d.kind).toBe("unschedulable");
    expect(d.note).toMatch(/administrator will action/i);
  });

  it("keeps the requested date rather than hiding it", () => {
    // The school asked for this. Discarding it to tidy the display would throw
    // away their stated preference — the reason we clamp instead of null.
    const d = describeSchedule("2030-11-17T13:33:00Z", "submitted", AT);
    expect(d.date?.toISOString()).toBe("2030-11-17T13:33:00.000Z");
  });

  it("leaves a within-horizon request as a normal pending one", () => {
    const d = describeSchedule(daysFrom(27), "submitted", AT);
    expect(d.kind).toBe("pending");
    expect(d.note).toBe("awaiting admin action");
  });

  it("treats the horizon boundary as still schedulable", () => {
    // Exactly at the limit is what validateScheduledAt accepts, so the display
    // must agree — flagging it would contradict a request the form just took.
    const d = describeSchedule(
      daysFrom(RESTORE_SCHEDULE_MAX_HORIZON_DAYS - 0.01),
      "submitted",
      AT,
    );
    expect(d.kind).toBe("pending");
  });

  it("does not claim a finished request is awaiting action", () => {
    for (const status of ["completed", "failed", "cancelled"]) {
      const d = describeSchedule(daysFrom(5), status, AT);
      expect(d.kind, status).toBe("settled");
      expect(d.note, status).toBeNull();
    }
  });

  it("does not flag a finished request that was scheduled far out", () => {
    // A 2030 row that already completed needs no warning — nothing is pending,
    // so a warning would be its own false statement.
    const d = describeSchedule("2030-11-17T13:33:00Z", "completed", AT);
    expect(d.kind).toBe("settled");
    expect(d.note).toBeNull();
  });

  it("reports an unparseable timestamp instead of rendering Invalid Date", () => {
    const d = describeSchedule("not-a-timestamp", "submitted", AT);
    expect(d.kind).toBe("unschedulable");
    expect(d.date).toBeNull();
    expect(d.note).toMatch(/not recorded/i);
  });
});
