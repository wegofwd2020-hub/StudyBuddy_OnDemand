/**
 * Grouping shared by the report cards that list units (#773, #776).
 *
 * One module because #776's whole premise is that these cards should LOOK THE
 * SAME — the issue asks for the admin overview to use "display format similar
 * to Reports->Engagement->Units with zero activity". Two copies of this logic
 * would drift, and the drift would be invisible: each page would still render
 * correctly, just differently, which is the failure the issue is reporting.
 */

/** The minimum a row needs to be grouped. Both `CurriculumHealthUnit` and
 *  `OverviewUnitRef` satisfy it structurally, so neither report has to convert. */
export interface GroupableUnit {
  unit_id: string;
  subject: string;
  grade?: number | null;
}

/**
 * Group units by grade, then by subject within each grade.
 *
 * Returns ENTRIES rather than an object, deliberately: JavaScript iterates
 * integer-like object keys in ascending numeric order regardless of insertion,
 * so a plain object would silently reorder the moment the non-numeric "Other"
 * bucket joined them — and the bug would look like a rendering quirk rather
 * than a data-structure choice.
 *
 * Units with no resolvable grade are collected under "Other" and sorted LAST.
 * They are never dropped: an untouched or struggling unit is exactly what these
 * cards exist to surface, so hiding the ones whose grade could not be resolved
 * would quietly understate the thing being measured.
 */
export function groupByGradeThenSubject<T extends GroupableUnit>(
  units: T[],
): [string, [string, T[]][]][] {
  const byGrade = new Map<number | null, T[]>();
  for (const u of units) {
    const g = u.grade ?? null;
    byGrade.set(g, [...(byGrade.get(g) ?? []), u]);
  }

  const grades = [...byGrade.keys()].sort((a, b) => {
    if (a === null) return 1;
    if (b === null) return -1;
    return a - b;
  });

  return grades.map((g) => {
    const bySubject = new Map<string, T[]>();
    for (const u of byGrade.get(g) ?? []) {
      bySubject.set(u.subject, [...(bySubject.get(u.subject) ?? []), u]);
    }
    const subjects = [...bySubject.entries()].sort(([a], [b]) => a.localeCompare(b));
    return [g === null ? "Other" : `Grade ${g}`, subjects] as [string, [string, T[]][]];
  });
}
