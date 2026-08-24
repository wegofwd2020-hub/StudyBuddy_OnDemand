/**
 * web/lib/school/restore-schedule.ts
 *
 * Client-side mirror of the `scheduled_at` bound enforced server-side in
 * `backend/src/backup/schemas.py::RestoreRequestCreate.validate_scheduled_at`
 * (issue #589). The "Preferred time" field on a restore request is a
 * request an administrator will action manually — nothing in the system
 * ever polls this timestamp and executes a restore automatically. Keeping
 * the horizon in sync here lets the form reject an unreasonable value
 * before a round trip to the API, and lets the copy stay honest about what
 * the field does.
 */

export const RESTORE_SCHEDULE_MAX_HORIZON_DAYS = 30;

/**
 * Validate a `<input type="datetime-local">` value against the same bound
 * the backend enforces. Returns `null` when the value is valid (including
 * an empty string — blank means "as soon as an administrator can action
 * it"), or a user-facing error message otherwise.
 */
export function validateScheduledAt(
  value: string,
  now: Date = new Date(),
): string | null {
  if (!value) return null;

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "That doesn't look like a valid date.";
  }

  if (parsed.getTime() < now.getTime()) {
    return "Preferred time can't be in the past.";
  }

  const horizonMs = RESTORE_SCHEDULE_MAX_HORIZON_DAYS * 24 * 60 * 60 * 1000;
  if (parsed.getTime() > now.getTime() + horizonMs) {
    return (
      `Preferred time can't be more than ${RESTORE_SCHEDULE_MAX_HORIZON_DAYS} days out. ` +
      "Restore requests are reviewed and actioned by an administrator, not executed " +
      "automatically at the requested time — pick a nearer date or leave this blank."
    );
  }

  return null;
}

/** `now` formatted for a datetime-local input's `min` attribute. */
export function nowForDatetimeLocalMin(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}` +
    `T${pad(now.getHours())}:${pad(now.getMinutes())}`
  );
}

/** `now + horizon` formatted for a datetime-local input's `max` attribute. */
export function maxForDatetimeLocalMax(now: Date = new Date()): string {
  const horizonMs = RESTORE_SCHEDULE_MAX_HORIZON_DAYS * 24 * 60 * 60 * 1000;
  return nowForDatetimeLocalMin(new Date(now.getTime() + horizonMs));
}

// ── Displaying an existing request's preferred time ───────────────────────────
//
// The validator above fixed NEW requests. It could not fix rows created before
// it landed: the demo still holds one asking for 17 Nov 2030, created three
// hours and sixteen minutes before the validator merged, and still displayed as
// "awaiting admin action". Nothing reads `scheduled_at` back, so that row is a
// promise the system will not keep — the reader is misled by data, not by code.
//
// These rows are deliberately NOT deleted or nulled: a school stated a
// preference, that is their record, and clamping the display is reversible
// where discarding the value is not. Keep the value, withdraw the promise.

/** Statuses where a scheduled time is history, not a pending expectation. */
const TERMINAL_STATUSES = ["completed", "failed", "cancelled"];

export type ScheduleDisplayKind = "asap" | "pending" | "settled" | "unschedulable";

export interface ScheduleDisplay {
  kind: ScheduleDisplayKind;
  /** The date to show, or null when there is nothing to show ("ASAP"). */
  date: Date | null;
  /** Secondary line, or null for none. */
  note: string | null;
}

/**
 * Decide how one existing request's preferred time should read.
 *
 * @param scheduledAt ISO timestamp, or null/undefined for "ASAP"
 * @param status      the request's current status
 * @param now         injectable for tests; defaults to the current time
 */
export function describeSchedule(
  scheduledAt: string | null | undefined,
  status: string,
  now: Date = new Date(),
): ScheduleDisplay {
  if (!scheduledAt) {
    return { kind: "asap", date: null, note: null };
  }

  const date = new Date(scheduledAt);
  if (Number.isNaN(date.getTime())) {
    // Unparseable rather than absent — say so instead of rendering
    // "Invalid Date", which reads as a bug to the person looking at it.
    return { kind: "unschedulable", date: null, note: "Time not recorded correctly." };
  }

  // A finished request's time is a record of what was asked for. Adding
  // "awaiting action" to a completed restore would be its own false statement.
  if (TERMINAL_STATUSES.includes(status)) {
    return { kind: "settled", date, note: null };
  }

  const horizonMs = RESTORE_SCHEDULE_MAX_HORIZON_DAYS * 24 * 60 * 60 * 1000;
  if (date.getTime() > now.getTime() + horizonMs) {
    return {
      kind: "unschedulable",
      date,
      note: `Outside the ${RESTORE_SCHEDULE_MAX_HORIZON_DAYS}-day window — an administrator will action this request.`,
    };
  }

  return { kind: "pending", date, note: "awaiting admin action" };
}
