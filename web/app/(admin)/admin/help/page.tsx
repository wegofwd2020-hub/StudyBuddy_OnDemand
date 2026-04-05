"use client";

import { useState } from "react";
import { MindMap } from "@/components/help/MindMap";
import { HELP_MINDMAPS } from "@/lib/content/help-mindmaps";
import { HelpCircle, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

const ADMIN_PERSONAS = ["super-admin"];

const GETTING_STARTED = [
  {
    step: "1",
    title: "Log in",
    body: "Go to /admin/login and sign in with your admin credentials. Your role (developer / tester / product_admin / super_admin) determines which pages are visible.",
  },
  {
    step: "2",
    title: "Dashboard",
    body: "The dashboard shows live subscription KPIs — total active students, MRR, new sign-ups, and churn. The pipeline section shows recent job status.",
  },
  {
    step: "3",
    title: "Content Review",
    body: "Open the review queue, filter by status (pending / in_review / approved), and click Review to open a version. Browse units, add inline annotations, then approve or reject.",
  },
  {
    step: "4",
    title: "Pipeline",
    body: "Upload a grade JSON file then trigger a build. Monitor the job list — each job shows built / failed / total counts and payload size. Click a job for full detail.",
  },
  {
    step: "5",
    title: "Demo Accounts",
    body: "Student and teacher demo requests appear here. Approve a request to provision a temporary account. Extend expiry or revoke at any time.",
  },
];

export default function AdminHelpPage() {
  const maps = HELP_MINDMAPS.filter((m) => ADMIN_PERSONAS.includes(m.id));
  const [expanded, setExpanded] = useState<string | null>(maps[0]?.id ?? null);

  return (
    <div className="max-w-5xl space-y-8 p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <HelpCircle className="h-7 w-7 text-indigo-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">Help &amp; Tutorial</h1>
          <p className="text-sm text-gray-400">
            Visual guide to the Admin Console — what you can do and where to find it.
          </p>
        </div>
      </div>

      {/* Getting started steps */}
      <section>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-400">
          Getting Started
        </h2>
        <ol className="space-y-3">
          {GETTING_STARTED.map((s) => (
            <li key={s.step} className="flex gap-4 rounded-lg bg-gray-800 p-4">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                {s.step}
              </span>
              <div>
                <p className="font-medium text-white">{s.title}</p>
                <p className="mt-0.5 text-sm text-gray-400">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Mind maps */}
      <section>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-400">
          Persona Mind Map
        </h2>
        <div className="space-y-4">
          {maps.map((map) => (
            <div key={map.id} className="overflow-hidden rounded-xl border border-gray-700">
              <button
                className={cn(
                  "flex w-full items-center justify-between px-5 py-4 text-left transition-colors",
                  map.color,
                )}
                onClick={() => setExpanded(expanded === map.id ? null : map.id)}
                aria-expanded={expanded === map.id}
              >
                <div>
                  <p className="font-semibold text-white">{map.title}</p>
                  <p className="text-sm text-white/70">{map.subtitle}</p>
                </div>
                {expanded === map.id ? (
                  <ChevronUp className="h-5 w-5 shrink-0 text-white" />
                ) : (
                  <ChevronDown className="h-5 w-5 shrink-0 text-white" />
                )}
              </button>

              {expanded === map.id && (
                <div className="bg-white p-4">
                  <MindMap diagram={map.diagram} className="min-h-[400px]" />
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Quick reference */}
      <section>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-400">
          Quick Reference
        </h2>
        <div className="overflow-hidden rounded-xl border border-gray-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 bg-gray-800">
                <th className="px-4 py-2 text-left font-medium text-gray-300">Task</th>
                <th className="px-4 py-2 text-left font-medium text-gray-300">Where</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {[
                ["Approve / publish content", "/admin/content-review → version detail"],
                ["Trigger pipeline build", "/admin/pipeline/upload"],
                ["View subscription MRR", "/admin/dashboard or /admin/analytics"],
                ["Manage demo student accounts", "/admin/demo-accounts"],
                ["Manage demo teacher accounts", "/admin/demo-teacher-accounts"],
                ["View audit log", "/admin/audit"],
                ["Check system health", "/admin/health"],
                ["View student feedback", "/admin/feedback"],
              ].map(([task, where]) => (
                <tr key={task} className="bg-gray-900">
                  <td className="px-4 py-2 text-gray-300">{task}</td>
                  <td className="px-4 py-2 font-mono text-xs text-indigo-400">{where}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
