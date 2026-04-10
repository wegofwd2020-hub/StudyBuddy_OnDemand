"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  AtRiskStudent,
  getAtRiskStudents,
  markAtRiskSeen,
  sendAtRiskReminder,
} from "@/lib/api/reports";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  Bell,
  CheckCircle,
  Clock,
  Eye,
  TrendingDown,
  UserX,
} from "lucide-react";

function RiskBadge({ reasons }: { reasons: AtRiskStudent["risk_reasons"] }) {
  if (reasons.inactive && reasons.low_pass_rate) {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
        <AlertTriangle className="h-3 w-3" />
        Inactive + low pass rate
      </span>
    );
  }
  if (reasons.inactive) {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-700">
        <Clock className="h-3 w-3" />
        Inactive
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded bg-yellow-100 px-2 py-0.5 text-xs font-semibold text-yellow-700">
      <TrendingDown className="h-3 w-3" />
      Low pass rate
    </span>
  );
}

function LastActiveCell({ lastActive, inactiveDays }: { lastActive: string | null; inactiveDays: number | null }) {
  if (!lastActive) {
    return <span className="text-gray-400">Never active</span>;
  }
  const label = inactiveDays != null ? `${inactiveDays}d ago` : new Date(lastActive).toLocaleDateString();
  return <span className={cn(inactiveDays != null && inactiveDays > 21 ? "font-semibold text-red-600" : "text-gray-600")}>{label}</span>;
}

export default function AtRiskPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["at-risk", schoolId],
    queryFn: () => getAtRiskStudents(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  const seenMutation = useMutation({
    mutationFn: ({ studentId, seen }: { studentId: string; seen: boolean }) =>
      markAtRiskSeen(schoolId, studentId, seen),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["at-risk", schoolId] }),
  });

  const reminderMutation = useMutation({
    mutationFn: (studentId: string) => sendAtRiskReminder(schoolId, studentId),
  });

  const unseen = data?.students.filter((s) => !s.is_seen) ?? [];
  const seen = data?.students.filter((s) => s.is_seen) ?? [];

  return (
    <div className="max-w-5xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">At-Risk Students</h1>
        <p className="mt-1 text-sm text-gray-500">
          Students who are inactive or have a low pass rate. Mark as seen once
          you&apos;ve followed up, or send a push reminder.
        </p>
        {data && (
          <p className="mt-0.5 text-xs text-gray-400">
            Thresholds: inactive &gt; {data.inactive_days_threshold} days ·
            pass rate &lt; {data.pass_rate_threshold}%
          </p>
        )}
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-gray-100" />
          ))}
        </div>
      )}

      {!isLoading && data && data.total === 0 && (
        <div className="rounded-xl border border-green-100 bg-green-50 py-14 text-center">
          <CheckCircle className="mx-auto mb-3 h-10 w-10 text-green-400" />
          <p className="text-sm font-medium text-green-700">No at-risk students</p>
          <p className="mt-1 text-xs text-gray-500">
            All enrolled students are active and passing. Check back later or
            adjust thresholds in{" "}
            <Link href="/school/reports/alerts" className="underline hover:text-gray-700">
              Alert Settings
            </Link>
            .
          </p>
        </div>
      )}

      {!isLoading && data && data.total > 0 && (
        <>
          {/* Needs attention */}
          {unseen.length > 0 && (
            <section>
              <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-700">
                <UserX className="h-4 w-4 text-red-500" />
                Needs attention ({unseen.length})
              </h2>
              <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
                <table className="w-full text-sm">
                  <thead className="border-b border-gray-100 bg-gray-50">
                    <tr>
                      {["Student", "Grade", "Last active", "Pass rate", "Risk", "Actions"].map(
                        (h) => (
                          <th
                            key={h}
                            className="px-4 py-3 text-left text-xs font-medium text-gray-500"
                          >
                            {h}
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {unseen.map((s) => (
                      <tr key={s.student_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <Link
                            href={`/school/reports/student/${s.student_id}`}
                            className="font-medium text-gray-900 hover:text-indigo-600 hover:underline"
                          >
                            {s.student_name}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-gray-500">Gr. {s.grade}</td>
                        <td className="px-4 py-3">
                          <LastActiveCell
                            lastActive={s.last_active}
                            inactiveDays={s.inactive_days}
                          />
                        </td>
                        <td className="px-4 py-3">
                          {s.pass_rate_pct != null ? (
                            <span
                              className={cn(
                                "font-medium",
                                s.risk_reasons.low_pass_rate
                                  ? "text-red-600"
                                  : "text-gray-700",
                              )}
                            >
                              {s.pass_rate_pct.toFixed(0)}%
                            </span>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <RiskBadge reasons={s.risk_reasons} />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() =>
                                reminderMutation.mutate(s.student_id)
                              }
                              disabled={reminderMutation.isPending}
                              title="Send push reminder"
                              className="inline-flex items-center gap-1 rounded bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-100 disabled:opacity-50"
                            >
                              <Bell className="h-3 w-3" />
                              Remind
                            </button>
                            <button
                              onClick={() =>
                                seenMutation.mutate({
                                  studentId: s.student_id,
                                  seen: true,
                                })
                              }
                              disabled={seenMutation.isPending}
                              title="Mark as reviewed"
                              className="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 disabled:opacity-50"
                            >
                              <Eye className="h-3 w-3" />
                              Mark seen
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Already reviewed */}
          {seen.length > 0 && (
            <section>
              <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-500">
                <CheckCircle className="h-4 w-4 text-green-400" />
                Reviewed ({seen.length})
              </h2>
              <div className="overflow-hidden rounded-xl border border-gray-100 bg-white opacity-75">
                <table className="w-full text-sm">
                  <thead className="border-b border-gray-100 bg-gray-50">
                    <tr>
                      {["Student", "Grade", "Last active", "Pass rate", "Risk", ""].map((h) => (
                        <th
                          key={h}
                          className="px-4 py-3 text-left text-xs font-medium text-gray-400"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {seen.map((s) => (
                      <tr key={s.student_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <Link
                            href={`/school/reports/student/${s.student_id}`}
                            className="font-medium text-gray-700 hover:text-indigo-600 hover:underline"
                          >
                            {s.student_name}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-gray-400">Gr. {s.grade}</td>
                        <td className="px-4 py-3 text-gray-400">
                          <LastActiveCell
                            lastActive={s.last_active}
                            inactiveDays={s.inactive_days}
                          />
                        </td>
                        <td className="px-4 py-3 text-gray-400">
                          {s.pass_rate_pct != null ? `${s.pass_rate_pct.toFixed(0)}%` : "—"}
                        </td>
                        <td className="px-4 py-3">
                          <RiskBadge reasons={s.risk_reasons} />
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() =>
                              seenMutation.mutate({
                                studentId: s.student_id,
                                seen: false,
                              })
                            }
                            disabled={seenMutation.isPending}
                            className="text-xs text-gray-400 hover:text-gray-600 disabled:opacity-50"
                          >
                            Unmark
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}

      {reminderMutation.isSuccess && (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-white px-5 py-3 shadow-lg ring-1 ring-gray-200">
          <p className="text-sm text-gray-700">
            {reminderMutation.data?.queued
              ? "Reminder queued successfully."
              : "No push tokens registered for this student."}
          </p>
        </div>
      )}
    </div>
  );
}
