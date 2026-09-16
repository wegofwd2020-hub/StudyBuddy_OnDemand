/**
 * The Unit Performance CSV, grouped by Grade and Stream (#772).
 *
 * Grouping in a CSV is COLUMNS plus a deterministic ORDER, not section header
 * rows. Every row names its own grade and stream, so a teacher can filter,
 * sort and pivot in a spreadsheet; header rows mixed into the data would break
 * all three.
 *
 * Kept out of the page so the column contract and the order can be tested
 * without rendering anything.
 */

import type { CurriculumHealthReport, CurriculumHealthUnit } from "@/lib/api/reports";
import { UNSTREAMED, streamLabel } from "@/lib/reports/streams";

export const UNIT_PERFORMANCE_FIELDS = [
  "Grade",
  "Stream",
  "Subject",
  "Unit ID",
  "Unit name",
  "Health tier",
  "First-attempt pass rate %",
  "Average score %",
  "Avg attempts to pass",
  "Feedback count",
  "Recommended action",
] as const;

type Row = Record<(typeof UNIT_PERFORMANCE_FIELDS)[number], string | number>;

/**
 * Grade (numeric, no-grade last) -> Stream (by label, `unstreamed` last) ->
 * Subject -> unit name.
 *
 * No-grade and no-stream sort LAST rather than first, matching the "Other"
 * bucket on the report screens (`groupByGradeThenSubject`): they are real rows
 * a reader still needs, not headline groups.
 */
function compareUnits(a: CurriculumHealthUnit, b: CurriculumHealthUnit): number {
  const ga = a.grade ?? null;
  const gb = b.grade ?? null;
  if (ga !== gb) {
    if (ga === null) return 1;
    if (gb === null) return -1;
    return ga - gb;
  }
  const sa = a.stream ?? UNSTREAMED;
  const sb = b.stream ?? UNSTREAMED;
  if (sa !== sb) {
    if (sa === UNSTREAMED) return 1;
    if (sb === UNSTREAMED) return -1;
    return streamLabel(sa).localeCompare(streamLabel(sb));
  }
  return (
    a.subject.localeCompare(b.subject) ||
    (a.unit_name ?? a.unit_id).localeCompare(b.unit_name ?? b.unit_id)
  );
}

export function buildUnitPerformanceCsv(data: CurriculumHealthReport): {
  fields: string[];
  rows: Row[];
} {
  const rows: Row[] = [...data.units].sort(compareUnits).map((u) => ({
    Grade: u.grade ?? "",
    Stream: streamLabel(u.stream ?? UNSTREAMED),
    Subject: u.subject,
    "Unit ID": u.unit_id,
    "Unit name": u.unit_name ?? "",
    "Health tier": u.health_tier,
    "First-attempt pass rate %": u.first_attempt_pass_rate_pct.toFixed(1),
    "Average score %": u.avg_score_pct.toFixed(1),
    "Avg attempts to pass": u.avg_attempts_to_pass.toFixed(2),
    "Feedback count": u.feedback_count,
    "Recommended action": u.recommended_action,
  }));

  // Feedback that names no unit has no row to live on, so without this the file
  // silently omits it and the total cannot be reconciled against the dashboard.
  // Appended AFTER sorting: it is visibly not a unit and belongs to no group.
  if (data.general_feedback_count) {
    rows.push({
      Grade: "",
      Stream: "",
      Subject: "",
      "Unit ID": "—",
      "Unit name": "General feedback (not tied to a unit)",
      "Health tier": "",
      "First-attempt pass rate %": "",
      "Average score %": "",
      "Avg attempts to pass": "",
      "Feedback count": data.general_feedback_count,
      "Recommended action": "",
    });
  }

  return { fields: [...UNIT_PERFORMANCE_FIELDS], rows };
}

/**
 * The filters go in the NAME, not only in the contents. Two downloads an hour
 * apart both called `unit_performance.csv` sit in one folder covering different
 * populations, and nothing in the file says which is which.
 */
export function unitPerformanceFilename(
  grade: number | null,
  stream: string | null,
): string {
  const parts = ["unit_performance"];
  if (grade !== null) parts.push(`grade_${grade}`);
  if (stream !== null) parts.push(stream);
  return `${parts.join("_")}.csv`;
}
