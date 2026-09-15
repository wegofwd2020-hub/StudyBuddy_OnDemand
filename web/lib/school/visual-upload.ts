/**
 * What the visual-asset upload form is still missing (issue #618).
 *
 * The Upload button used to be disabled until every field was valid, with no
 * indication why. The three ID fields have placeholders that look exactly like
 * real values — `default-2026-g11-science`, `G11-PHYS-002`, `s1` — so the form
 * appears filled in, and a user who chose a file and pressed Upload got a
 * button that did nothing at all. It was reported as the upload being broken,
 * which is a fair reading of an inert control.
 *
 * The button now submits, and this says what is missing.
 */

/** IDs start with a letter or digit, then letters, digits, dot, underscore, dash. */
export const ID_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

export interface UploadFields {
  file: File | null;
  curriculum: string;
  unit: string;
  section: string;
}

/**
 * Returns a message naming what still needs filling, or null when ready.
 *
 * Missing and malformed are reported separately: "you left this blank" and
 * "this is not a valid ID" are different problems and a single generic message
 * would send the user hunting.
 */
export function describeMissingUploadFields(fields: UploadFields): string | null {
  const labelled: Array<[string, string]> = [
    ["Curriculum ID", fields.curriculum],
    ["Unit ID", fields.unit],
    ["Section ID", fields.section],
  ];

  const blank = labelled
    .filter(([, value]) => value.trim() === "")
    .map(([label]) => label);
  const malformed = labelled
    .filter(([, value]) => value.trim() !== "" && !ID_RE.test(value.trim()))
    .map(([label]) => label);

  if (!fields.file && blank.length === 0 && malformed.length === 0) {
    return "Choose a file to upload.";
  }

  const parts: string[] = [];
  if (blank.length) parts.push(`Fill in ${formatList(blank)}.`);
  if (malformed.length) {
    parts.push(
      `${formatList(malformed)} ${malformed.length === 1 ? "is" : "are"} not a valid ID — ` +
        'use letters, numbers, ".", "_" or "-", starting with a letter or number.',
    );
  }
  if (!fields.file) parts.push("Choose a file to upload.");

  return parts.length ? parts.join(" ") : null;
}

function formatList(items: string[]): string {
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}
