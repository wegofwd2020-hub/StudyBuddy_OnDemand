/**
 * Date formatting — single source of truth for every date/time rendered
 * anywhere in the web app (#759).
 *
 * Decision (2026-09-16, binding, recorded on issue #759): dates render
 * numeric and DAY-FIRST — `dd/mm/yyyy`, e.g. `14/09/2026` — because that is
 * the convention of the schools this product serves, not the US month-first
 * convention `toLocaleDateString()` defaults to on an unconfigured locale.
 * Where a time accompanies a date it is 24-hour: `14/09/2026 14:05`. Time
 * alone is `14:05`. This superseded an earlier named-month format
 * (`15 Jun 2026`) adopted to dodge exactly this day/month ambiguity — day-first
 * numeric dodges it just as well and matches what the schools already expect,
 * so the named-month table is gone.
 *
 * No browser-locale formatting anywhere in `app/`, `components/`, or `lib/`
 * (outside this file): never `toLocaleDateString`, `toLocaleTimeString`, a
 * date through `toLocaleString`, or `Intl.DateTimeFormat`. Those render
 * per the VIEWER's OS/browser locale, so the same report reads as a different
 * day to two teachers at the same school depending on their machine's
 * settings — which is the defect this module exists to remove. (Plain
 * `toLocaleString()` on a NUMBER — money, counts — is unrelated and stays;
 * see the ESLint guard in `eslint.config.mjs`, which can only ban the
 * date-shaped calls for the same reason.)
 *
 * Two input shapes, handled differently on purpose:
 *
 * 1. A DATE-ONLY string, `YYYY-MM-DD` (e.g. a week-start bucket with no time
 *    component). This is parsed directly out of the STRING, never through
 *    `new Date(iso)` — `new Date("2026-06-15")` is midnight UTC, so
 *    `.getDate()` west of Greenwich returns the 14th: a value that was never
 *    an instant, and so never had a timezone, gets shifted by one anyway.
 *    Because a date-only value has no time, `formatTime`/`formatDateTime`
 *    on one fall back to `formatDate` output rather than fabricate `00:00`.
 *
 * 2. Anything else — a full ISO timestamp, an epoch number, or a `Date` — IS
 *    an instant, so it goes through `Date` and renders in the VIEWER's local
 *    timezone via `getDate/getMonth/getFullYear/getHours/getMinutes`, zero
 *    padded. Only the RENDERING is pinned (numeric, day-first, 24-hour); the
 *    day/hour value itself legitimately depends on the reader's timezone,
 *    same as before.
 *
 * `null`/`undefined` render as `""`. An unparseable string is returned
 * UNCHANGED — degrading to the raw value beats "Invalid Date" or a blank cell,
 * since the reader can still see what the server actually sent.
 *
 * CSV exports use the same `dd/mm/yyyy` (#759), with the column header naming
 * the convention (`Week start (DD/MM/YYYY)`). Known trade-off, accepted: Excel
 * re-types a date-like cell using the READER's regional settings, so on a
 * US-locale machine `03/09/2026` opens as 9 March. That is Excel's own
 * re-interpretation of the file, not something this module can control — the
 * header label is the file's only safeguard.
 */

/** Split a `YYYY-MM-DD` string into parts, or null if it isn't one. See the
 *  file header — this is why date-only values are never routed through
 *  `new Date()`. */
function parts(iso: string): { y: string; m: number; d: string } | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return null;
  const month = Number(m[2]);
  if (month < 1 || month > 12) return null;
  return { y: m[1], m: month, d: m[3] };
}

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

type Resolved =
  | { kind: "empty" }
  | { kind: "dateOnly"; d: string; m: number; y: string }
  | { kind: "instant"; date: Date }
  | { kind: "invalid"; original: string };

/** Classify an input value once, so every helper below shares the same
 *  date-only-vs-instant-vs-invalid decision instead of re-deriving it. */
function resolve(value: string | number | Date | null | undefined): Resolved {
  if (value === null || value === undefined) return { kind: "empty" };
  if (typeof value === "string") {
    const p = parts(value);
    if (p) return { kind: "dateOnly", d: p.d, m: p.m, y: p.y };
    const date = new Date(value);
    if (isNaN(date.getTime())) return { kind: "invalid", original: value };
    return { kind: "instant", date };
  }
  const date = value instanceof Date ? value : new Date(value);
  if (isNaN(date.getTime())) return { kind: "invalid", original: "" };
  return { kind: "instant", date };
}

function dateOnlyToDMY(d: string, m: number, y: string): string {
  return `${d}/${pad2(m)}/${y}`;
}

function instantToDMY(date: Date): string {
  return `${pad2(date.getDate())}/${pad2(date.getMonth() + 1)}/${date.getFullYear()}`;
}

function instantToHM(date: Date): string {
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

/** `2026-06-15` / an ISO timestamp / an epoch number / a `Date` -> `15/06/2026`. */
export function formatDate(value: string | number | Date | null | undefined): string {
  const r = resolve(value);
  switch (r.kind) {
    case "empty":
      return "";
    case "invalid":
      return r.original;
    case "dateOnly":
      return dateOnlyToDMY(r.d, r.m, r.y);
    case "instant":
      return instantToDMY(r.date);
  }
}

/** An instant -> `14:05` (24-hour, zero-padded). A date-only string has no
 *  time component, so it falls back to `formatDate` output rather than
 *  fabricate `00:00`. */
export function formatTime(value: string | number | Date | null | undefined): string {
  const r = resolve(value);
  switch (r.kind) {
    case "empty":
      return "";
    case "invalid":
      return r.original;
    case "dateOnly":
      return dateOnlyToDMY(r.d, r.m, r.y);
    case "instant":
      return instantToHM(r.date);
  }
}

/** An instant -> `14/09/2026 14:05`. A date-only string falls back to
 *  `formatDate` output (no fabricated `00:00`), same as `formatTime`. */
export function formatDateTime(value: string | number | Date | null | undefined): string {
  const r = resolve(value);
  switch (r.kind) {
    case "empty":
      return "";
    case "invalid":
      return r.original;
    case "dateOnly":
      return dateOnlyToDMY(r.d, r.m, r.y);
    case "instant":
      return `${instantToDMY(r.date)} ${instantToHM(r.date)}`;
  }
}

/** `2026-06-15` -> `15/06`, for chart axes where the year would not fit. */
export function formatDayMonth(value: string | number | Date | null | undefined): string {
  const r = resolve(value);
  switch (r.kind) {
    case "empty":
      return "";
    case "invalid":
      return r.original;
    case "dateOnly":
      return `${r.d}/${pad2(r.m)}`;
    case "instant":
      return `${pad2(r.date.getDate())}/${pad2(r.date.getMonth() + 1)}`;
  }
}
