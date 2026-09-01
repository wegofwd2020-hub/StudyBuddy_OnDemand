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
    body: "Go to /signin and enter your school-issued email and password. The same page handles teachers, school admins, and students — the system routes you to the right portal automatically based on your account.",
  },
  {
    step: "2",
    title: "Classrooms — focus on yours",
    body: 'Classrooms list defaults to a "My classrooms" view showing the rooms you lead. Toggle to "All classrooms" to peek at the rest of the school. The grade filter only lists grades that actually have a classroom — no clutter.',
  },
  {
    step: "3",
    title: "Student Progress — students you teach",
    body: 'Same toggle pattern: "My students" shows everyone enrolled in classrooms you lead; "All school" shows the wider roster. Grade pills auto-narrow to grades present in the current view.',
  },
  {
    step: "4",
    title: "Lessons & Content",
    body: 'Browse AI-generated lessons, tutorials, quizzes, and activities. Default view is "My content" — the subjects your classrooms have adopted. Each subject row rolls up multiple regenerations into one — if you see a "4 versions" chip, the link opens the latest. Lesson images are clickable — tap to enlarge in a lightbox.',
  },
  {
    step: "5",
    title: "Reports",
    body: "Check the Overview for class-level stats, drill into At-Risk to spot struggling students, or view Unit Performance to find difficult content.",
  },
  {
    step: "6",
    title: "Alerts & Digest",
    body: "Alerts notify you when thresholds are breached (e.g. class average drops below 60%). Tune the thresholds in Alert Settings, and use Digest Settings to subscribe to a weekly email summary.",
  },
  {
    step: "7",
    title: "Exports",
    body: "Export CSV downloads the Overview, Trends or Unit Performance report. Pick the period before downloading — Overview offers 7 days / 30 days / this term, Trends offers 4 weeks / 12 weeks / this term (it's grouped into whole weeks). Unit Performance covers all activity to date.",
  },
  {
    step: "8",
    title: "Student feedback",
    body: "Students rate lessons and tutorials with a thumbs up/down and can leave a comment. The Feedback report collects them per unit, so repeated thumbs-down on one unit is a signal to look at that content.",
  },
];

// Admin steps continue the teacher list, so their numbers are derived rather
// than written down — adding a teacher step used to silently create two step
// 7s.
const ADMIN_ONLY = [
  {
    title: "Set up your school",
    body: "The Get started checklist walks the whole first-run setup — adding teachers and students, creating classrooms, adopting curricula. It ticks items off automatically as you complete them, so it's safe to leave and come back.",
  },
  {
    title: "Teachers & Students",
    body: "Provision accounts from the Administration menu. Provisioned users get a temporary password emailed to them and must reset it on first login. School Admin is a superset of Teacher — an admin can do everything a teacher can, plus user management.",
  },
  {
    title: "Curriculum library",
    body: "Browse the platform Catalog and adopt curricula for your school. Adopted content can be edited: an import creates your school's own copy, and edits go through draft → review → approved before students see them.",
  },
  {
    title: "Curriculum Upload & Pipeline",
    body: "Upload a grade curriculum JSON file, then trigger the AI pipeline to generate lessons and quizzes. Monitor job progress in Pipeline Jobs. You can also define a curriculum in the builder and submit it for approval instead of uploading a file.",
  },
  {
    title: "Backups & Restore",
    body: "Curriculum backups run on a schedule you control. To roll something back, raise a restore request — it shows you a dry run of exactly what would change, and needs confirming before anything is written.",
  },
  {
    title: "Branding",
    body: "Customise your school's colours and logo in Settings → Customize. It applies across the portal your teachers and students see.",
  },
  {
    title: "Subscription & Storage",
    body: "View your plan limits (students, teachers, pipeline quota) on Subscription, and current content storage use on Storage.",
  },
  {
    title: "Content Retention",
    body: "Manage curriculum version lifecycle from the Content Retention page. See which versions are active, unavailable (expired), or purged. Renew expiring content with one click, pay for a renewal via Stripe, or purchase additional storage. Assign a specific curriculum version as the live content source for each grade.",
  },
];

