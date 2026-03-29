"use client";

import { useQuery } from "@tanstack/react-query";
import { getSubscriptionAnalytics, getStruggleReport } from "@/lib/api/admin";

export default function AdminAnalyticsPage() {
  const { data: sub, isLoading: subLoading } = useQuery({
    queryKey: ["admin", "analytics", "subscriptions"],
    queryFn: getSubscriptionAnalytics,
    staleTime: 60_000,
  });

  const { data: struggle, isLoading: struggleLoading } = useQuery({
    queryKey: ["admin", "analytics", "struggle"],
    queryFn: getStruggleReport,
    staleTime: 300_000,
  });

  return (
    <div className="mx-auto max-w-6xl p-8">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">Platform Analytics</h1>
      <p className="mb-8 text-sm text-gray-500">
        Subscription funnel and student struggle data
      </p>

      {/* Subscription funnel */}
      <section className="mb-10">
        <h2 className="mb-4 text-base font-semibold text-gray-800">
          Subscription Breakdown
        </h2>
        {subLoading ? (
          <div className="h-40 animate-pulse rounded-xl bg-gray-100" />
        ) : sub ? (
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Metric
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">
                    Value
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr>
                  <td className="px-4 py-3 text-gray-700">Monthly subscribers</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-900">
                    {sub.active_monthly.toLocaleString()}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-gray-700">Annual subscribers</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-900">
                    {sub.active_annual.toLocaleString()}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-gray-700">Total active</td>
                  <td className="px-4 py-3 text-right font-mono font-semibold text-gray-900">
                    {sub.total_active.toLocaleString()}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-gray-700">MRR (CAD)</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-900">
                    ${sub.mrr_usd.toLocaleString("en-CA", { minimumFractionDigits: 2 })}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-gray-700">New this month</td>
                  <td className="px-4 py-3 text-right font-mono text-green-700">
                    +{sub.new_this_month}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-gray-700">Cancelled this month</td>
                  <td className="px-4 py-3 text-right font-mono text-red-600">
                    -{sub.cancelled_this_month}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-gray-700">Churn rate</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-900">
                    {(sub.churn_rate * 100).toFixed(2)}%
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400">No subscription data available.</p>
        )}
      </section>

      {/* Struggle report */}
      <section>
        <h2 className="mb-1 text-base font-semibold text-gray-800">Struggle Report</h2>
        <p className="mb-4 text-xs text-gray-500">
          Units with highest fail rates across all students.
          {struggle && (
            <> Generated {new Date(struggle.generated_at).toLocaleString()}.</>
          )}
        </p>
        {struggleLoading ? (
          <div className="h-48 animate-pulse rounded-xl bg-gray-100" />
        ) : struggle && struggle.units?.length > 0 ? (
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Unit</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Grade</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Subject
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">
                    Avg Score
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">
                    Attempts
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">
                    Fail Rate
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {struggle.units.map((unit) => (
                  <tr key={unit.unit_id}>
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {unit.unit_title}
                    </td>
                    <td className="px-4 py-3 text-gray-600">Gr. {unit.grade}</td>
                    <td className="px-4 py-3 text-gray-600">{unit.subject}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-900">
                      {(unit.avg_score * 100).toFixed(0)}%
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-600">
                      {unit.attempt_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className={
                          unit.fail_rate > 0.4
                            ? "font-semibold text-red-600"
                            : unit.fail_rate > 0.2
                              ? "text-yellow-600"
                              : "text-green-600"
                        }
                      >
                        {(unit.fail_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400">No struggle data available.</p>
        )}
      </section>
    </div>
  );
}
