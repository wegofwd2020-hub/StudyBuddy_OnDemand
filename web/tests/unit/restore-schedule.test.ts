/**
 * Restore-request "Preferred time" display (issue #589).
 *
 * The validator (#595) bounded new requests to a 30-day horizon, but rows
 * created before it landed still display a date nothing will honour. The demo
 * holds one asking for 17 Nov 2030 — created 3h16m before the fix merged — and
 * shows it as "awaiting admin action".
 *
 * These tests pin the clamp: keep the value the school stated, withdraw the
 * promise around it.
 */

import { describe, expect, it } from "vitest";

import {
  RESTORE_SCHEDULE_MAX_HORIZON_DAYS,
  describeSchedule,
} from "@/lib/school/restore-schedule";

// Fixed "now" so these never drift with the wall clock.
const NOW = new Date("2026-08-24T12:00:00Z");

function daysFromNow(n: number): string {
  return new Date(NOW.getTime() + n * 86_400_000).toISOString();
}

describe("describeSchedule", () => {
  it("says ASAP when no time was given", () => {
    const d = describeSchedule(null, "submitted", NOW);
    expect(d.kind).toBe("asap");
    expect(d.date).toBeNull();
    expect(d.note).toBeNull();
  });

  it("marks the real 2030 row as unschedulable", () => {
    // The actual row on the demo database.
    const d = describeSchedule("2030-11-17T13:33:00Z", "submitted", NOW);
    expect(d.kind).toBe("unschedulable");
    expect(d.note).toMatch(/administrator will action/i);
  });

  it("keeps the requested date rather than hiding it", () => {
    // The school asked for this. Discarding it to tidy the display would throw
    // away their stated preference — the whole reason we clamp instead of null.
    const d = describeSchedule("2030-11-17T13:33:00Z", "submitted", NOW);
    expect(d.date?.toISOString()).toBe("2030-11-17T13:33:00.000Z");
  });

  it("leaves a within-horizon request as a normal pending one", () => {
    const d = describeSchedule(daysFromNow(27), "submitted", NOW);
    expect(d.kind).toBe("pending");
    expect(d.note).toBe("awaiting admin action");
  });

  it("treats the horizon boundary as still schedulable", () => {
    // Exactly at the limit is what the API accepts, so the UI must agree —
    // flagging it would contradict a request the backend just took.
    const d = describeSchedule(
      daysFromNow(RESTORE_SCHEDULE_MAX_HORIZON_DAYS - 0.01),
      "submitted",
      NOW,
    );
    expect(d.kind).toBe("pending");
  });

  it("does not claim a completed request is awaiting action", () => {
    // Its time is now a record of what was asked for, not an expectation.
    for (const status of ["completed", "failed", "cancelled"]) {
      const d = describeSchedule(daysFromNow(5), status, NOW);
      expect(d.kind, status).toBe("settled");
      expect(d.note, status).toBeNull();
    }
  });

  it("does not flag a finished request that was scheduled far out", () => {
    // A 2030 row that already completed needs no warning — nothing is pending.
    const d = describeSchedule("2030-11-17T13:33:00Z", "completed", NOW);
    expect(d.kind).toBe("settled");
    expect(d.note).toBeNull();
  });

  it("reports an unparseable timestamp instead of rendering Invalid Date", () => {
    const d = describeSchedule("not-a-timestamp", "submitted", NOW);
    expect(d.kind).toBe("unschedulable");
    expect(d.date).toBeNull();
    expect(d.note).toMatch(/not recorded/i);
  });

  it("stays in step with the backend horizon constant", () => {
    // backend/src/backup/schemas.py :: RESTORE_SCHEDULE_MAX_HORIZON_DAYS.
    // A frontend stricter than the API flags rows the API accepted; looser,
    // and it fails to flag rows the API rejected.
    expect(RESTORE_SCHEDULE_MAX_HORIZON_DAYS).toBe(30);
  });
});
