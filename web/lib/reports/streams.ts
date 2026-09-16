/**
 * Stream display, shared by every report that offers a stream filter
 * (#771, #772, #773, #774, #776).
 *
 * One module because the label is a contract with the reader, not a per-page
 * detail: "Commerce" on Unit Performance and "commerce" on the Feedback report
 * read as two different things, and a teacher comparing the two reports cannot
 * tell whether they are looking at the same cohort.
 */

/** The bucket for students whose curricula carry no stream.
 *
 * Mirrors `UNSTREAMED` in backend/src/reports/service.py. It is deliberately
 * NOT a code from the streams registry (migration 0045) and therefore cannot
 * collide with one. School-owned curricula never carry a stream, so this bucket
 * is permanent rather than a migration artefact. */
export const UNSTREAMED = "unstreamed";

/** The five system seeds from migration 0045. */
const KNOWN: Record<string, string> = {
  science: "Science",
  commerce: "Commerce",
  humanities: "Humanities",
  english: "English Core",
  stem: "STEM",
};

/**
 * Display name for a stream code. `null` means "no filter applied".
 *
 * The registry's own `display_name` is not carried on the report responses and
 * fetching it would be a second request to label four chips.
 *
 * An UNKNOWN code falls through to a capitalised form of itself rather than
 * being hidden or shown raw: schools can mint their own streams through the
 * upload page's upsert-on-use (Epic 8 H-10), so an unrecognised code is a
 * normal event, not a bug. Hiding it would drop a real option out of the
 * picker.
 */
export function streamLabel(code: string | null): string {
  if (code === null) return "All streams";
  if (code === UNSTREAMED) return "No stream";
  return KNOWN[code] ?? code.charAt(0).toUpperCase() + code.slice(1);
}
