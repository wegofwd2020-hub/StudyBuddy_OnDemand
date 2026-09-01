"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getStudentReport } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { LinkButton } from "@/components/ui/link-button";
import { Award, CheckCircle, XCircle, Clock } from "lucide-react";

function secondsToHm(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  // A 45-second read used to render as "0m", which is indistinguishable from
  // never having opened the lesson at all. Most rows on this table are short,
  // so that one rounding turned a column of real activity into a column of
  // zeroes — and made the "Reading time" tile above look invented.
  if (m === 0 && s > 0) return "<1m";
  return `${m}m`;
}

export default function StudentDetailPage() {
  const { student_id } = useParams<{ student_id: string }>();
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const { data: report, isLoading } = useQuery({
    queryKey: ["student-report", schoolId, student_id],
    queryFn: () => getStudentReport(schoolId, student_id),
    enabled: !!schoolId && !!student_id,
    staleTime: 120_000,
  });

  return (
    <div className="max-w-4xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <LinkButton href="/school/class/all" variant="outline" size="sm">
          ← Class
        </LinkButton>
        <h1 className="text-2xl font-bold text-gray-900">
          {isLoading ? "Loading…" : (report?.student_name ?? "Student Detail")}
        </h1>
        {report && (
          <Badge className="border-blue-100 bg-blue-50 text-blue-700">
            Grade {report.grade}
          </Badge>
        )}
      </div>

      {isLoading && <Skeleton className="h-48 rounded-lg" />}

      {report && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {/* Every tile carries the definition it counts.
                None of them did, and a tester comparing this card with the
                student's own My Stats page found 43% here against 65% there for
                the same child on the same afternoon and reported a data bug.
                Both numbers were right: this one counts first attempts, that one
                counts every attempt. Nothing on either screen said so. */}
            {[
              {
                label: "Units completed",
                value: report.units_completed,
                hint: "Quiz passed",
              },
              {
                // Answers "does In progress include Needs Retry?" — yes. It is
                // every unit reached and not yet passed, whether the quiz was
                // failed or never taken.
                label: "In progress",
                value: report.units_in_progress,
                hint: "Reached, not yet passed",
              },
              {
                label: "Pass rate",
                value: `${report.first_attempt_pass_rate_pct.toFixed(0)}%`,
                // The house convention on four other screens ("Pass rate (1st
                // attempt)", "First-attempt pass rate %"); this tile was the one
                // place it had been dropped.
                hint: "First attempt only",
              },
              // Lesson-reading time only -- quizzes record per-answer timings, not a
              // session duration, so this is not "time in the product" and the
              // old label promised more than the number delivers.
              {
                label: "Reading time",
                value: secondsToHm(report.total_time_spent_s),
                hint: "Total of the column below",
              },
            ].map(({ label, value, hint }) => (
              <Card key={label} className="border shadow-sm">
                <CardContent className="p-4">
                  <p className="text-xs font-medium tracking-wide text-gray-400 uppercase">
                    {label}
                  </p>
                  <p className="mt-1 text-xl font-bold text-gray-900">{value}</p>
                  <p className="mt-0.5 text-[11px] text-gray-400">{hint}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {(report.strongest_subject || report.needs_attention_subject) && (
            <div className="flex flex-wrap gap-3">
              {report.strongest_subject && (
                <div className="flex items-center gap-1.5 rounded-lg border border-green-100 bg-green-50 px-3 py-1.5 text-sm text-green-700">
                  {/* Award, not CheckCircle. A green check is this app's mark for
                      "done" — a finished pipeline job, a cleared alert, a lesson
                      read. "Strongest" is a RANKING, not a completion, and using
                      the same mark for both made one icon carry two classes of
                      meaning on a screen that shows them side by side. */}
                  <Award className="h-4 w-4" />
                  Strongest:{" "}
                  <span className="font-medium">{report.strongest_subject}</span>
                </div>
              )}
              {report.needs_attention_subject && (
                <div className="flex items-center gap-1.5 rounded-lg border border-orange-100 bg-orange-50 px-3 py-1.5 text-sm text-orange-700">
                  <XCircle className="h-4 w-4" />
                  Needs attention:{" "}
                  <span className="font-medium">{report.needs_attention_subject}</span>
                </div>
              )}
            </div>
          )}

          <Card className="border shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Unit progress</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      {[
                        "Unit",
                        "Subject",
                        "Lesson",
                        "Attempts",
                        "Best score",
                        // Named identically to the tile above, because it is now
                        // the same quantity at a finer grain: these cells add up
                        // to that number. "Time" said nothing about which time,
                        // and held an average while the tile held a sum.
                        "Reading time",
                      ].map((h) => (
                        <th
                          key={h}
                          className="px-4 py-2.5 text-left text-xs font-medium text-gray-500"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {report.per_unit.map((u) => (
                      <tr key={u.unit_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-800">
                          {u.unit_name ?? u.unit_id}
                        </td>
                        <td className="px-4 py-3 text-gray-500 capitalize">
                          {u.subject}
                        </td>
                        {/* Bare icons with no legend anywhere on the page. A
                            tester read this column as a health marker and asked
                            why low-scoring rows had no warning in it — a fair
                            reading of an unlabelled tick. It has always meant
                            only "opened the lesson", so it now says so, to a
                            screen reader and on hover alike. */}
                        <td className="px-4 py-3">
                          {u.lesson_viewed ? (
                            <CheckCircle
                              className="h-4 w-4 text-green-500"
                              aria-label="Lesson opened"
                            >
                              <title>Lesson opened</title>
                            </CheckCircle>
                          ) : (
                            <Clock
                              className="h-4 w-4 text-gray-300"
                              aria-label="Lesson not opened"
                            >
                              <title>Lesson not opened</title>
                            </Clock>
                          )}
                        </td>
                        <td className="px-4 py-3 text-gray-600">{u.quiz_attempts}</td>
                        {/* The needs-attention marker the tester asked for, on the
                            score rather than the lesson column — the score is what
                            makes a unit need attention.

                            The condition is `!u.passed`, NOT a hardcoded 50%. Pass
                            marks are per-school (ADR-007), so a fixed threshold
                            would flag units a school considers passed and miss
                            ones it does not. `passed` already carries that school's
                            own grading scale.

                            Same icon and colour as the "Needs attention" chip
                            above, deliberately: the legend and the rows should
                            speak one language, which is the whole complaint. */}
                        <td className="px-4 py-3">
                          {u.best_score !== null ? (
                            <span
                              className={
                                u.passed
                                  ? "font-medium text-green-600"
                                  : "inline-flex items-center gap-1.5 font-medium text-orange-700"
                              }
                            >
                              {!u.passed && (
                                <XCircle
                                  className="h-3.5 w-3.5 shrink-0"
                                  aria-label="Needs attention"
                                >
                                  <title>Needs attention</title>
                                </XCircle>
                              )}
                              {u.best_score.toFixed(0)}%
                            </span>
                          ) : (
                            <span className="text-gray-300">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-400">
                          {secondsToHm(u.total_duration_s)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
