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
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Platform Analytics</h1>
      <p className="text-sm text-gray-500 mb-8">Subscription funnel and student struggle data</p>

      {/* Subscription funnel */}
      <section className="mb-10">
        <h2 className="text-base font-semibold text-gray-800 mb-4">Subscription Breakdown</h2>
        {subLoading ? (
          <div className="h-40 bg-gray-100 rounded-xl animate-pulse" />
        ) : sub ? (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Metric</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Value</th>
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
        <h2 className="text-base font-semibold text-gray-800 mb-1">Struggle Report</h2>
        <p className="text-xs text-gray-500 mb-4">
          Units with highest fail rates across all students.
          {struggle && (
            <> Generated {new Date(struggle.generated_at).toLocaleString()}.</>
          )}
        </p>
        {struggleLoading ? (
          <div className="h-48 bg-gray-100 rounded-xl animate-pulse" />
        ) : struggle && struggle.units.length > 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Unit</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Grade</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Subject</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Avg Score</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Attempts</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Fail Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {struggle.units.map((unit) => (
                  <tr key={unit.unit_id}>
                    <td className="px-4 py-3 text-gray-900 font-medium">
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
                            ? "text-red-600 font-semibold"
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
