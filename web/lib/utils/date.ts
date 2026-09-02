/**
 * Date formatting for report screens.
 *
 * A tester asked why the Weekly breakdown shows `2026-06-15` on screen and
 * `15-06-2026` in the downloaded Excel. Nothing in the export converts it — we
 * write ISO 8601 in both places. Excel recognises `2026-06-15` as a date,
 * stores it as one, and renders it using the reader's regional settings. Two
 * teachers on different locales see different text from an identical file, and
 * we cannot control that from here.
 *
 * What we CAN control is whether a date can be read as the wrong day. A row
 * reading `03-08-2026` is 3 August in his locale and 8 March in a US one, with
 * nothing on the page saying which convention is in force. So the screen uses a
 * NAMED month, which no locale can reinterpret, and the CSV keeps ISO 8601 with
 * the convention stated in its column header.
 *
 * The month names are a fixed table rather than `toLocaleDateString`, on
 * purpose: a locale-dependent formatter would reintroduce exactly the variance
 * this exists to remove — the same report reading differently for two teachers
 * at the same school.
 */

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

/** Split a `YYYY-MM-DD` string into parts, or null if it isn't one.
 *
 *  Parsed from the STRING, never through `new Date(iso)`. `new Date("2026-06-15")`
 *  is midnight UTC, so `getDate()` west of Greenwich returns the 14th — a
 *  date-only value silently shifted by a timezone it never had.
 */
function parts(iso: string): { y: string; m: number; d: string } | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return null;
  const month = Number(m[2]);
  if (month < 1 || month > 12) return null;
  return { y: m[1], m: month, d: m[3] };
}

/** `2026-06-15` -> `15 Jun 2026`. Unparseable input is returned unchanged, so a
 *  format we did not anticipate degrades to the raw value rather than "Invalid
 *  Date" or an empty cell. */
export function formatWeekStart(iso: string): string {
  const p = parts(iso);
  if (!p) return iso;
  return `${p.d} ${MONTHS[p.m - 1]} ${p.y}`;
}

/** `2026-06-15` -> `15 Jun`, for chart axes where the year would not fit.
 *
 *  Replaces `week_start.slice(5)`, which produced `06-15` — month-first, and so
 *  the single most ambiguous rendering of the three the report had. */
export function formatWeekShort(iso: string): string {
  const p = parts(iso);
  if (!p) return iso;
  return `${p.d} ${MONTHS[p.m - 1]}`;
}
