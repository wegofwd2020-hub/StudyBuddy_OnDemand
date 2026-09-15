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
