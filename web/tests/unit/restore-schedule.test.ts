import { describe, it, expect } from "vitest";
import {
  validateScheduledAt,
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
