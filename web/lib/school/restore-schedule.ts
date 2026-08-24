/**
 * How to display a restore request's "Preferred time" (issue #589).
 *
 * `scheduled_at` is a *preference*, not a promise: nothing in the system reads
 * it back. The restore lifecycle only advances when a human acts. The field was
 * relabelled from "Schedule for" to "Preferred time" and bounded to a 30-day
 * horizon (#595) so it can no longer imply unattended execution.
 *
 * That fixed new requests. It could not fix rows created before it landed —
 * the demo still holds one asking for **17 Nov 2030**, created three hours and
 * sixteen minutes before the validator merged, and still displayed as awaiting
 * action. Anyone reading that table is told the system will do something on a
 * date it will not.
 *
 * These rows are deliberately NOT deleted or nulled: a school stated a
 * preference, that is their educational record, and clamping the *display* is
 * reversible where discarding the value is not. So the value is kept and shown,
 * and the promise around it is withdrawn.
 *
 * The horizon is duplicated from the backend's
 * `RESTORE_SCHEDULE_MAX_HORIZON_DAYS` (backend/src/backup/schemas.py). Keep them
 * in step — a frontend that is stricter would flag rows the API accepted, and
 * one that is looser would fail to flag rows it rejected.
 */

export const RESTORE_SCHEDULE_MAX_HORIZON_DAYS = 30;

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
 * Decide how one request's preferred time should read.
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

  const horizon = new Date(
    now.getTime() + RESTORE_SCHEDULE_MAX_HORIZON_DAYS * 86_400_000,
  );
  if (date > horizon) {
    return {
      kind: "unschedulable",
      date,
      note: "Outside the 30-day window — an administrator will action this request.",
    };
  }

  return { kind: "pending", date, note: "awaiting admin action" };
}
