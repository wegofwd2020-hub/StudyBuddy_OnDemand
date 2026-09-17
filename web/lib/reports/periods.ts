import type { ReportPeriod } from "@/lib/api/reports";

/**
 * The reporting windows the school overview endpoint accepts.
 *
 * Extracted from `school/dashboard/page.tsx` so every surface reading
 * `getOverviewReport` offers the same three and labels them identically (#770).
 * The Engagement report previously hardcoded "Last 30 days" in prose with no
 * way to change it, so the same figures were described differently on two
 * screens and only one of them could be re-scoped.
 *
 * Deliberately NOT the admin analytics vocabulary ("7d"/"30d"/"all"): that set
 * has an all-time window this endpoint cannot serve, and lacks the school term
 * this one can. Offering a value the API rejects is worse than offering fewer.
 */
export const OVERVIEW_PERIODS: { value: ReportPeriod; label: string }[] = [
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "term", label: "This term" },
];

/** Mid-sentence form, e.g. "Showing the last 7 days." */
export const OVERVIEW_PERIOD_LABELS: Record<ReportPeriod, string> = {
  "7d": "the last 7 days",
  "30d": "the last 30 days",
  term: "this term",
};
