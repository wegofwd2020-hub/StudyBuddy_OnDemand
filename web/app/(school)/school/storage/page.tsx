"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getSchoolStorage,
  createStorageCheckout,
  type StorageBreakdownItem,
} from "@/lib/api/school-admin";
import { STORAGE_PACKAGES } from "@/lib/pricing";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, HardDrive, AlertTriangle, CheckCircle, BookOpen, CreditCard } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Quota bar ─────────────────────────────────────────────────────────────────

function QuotaBar({ usedGb, totalGb, usedPct }: { usedGb: number; totalGb: number; usedPct: number }) {
  const isWarning = usedPct >= 80;
  const isFull = usedPct >= 100;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-600">Storage used</span>
        <span
          className={cn(
            "font-medium tabular-nums",
            isFull ? "text-red-600" : isWarning ? "text-amber-600" : "text-gray-700",
          )}
        >
          {usedGb.toFixed(2)} GB / {totalGb} GB
          <span className="ml-1.5 text-xs font-normal text-gray-400">({usedPct.toFixed(1)}%)</span>
        </span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-gray-100">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            isFull ? "bg-red-500" : isWarning ? "bg-amber-400" : "bg-blue-500",
          )}
          style={{ width: `${Math.min(usedPct, 100)}%` }}
        />
      </div>
      {isWarning && !isFull && (
        <p className="flex items-center gap-1.5 text-xs text-amber-600">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          Storage is {usedPct.toFixed(0)}% full — consider purchasing additional storage.
        </p>
      )}
      {isFull && (
        <p className="flex items-center gap-1.5 text-xs text-red-600">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          Storage quota exceeded — new pipeline builds will fail until you add more storage.
        </p>
      )}
    </div>
  );
}

// ── Breakdown row ─────────────────────────────────────────────────────────────

function BreakdownRow({ item, totalGb }: { item: StorageBreakdownItem; totalGb: number }) {
  const pct = totalGb > 0 ? (item.gb_used / totalGb) * 100 : 0;

  return (
    <tr className="border-b last:border-0">
      <td className="py-3 pr-4">
        <div className="flex items-center gap-2">
          <BookOpen className="h-3.5 w-3.5 shrink-0 text-gray-400" />
          <span className="text-sm text-gray-800">{item.name}</span>
        </div>
      </td>
      <td className="py-3 pr-4 text-center">
        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
          Grade {item.grade}
        </span>
      </td>
      <td className="py-3 pr-4 text-right font-mono text-sm tabular-nums text-gray-700">
        {item.gb_used.toFixed(2)} GB
      </td>
      <td className="py-3 pr-4 text-right text-xs text-gray-400 tabular-nums">
        {item.job_count} build{item.job_count !== 1 ? "s" : ""}
      </td>
      <td className="py-3 w-32">
        <div className="h-1.5 overflow-hidden rounded-full bg-gray-100">
          <div className="h-full rounded-full bg-blue-400" style={{ width: `${Math.min(pct, 100)}%` }} />
        </div>
      </td>
    </tr>
  );
}

// ── Storage add-on card ───────────────────────────────────────────────────────