const GETTING_STARTED_ADMIN = [
  ...GETTING_STARTED_TEACHER,
  ...ADMIN_ONLY.map((s, i) => ({
    ...s,
    step: String(GETTING_STARTED_TEACHER.length + i + 1),
  })),
];

// Teacher-focused FAQ (#370) — task-oriented answers distinct from the
// student help, each pointing at the portal location that resolves it.
const TEACHER_FAQ: { q: string; a: string; where: string }[] = [
  {
    q: "How do I see which of my students are struggling?",
    a: "The At-Risk report flags students below your school's thresholds (low scores, inactivity, repeated quiz failures). The dashboard also surfaces unread alerts when a class average drops.",
    where: "/school/reports/at-risk",
  },
  {
    q: "Where do I find the lessons for my class?",
    a: 'Open the content browser — it defaults to "My content", the subjects your classrooms have adopted. Pick a subject, then a unit, to read the AI-generated lesson, tutorial, and quizzes.',
    where: "/school/curriculum/content",
  },
  {
    q: "How do I get notified when a class is falling behind?",
    a: "Alerts fire automatically when a threshold is breached. Turn on a weekly email summary in Digest Settings so you don't have to check manually.",
    where: "/school/digest",
  },
  {
    q: "Can I focus on just my own classes instead of the whole school?",
    a: 'Both the Classrooms and Student Progress pages default to a "My" view (rooms you lead / students you teach). Toggle to "All school" only when you need the wider picture.',
    where: "/school/classrooms",
  },
  {
    q: "How do I track one student's progress over time?",
    a: "Open the Students roster and click a student row for their per-unit history, quiz attempts, and recent activity.",
    where: "/school/students",
  },
  {
    q: "Can I make a lesson easier to read for a student?",
    a: "Lesson content already targets a reading level one to two grades below the student's grade. For dyslexia support, toggle the dyslexia-friendly font from the Eye icon in the top bar (or press Alt+D).",
    where: "Top bar → Eye icon (Alt+D)",
  },
  // The questions below came from real reports rather than guesswork — each one
  // is a number or behaviour a teacher queried, so the answer belongs here and
  // not only in a reply.
  {
    q: "A student can't start a quiz — is something broken?",
    a: "No. A quiz opens once the student has opened that unit's lesson, so they arrive having read it. Their screen offers a link straight to the lesson. Students who already attempted a unit keep access to its quiz, and if a unit has no lesson available the quiz stays open rather than trapping them.",
    where: "Student view → unit → Lesson, then Quiz",
  },
  {
    q: "Why is the pass rate here different from the one the student sees?",
    a: "They answer different questions, and both are right. Your figure counts FIRST attempts — of the units the student tried, how many they passed first time, which is what tells you where teaching landed. The student's own page counts every attempt, because a retake that succeeds is a pass. Each tile now says which it is.",
    where: "/school/students → student row",
  },
  {
    q: "What does 'In progress' include?",
    a: "Every unit the student has reached and not yet passed — whether they failed the quiz or haven't taken it. 'Units completed' means the quiz was passed. Each tile on the student detail card states its definition.",
    where: "/school/students → student row",
  },
  {
    q: "Reading time doesn't look right against the units listed.",
    a: "The Reading time tile is the total of the Reading time column below it, so the column adds up to the tile. It counts time on lesson, tutorial and activity pages. Anything under a minute shows as '<1m' so a short read isn't indistinguishable from never opening it.",
    where: "/school/students → student row",
  },
  {
    q: "Why does the CSV feedback count differ from the dashboard tile?",
    a: "The dashboard tile counts UNREVIEWED feedback only, including general comments not tied to a unit. The Unit Performance CSV counts all feedback, reviewed or not, but only where it names a unit. Both are scoped to your school.",
    where: "/school/reports/export",
  },
];

