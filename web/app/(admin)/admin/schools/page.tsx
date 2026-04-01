"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listAdminSchools, type AdminSchoolListItem } from "@/lib/api/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Loader2, Search, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Plan badge ────────────────────────────────────────────────────────────────

function PlanBadge({ plan, subStatus }: { plan: string; subStatus: string | null }) {
  const styles: Record<string, string> = {
    enterprise: "bg-purple-100 text-purple-700",
    professional: "bg-blue-100 text-blue-700",
    starter: "bg-gray-100 text-gray-600",
    none: "bg-gray-100 text-gray-400",
  };
  const inactive = subStatus && !["active", "trialing"].includes(subStatus);
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize",
        styles[plan] ?? "bg-gray-100 text-gray-600",
        inactive && "opacity-60",
      )}
    >
      {plan}
      {inactive && <span className="ml-1 text-gray-400">({subStatus})</span>}
    </span>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

export default function AdminSchoolsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Simple debounce via onChange + setTimeout
  function handleSearch(value: string) {
    setSearch(value);
    clearTimeout((handleSearch as unknown as { _t?: ReturnType<typeof setTimeout> })._t);
    (handleSearch as unknown as { _t?: ReturnType<typeof setTimeout> })._t = setTimeout(() => {
      setDebouncedSearch(value);
      setPage(1);
    }, 300);
  }

  const { data, isLoading } = useQuery({
    queryKey: ["admin-schools", page, debouncedSearch],
    queryFn: () => listAdminSchools(page, PAGE_SIZE, debouncedSearch || undefined),
    staleTime: 30_000,
  });

  const schools: AdminSchoolListItem[] = data?.schools ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="max-w-6xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Schools</h1>
        <div className="relative w-64">
          <Search className="absolute top-1/2 left-2.5 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search name or email…"
            className="pl-8"
          />
        </div>
      </div>

      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {total} school{total !== 1 ? "s" : ""}
            {debouncedSearch ? ` matching "${debouncedSearch}"` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : schools.length === 0 ? (
            <p className="py-10 text-center text-sm text-gray-400">No schools found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      School
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      Plan
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      Students
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      Teachers
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      Country
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      Joined
                    </th>
                    <th className="w-16 px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {schools.map((school) => (
                    <tr key={school.school_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div>
                            <p className="font-medium text-gray-800">{school.name}</p>
                            <p className="text-xs text-gray-400">{school.contact_email}</p>
                          </div>
                          {school.has_override && (
                            <span title="Has limit override">
                              <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <PlanBadge
                          plan={school.plan}
                          subStatus={school.subscription_status}
                        />
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        {school.seats_used_students}
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        {school.seats_used_teachers}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500 uppercase">
                        {school.country}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {new Date(school.created_at).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/admin/schools/${school.school_id}`}
                          className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
                        >
                          Manage →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {pageCount > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded-md border border-gray-200 px-3 py-1.5 text-xs disabled:opacity-40 hover:bg-gray-50"
          >
            ← Prev
          </button>
          <span className="text-xs text-gray-500">
            Page {page} of {pageCount}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
            disabled={page === pageCount}
            className="rounded-md border border-gray-200 px-3 py-1.5 text-xs disabled:opacity-40 hover:bg-gray-50"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
