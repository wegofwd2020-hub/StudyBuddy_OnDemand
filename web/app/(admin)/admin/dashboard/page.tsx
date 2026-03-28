"use client";

import Image from "next/image";
import { useQuery } from "@tanstack/react-query";
import { getSubscriptionAnalytics, getPipelineJobs } from "@/lib/api/admin";
import { TrendingUp, Users, DollarSign, GitBranch, AlertTriangle } from "lucide-react";

function KpiCard({
  label,
  value,
  sub,
  icon,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-500">{label}</span>
        <span className="text-gray-400">{icon}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function AdminDashboardPage() {
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ["admin", "analytics", "subscriptions"],
    queryFn: getSubscriptionAnalytics,
    staleTime: 60_000,
  });

  const { data: pipelineData, isLoading: pipelineLoading } = useQuery({
    queryKey: ["admin", "pipeline", "jobs"],
    queryFn: getPipelineJobs,
    staleTime: 30_000,
  });

  const activeJobs = pipelineData?.jobs?.filter(
    (j) => j.status === "running" || j.status === "queued",
  ).length ?? 0;

  const failedJobs = pipelineData?.jobs?.filter(
    (j) => j.status === "failed",
  ).length ?? 0;

  return (
    <div className="flex flex-col">
      {/* Hero image */}
      <div className="relative w-full h-[240px] bg-gray-900">
        <Image
          src="/assets/peeple.png"
          alt="Admin Console"
          fill
          priority
          className="object-contain object-center"
        />
      </div>

    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1 text-center">Platform Dashboard</h1>
      <p className="text-sm text-gray-500 mb-8 text-center">Live subscription and pipeline overview</p>

      {/* Subscription KPIs */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
          Subscriptions
        </h2>
        {analyticsLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-28 bg-gray-100 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : analytics ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard
              label="Total Active"
              value={analytics.total_active.toLocaleString()}
              sub={`${analytics.active_monthly} monthly · ${analytics.active_annual} annual`}
              icon={<Users className="h-4 w-4" />}
            />
            <KpiCard
              label="MRR"
              value={`$${analytics.mrr_usd.toLocaleString("en-CA", { minimumFractionDigits: 0 })}`}
              icon={<DollarSign className="h-4 w-4" />}
            />
            <KpiCard
              label="New This Month"
              value={analytics.new_this_month}
              icon={<TrendingUp className="h-4 w-4" />}
            />
            <KpiCard
              label="Churn Rate"
              value={`${(analytics.churn_rate * 100).toFixed(1)}%`}
              sub={`${analytics.cancelled_this_month} cancelled`}
              icon={<AlertTriangle className="h-4 w-4" />}
            />
          </div>
        ) : (
          <p className="text-sm text-gray-400">No analytics data available.</p>
        )}
      </section>

      {/* Pipeline Summary */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
          Pipeline
        </h2>
        {pipelineLoading ? (
          <div className="h-24 bg-gray-100 rounded-xl animate-pulse" />
        ) : (
          <div className="grid grid-cols-3 gap-4">
            <KpiCard
              label="Total Jobs"
              value={pipelineData?.jobs.length ?? 0}
              icon={<GitBranch className="h-4 w-4" />}
            />
            <KpiCard
              label="Active"
              value={activeJobs}
              sub="running or queued"
              icon={<GitBranch className="h-4 w-4" />}
            />
            <KpiCard
              label="Failed"
              value={failedJobs}
              icon={<AlertTriangle className="h-4 w-4" />}
            />
          </div>
        )}
      </section>
    </div>
    </div>
  );
}