function AddOnCard({
  gb,
  priceUsd,
  label,
  onBuy,
  isLoading,
}: {
  gb: number;
  priceUsd: string;
  label: string;
  onBuy: () => void;
  isLoading: boolean;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3">
      <div>
        <p className="text-sm font-medium text-gray-900">+{gb} GB</p>
        <p className="text-xs text-gray-500">One-time · never expires</p>
      </div>
      <div className="flex items-center gap-3">
        <span className="font-mono text-sm font-semibold text-gray-800">
          ${parseFloat(priceUsd).toFixed(0)}
        </span>
        <Button size="sm" variant="outline" onClick={onBuy} disabled={isLoading} className="gap-1.5">
          {isLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CreditCard className="h-3.5 w-3.5" />}
          Buy
        </Button>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function StoragePage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";

  const [origin, setOrigin] = useState("");
  useEffect(() => { setOrigin(window.location.origin); }, []);

  const [buyingGb, setBuyingGb] = useState<number | null>(null);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);

  const { data: storage, isLoading } = useQuery({
    queryKey: ["school-storage", schoolId],
    queryFn: () => getSchoolStorage(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
    refetchInterval: 5 * 60_000, // refresh every 5 min
  });

  async function handleBuy(gb: number) {
    if (!origin) return;
    setBuyingGb(gb);
    setCheckoutError(null);
    try {
      const { checkout_url } = await createStorageCheckout(
        schoolId,
        gb as 5 | 10 | 25,
        `${origin}/school/storage?success=1`,
        `${origin}/school/storage?cancelled=1`,
      );
      window.location.href = checkout_url;
    } catch {
      setCheckoutError("Could not start checkout. Please try again.");
      setBuyingGb(null);
    }
  }

  return (
    <div className="max-w-3xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Storage</h1>
        <p className="mt-1 text-sm text-gray-500">
          Curriculum content generated by pipeline builds is stored here.
        </p>
      </div>

      {/* Quota card */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <HardDrive className="h-4 w-4 text-gray-400" />
            Quota
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading…
            </div>
          ) : storage ? (
            <div className="space-y-4">
              <QuotaBar
                usedGb={storage.used_gb}
                totalGb={storage.total_gb}
                usedPct={storage.used_pct}
              />

              {/* Quota breakdown: base + purchased */}
              <div className="flex gap-6 text-xs text-gray-500">
                <span>
                  <span className="font-medium text-gray-700">{storage.base_gb} GB</span> base (plan)
                </span>
                {storage.purchased_gb > 0 && (
                  <span>
                    <span className="font-medium text-gray-700">+{storage.purchased_gb} GB</span> purchased
                  </span>
                )}
                <span>
                  <span className="font-medium text-gray-700">{storage.total_gb} GB</span> total
                </span>
              </div>

              {/* Over-quota badge */}
              {storage.over_quota && (
                <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  Quota exceeded — purchase additional storage to resume pipeline builds.
                </div>
              )}

              {!storage.over_quota && storage.used_pct < 80 && (
                <div className="flex items-center gap-2 text-xs text-green-600">
                  <CheckCircle className="h-3.5 w-3.5 shrink-0" />
                  Storage is healthy.
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400">No storage data available.</p>
          )}
        </CardContent>
      </Card>

      {/* Per-curriculum breakdown */}
      {storage && storage.breakdown.length > 0 && (
        <Card className="border shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Breakdown by curriculum</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-gray-50 text-left text-xs font-medium text-gray-500">
                  <th className="px-4 py-2">Curriculum</th>
                  <th className="px-4 py-2 text-center">Grade</th>
                  <th className="px-4 py-2 text-right">Used</th>
                  <th className="px-4 py-2 text-right">Builds</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="px-4">
                {storage.breakdown.map((item) => (
                  <tr key={item.curriculum_id} className="border-b px-4 last:border-0">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <BookOpen className="h-3.5 w-3.5 shrink-0 text-gray-400" />
                        <span className="text-sm text-gray-800">{item.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                        Grade {item.grade}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-sm tabular-nums text-gray-700">
                      {item.gb_used.toFixed(2)} GB
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-gray-400 tabular-nums">
                      {item.job_count} build{item.job_count !== 1 ? "s" : ""}
                    </td>
                    <td className="px-4 py-3 w-32">
                      <div className="h-1.5 overflow-hidden rounded-full bg-gray-100">
                        <div
                          className="h-full rounded-full bg-blue-400"
                          style={{ width: `${Math.min((item.gb_used / storage.total_gb) * 100, 100)}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Empty breakdown */}
      {storage && storage.breakdown.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-200 px-6 py-10 text-center">
          <HardDrive className="mx-auto mb-2 h-8 w-8 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">No content built yet</p>
          <p className="mt-1 text-xs text-gray-400">
            Storage usage will appear here after your first pipeline build completes.
          </p>
        </div>
      )}

      {/* Add-on purchase — admins only */}
      {isAdmin && (
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-gray-900">Purchase additional storage</h2>
          <p className="text-sm text-gray-500">
            One-time purchases. Storage never expires and carries over on plan changes.
          </p>

          {checkoutError && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {checkoutError}
            </div>
          )}

          <div className="space-y-2">
            {STORAGE_PACKAGES.map((pkg) => (
              <AddOnCard
                key={pkg.gb}
                gb={pkg.gb}
                priceUsd={pkg.priceUsd}
                label={pkg.label}
                onBuy={() => handleBuy(pkg.gb)}
                isLoading={buyingGb === pkg.gb}
              />
            ))}
          </div>
        </div>
      )}

      {!isAdmin && (
        <p className="text-center text-xs text-gray-400">
          Only school administrators can purchase additional storage.
        </p>
      )}
    </div>
  );
}
