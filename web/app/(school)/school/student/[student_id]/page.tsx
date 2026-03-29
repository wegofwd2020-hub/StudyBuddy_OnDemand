"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getStudentReport } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { LinkButton } from "@/components/ui/link-button";
import { CheckCircle, XCircle, Clock } from "lucide-react";

function secondsToHm(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
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
            {[
              { label: "Units completed", value: report.units_completed },
              { label: "In progress", value: report.units_in_progress },
              {
                label: "Pass rate",
                value: `${report.first_attempt_pass_rate_pct.toFixed(0)}%`,
              },
              { label: "Time spent", value: secondsToHm(report.total_time_spent_s) },
            ].map(({ label, value }) => (
              <Card key={label} className="border shadow-sm">
                <CardContent className="p-4">
                  <p className="text-xs font-medium tracking-wide text-gray-400 uppercase">
                    {label}
                  </p>
                  <p className="mt-1 text-xl font-bold text-gray-900">{value}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {(report.strongest_subject || report.needs_attention_subject) && (
            <div className="flex flex-wrap gap-3">
              {report.strongest_subject && (
                <div className="flex items-center gap-1.5 rounded-lg border border-green-100 bg-green-50 px-3 py-1.5 text-sm text-green-700">
                  <CheckCircle className="h-4 w-4" />
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
                        "Time",
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
                        <td className="px-4 py-3">
                          {u.lesson_viewed ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <Clock className="h-4 w-4 text-gray-300" />
                          )}
                        </td>
                        <td className="px-4 py-3 text-gray-600">{u.quiz_attempts}</td>
                        <td className="px-4 py-3">
                          {u.best_score !== null ? (
                            <span
                              className={
                                u.passed ? "font-medium text-green-600" : "text-red-500"
                              }
                            >
                              {u.best_score.toFixed(0)}%
                            </span>
                          ) : (
                            <span className="text-gray-300">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-400">
                          {secondsToHm(u.avg_duration_s)}
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
