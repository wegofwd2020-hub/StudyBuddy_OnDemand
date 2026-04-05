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
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm text-gray-500">{label}</span>
        <span className="text-gray-400">{icon}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-gray-400">{sub}</p>}
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

  const activeJobs =
    pipelineData?.jobs?.filter((j) => j.status === "running" || j.status === "queued")
      .length ?? 0;

  const failedJobs = pipelineData?.jobs?.filter((j) => j.status === "failed").length ?? 0;

  return (
    <div className="flex flex-col">
      {/* Hero image */}
      <div className="relative h-[240px] w-full bg-gray-900">
        <Image
          src="/assets/peeple.png"
          alt="Admin Console"
          fill
          priority
          className="object-contain object-center"
        />
      </div>

      <div className="mx-auto max-w-6xl p-8">
        <h1 className="mb-1 text-center text-2xl font-bold text-gray-900">
          Platform Dashboard
        </h1>
        <p className="mb-8 text-center text-sm text-gray-500">
          Live subscription and pipeline overview
        </p>

        {/* Subscription KPIs */}
        <section className="mb-8">
          <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500 uppercase">
            Subscriptions
          </h2>
          {analyticsLoading ? (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-28 animate-pulse rounded-xl bg-gray-100" />
              ))}
            </div>
          ) : analytics ? (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <KpiCard
                label="Total Active"
                value={analytics.total_active.toLocaleString()}
                sub={`${analytics.active_monthly} monthly · ${analytics.active_annual} annual`}
                icon={<Users className="h-4 w-4" />}
              />
              <KpiCard
                label="MRR"
                value={`$${parseFloat(analytics.mrr_usd).toLocaleString("en-CA", { minimumFractionDigits: 0 })}`}
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
          <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500 uppercase">
            Pipeline
          </h2>
          {pipelineLoading ? (
            <div className="h-24 animate-pulse rounded-xl bg-gray-100" />
          ) : (
            <div className="grid grid-cols-3 gap-4">
              <KpiCard
                label="Total Jobs"
                value={pipelineData?.jobs?.length ?? 0}
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