function FaqItem({ q, a, where }: { q: string; a: string; where: string }) {
  return (
    <details className="group rounded-lg border border-gray-100 bg-white shadow-sm">
      <summary className="flex cursor-pointer items-center justify-between gap-3 px-4 py-3 font-medium text-gray-900 marker:content-none">
        {q}
        <ChevronDown className="h-4 w-4 shrink-0 text-gray-400 transition-transform group-open:rotate-180" />
      </summary>
      <div className="border-t border-gray-50 px-4 py-3">
        <p className="text-sm text-gray-600">{a}</p>
        <p className="mt-2 font-mono text-xs text-blue-600">{where}</p>
      </div>
    </details>
  );
}

export default function SchoolHelpPage() {
  const teacher = useTeacher();
  const isAdmin = teacher?.role === "school_admin";

  const personaIds = isAdmin ? ["school-admin", "school-teacher"] : ["school-teacher"];
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
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500 uppercase">
          Getting Started
        </h2>
        <ol className="space-y-3">
          {steps.map((s) => (
            <li
              key={s.step}
              className="flex gap-4 rounded-lg border border-gray-100 bg-white p-4 shadow-sm"
            >
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
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500 uppercase">
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
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500 uppercase">
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
                isAdmin && [
                  "Assign grades to a teacher",
                  "/school/teachers → teacher row → Edit grades",
                ],
                isAdmin && ["Upload curriculum JSON", "/school/curriculum → Upload"],
                isAdmin && [
                  "Trigger pipeline build",
                  "/school/curriculum/jobs → Trigger",
                ],
                isAdmin && ["View subscription plan", "/school/subscription"],
                isAdmin && ["View / renew curriculum versions", "/school/retention"],
                isAdmin && [
                  "Purchase storage add-on",
                  "/school/retention → Storage strip",
                ],
                isAdmin && [
                  "Assign curriculum version to a grade",
                  "/school/retention → row → Details → Assign",
                ],
                isAdmin && ["Run the setup checklist", "/school/setup"],
                isAdmin && ["Adopt a platform curriculum", "/school/catalog"],
                isAdmin && ["Edit adopted content", "/school/library"],
                isAdmin && ["Review submitted content edits", "/school/review"],
                isAdmin && [
                  "Define a curriculum for approval",
                  "/school/curriculum/definitions",
                ],
                isAdmin && ["Curriculum backups", "/school/backups"],
                isAdmin && ["Request a restore", "/school/restore-requests/new"],
                isAdmin && [
                  "Brand the portal (colours, logo)",
                  "/school/settings/customize",
                ],
                isAdmin && ["Check storage use", "/school/storage"],
                isAdmin && ["Manage students", "/school/students"],
                ["View AI-generated content", "/school/curriculum/content"],
                ["Browse a unit's lesson", "/school/curriculum/content → subject → unit"],
                ["See class performance", "/school/reports/overview"],
                ["Week-over-week trends", "/school/reports/trends"],
                ["Engagement report", "/school/reports/engagement"],
                ["Unit performance / difficult content", "/school/reports/units"],
                ["Student feedback on content", "/school/reports/feedback"],
                ["Find at-risk students", "/school/reports/at-risk"],
                ["Export a report as CSV (choose the period)", "/school/reports/export"],
                ["Review and dismiss alerts", "/school/alerts"],
                ["Tune alert thresholds", "/school/reports/alerts/settings"],
                ["Weekly email summary", "/school/digest"],
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

      {/* Common teacher questions (#370) — teacher-focused, task-oriented help */}
      <section>
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500 uppercase">
          Common Teacher Questions
        </h2>
        <div className="space-y-2">
          {TEACHER_FAQ.map((f) => (
            <FaqItem key={f.q} q={f.q} a={f.a} where={f.where} />
          ))}
        </div>
      </section>
    </div>
  );
}
