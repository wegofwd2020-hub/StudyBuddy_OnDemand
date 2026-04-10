"use client";

import { useState } from "react";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { MindMap } from "@/components/help/MindMap";
import { HELP_MINDMAPS } from "@/lib/content/help-mindmaps";
import { HelpCircle, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

const GETTING_STARTED_TEACHER = [
  {
    step: "1",
    title: "Log in",
    body: 'Go to /school/login and sign in with your teacher credentials. The portal loads your assigned grades automatically.',
  },
  {
    step: "2",
    title: "Dashboard — My Classes",
    body: "The dashboard shows your assigned grades and a quick class summary. Grades are assigned by your school admin.",
  },
  {
    step: "3",
    title: "Content Library",
    body: "Browse AI-generated lessons, tutorials, quizzes, and activities for your assigned grades. Click a subject to see its units, then click a unit to view the full content.",
  },
  {
    step: "4",
    title: "Reports",
    body: "Check the Overview for class-level stats, drill into At-Risk to spot struggling students, or view Unit Performance to find difficult content.",
  },
  {
    step: "5",
    title: "Alerts & Digest",
    body: "Alerts notify you when thresholds are breached (e.g. class average drops below 60%). Digest Settings let you subscribe to a weekly email summary.",
  },
];

const GETTING_STARTED_ADMIN = [
  ...GETTING_STARTED_TEACHER,
  {
    step: "6",
    title: "Teachers",
    body: "Invite new teachers, view the full teacher roster, and assign grades. A teacher only sees content and students for their assigned grades.",
  },
  {
    step: "7",
    title: "Curriculum Upload",
    body: "Upload a grade curriculum JSON file, then trigger the AI pipeline to generate lessons and quizzes. Monitor job progress in the Pipeline Jobs tab.",
  },
  {
    step: "8",
    title: "Subscription",
    body: "View your current plan limits (students, teachers, pipeline quota). Upgrade or cancel via the Subscription page.",
  },
  {
    step: "9",
    title: "Content Retention",
    body: "Manage curriculum version lifecycle from the Content Retention page. See which versions are active, unavailable (expired), or purged. Renew expiring content with one click, pay for a renewal via Stripe, or purchase additional storage. Assign a specific curriculum version as the live content source for each grade.",
  },
];

export default function SchoolHelpPage() {
  const teacher = useTeacher();
  const isAdmin = teacher?.role === "school_admin";

  const personaIds = isAdmin
    ? ["school-admin", "school-teacher"]
    : ["school-teacher"];
  const maps = HELP_MINDMAPS.filter((m) => personaIds.includes(m.id));
  const steps = isAdmin ? GETTING_STARTED_ADMIN : GETTING_STARTED_TEACHER;

  const [expanded, setExpanded] = useState<string | null>(personaIds[0] ?? null);

  return (
    <div className="max-w-5xl space-y-8 p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <HelpCircle className="h-7 w-7 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Help &amp; Tutorial</h1>
          <p className="text-sm text-gray-500">
            {isAdmin
              ? "School Admin guide — manage teachers, curriculum, and reports."
              : "Teacher guide — browse content and monitor student progress."}
          </p>
        </div>
      </div>

      {/* Getting started */}
      <section>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Getting Started
        </h2>
        <ol className="space-y-3">
          {steps.map((s) => (
            <li key={s.step} className="flex gap-4 rounded-lg border border-gray-100 bg-white p-4 shadow-sm">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                {s.step}
              </span>
              <div>
                <p className="font-medium text-gray-900">{s.title}</p>
                <p className="mt-0.5 text-sm text-gray-500">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Mind maps — one per persona, collapsible */}
      <section>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
          {isAdmin ? "Persona Mind Maps" : "Your Role — Mind Map"}
        </h2>
        <div className="space-y-4">
          {maps.map((map) => (
            <div
              key={map.id}
              className="overflow-hidden rounded-xl border border-gray-200 shadow-sm"
            >
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
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Quick Reference
        </h2>
        <div className="overflow-hidden rounded-xl border border-gray-200 shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-2 text-left font-medium text-gray-600">Task</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Where</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[
                isAdmin && ["Invite a new teacher", "/school/teachers → Invite"],
                isAdmin && ["Assign grades to a teacher", "/school/teachers → teacher row → Edit grades"],
                isAdmin && ["Upload curriculum JSON", "/school/curriculum → Upload"],
                isAdmin && ["Trigger pipeline build", "/school/curriculum/jobs → Trigger"],
                isAdmin && ["View subscription plan", "/school/subscription"],
                isAdmin && ["View / renew curriculum versions", "/school/retention"],
                isAdmin && ["Purchase storage add-on", "/school/retention → Storage strip"],
                isAdmin && ["Assign curriculum version to a grade", "/school/retention → row → Details → Assign"],
                ["View AI-generated content", "/school/curriculum/content"],
                ["Browse a unit's lesson", "/school/curriculum/content → subject → unit"],
                ["See class performance", "/school/reports/overview"],
                ["Find at-risk students", "/school/reports/at-risk"],
                ["Export report as CSV", "/school/reports/export"],
                ["View student detail", "/school/students → student row"],
                ["Toggle dyslexia font", "Eye icon in top-right header, or Alt+D"],
              ]
                .filter((r): r is string[] => Boolean(r))
                .map(([task, where]) => (
                  <tr key={task}>
                    <td className="px-4 py-2 text-gray-700">{task}</td>
                    <td className="px-4 py-2 font-mono text-xs text-blue-600">{where}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
