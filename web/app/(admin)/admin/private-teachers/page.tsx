"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  listAdminPrivateTeachers,
  type AdminPrivateTeacherItem,
} from "@/lib/api/admin";
import { useAdmin, hasPermission } from "@/lib/hooks/useAdmin";
import { ShieldOff, Users, CheckCircle2, XCircle, Clock } from "lucide-react";

const PAGE_SIZE = 20;

function PlanBadge({ plan }: { plan: string | null }) {
  if (!plan) {
    return (
      <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
        No plan
      </span>
    );
  }
  const isProPlan = plan === "pro";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
        isProPlan
          ? "bg-indigo-100 text-indigo-700"
          : "bg-blue-100 text-blue-700"
      }`}
    >
      {plan.charAt(0).toUpperCase() + plan.slice(1)}
    </span>
  );
}

function SubStatusBadge({ status }: { status: string | null }) {
  if (!status) {
    return (
      <span className="text-xs text-gray-400">—</span>
    );
  }

  const meta: Record<string, { icon: React.ReactNode; className: string; label: string }> = {
    active: {
      icon: <CheckCircle2 className="h-3 w-3 shrink-0" aria-hidden="true" />,
      className: "bg-green-100 text-green-700",
      label: "Active",
    },
    trialing: {
      icon: <Clock className="h-3 w-3 shrink-0" aria-hidden="true" />,
      className: "bg-yellow-100 text-yellow-700",
      label: "Trialing",
    },
    past_due: {
      icon: <Clock className="h-3 w-3 shrink-0" aria-hidden="true" />,
      className: "bg-orange-100 text-orange-700",
      label: "Past Due",
    },
    cancelled: {
      icon: <XCircle className="h-3 w-3 shrink-0" aria-hidden="true" />,
      className: "bg-red-100 text-red-600",
      label: "Cancelled",
    },
  };

  const m = meta[status] ?? {
    icon: null,
    className: "bg-gray-100 text-gray-500",
    label: status,
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${m.className}`}
    >
      {m.icon}
      {m.label}
    </span>
  );
}

export default function AdminPrivateTeachersPage() {
  const admin = useAdmin();
  const [nameSearch, setNameSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "private-teachers", page, nameSearch],
    queryFn: () =>
      listAdminPrivateTeachers(page, PAGE_SIZE, nameSearch || undefined),
    staleTime: 30_000,
  });

  if (admin && !hasPermission(admin.role, "product_admin")) {
    return (
      <div className="mx-auto max-w-lg p-8">
        <div className="mb-2 flex items-center gap-3 text-red-600">
          <ShieldOff className="h-5 w-5" />
          <span className="font-semibold">Access denied</span>
        </div>
        <p className="text-sm text-gray-500">
          Managing private teachers requires <strong>product_admin</strong> or higher.
        </p>
      </div>
    );
  }

  function applySearch(e: React.FormEvent) {
    e.preventDefault();
    setNameSearch(searchInput.trim());
    setPage(1);
  }

  const teachers = data?.teachers ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="mx-auto max-w-6xl p-8">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">Private Teachers</h1>
      <p className="mb-6 text-sm text-gray-500">
        Teachers with their own subscription who upload custom curricula for their students.
      </p>

      {/* Search */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <form onSubmit={applySearch} className="flex gap-2">
          <input
            type="text"
            placeholder="Search by name or email…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          />
          <button
            type="submit"
            className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-200"
          >
            Search
          </button>
          {nameSearch && (
            <button
              type="button"
              onClick={() => {
                setSearchInput("");
                setNameSearch("");
                setPage(1);
              }}
              className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-500 transition-colors hover:bg-gray-200"
            >
              Clear
            </button>
          )}
        </form>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      ) : teachers.length > 0 ? (
        <>
          <p className="mb-2 text-xs text-gray-400">
            {total} teacher{total !== 1 ? "s" : ""}
          </p>
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Email
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Plan
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Curricula
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Joined
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {teachers.map((item: AdminPrivateTeacherItem) => (
                  <tr key={item.teacher_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {item.name}
                    </td>
                    <td className="max-w-[200px] truncate px-4 py-3 text-gray-600">
                      {item.email}
                    </td>
                    <td className="px-4 py-3">
                      <PlanBadge plan={item.plan} />
                    </td>
                    <td className="px-4 py-3">
                      <SubStatusBadge status={item.subscription_status} />
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {item.curricula_count}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="mt-4 flex items-center gap-3">
            <button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-200 disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">Page {page}</span>
            <button
              disabled={teachers.length < PAGE_SIZE}
              onClick={() => setPage(page + 1)}
              className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-200 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <div className="py-20 text-center text-gray-400">
          <Users className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="text-sm">No private teachers found.</p>
        </div>
      )}
    </div>
  );
}
