"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { GraduationCap, LogOut, BookOpen, Users, BarChart2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { demoTeacherLogout } from "@/lib/api/demo";

export default function DemoTeacherDashboard() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("sb_teacher_token");
    if (!token) {
      router.replace("/demo/teacher/login");
      return;
    }
    // Decode email from session cookie written at login
    try {
      const raw = document.cookie
        .split("; ")
        .find((c) => c.startsWith("sb_teacher_session="))
        ?.split("=")[1];
      if (raw) {
        const payload = JSON.parse(atob(raw));
        setEmail(payload.email ?? null);
      }
    } catch {
      // cookie missing or malformed — still show dashboard
    }
  }, [router]);

  async function handleLogout() {
    setLoggingOut(true);
    const token = localStorage.getItem("sb_teacher_token");
    try {
      if (token) await demoTeacherLogout(token);
    } catch {
      // best-effort
    } finally {
      localStorage.removeItem("sb_teacher_token");
      document.cookie = "sb_teacher_session=; path=/; max-age=0";
      router.replace("/demo/teacher/login");
    }
  }

  return (
    <div className="min-h-[80vh] px-4 py-12">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GraduationCap className="h-6 w-6 text-cyan-600" />
            <span className="text-lg font-bold text-gray-900">StudyBuddy</span>
            <span className="rounded bg-cyan-100 px-1.5 py-0.5 text-xs font-semibold text-cyan-700">
              Teacher Demo
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleLogout}
            disabled={loggingOut}
            className="gap-1.5"
          >
            <LogOut className="h-4 w-4" />
            {loggingOut ? "Signing out…" : "Sign out"}
          </Button>
        </div>

        {/* Welcome */}
        <div className="mb-8 rounded-xl border bg-white p-6 shadow-sm">
          <h1 className="mb-1 text-xl font-semibold text-gray-900">
            Welcome to your demo account
          </h1>
          {email && <p className="text-sm text-gray-500">{email}</p>}
          <p className="mt-3 text-sm text-gray-600">
            This is a 48-hour demo environment. Explore the teacher features below.
            Your account and any data created here will be removed after the demo
            period ends.
          </p>
        </div>

        {/* Feature cards */}
        <div className="grid gap-4 sm:grid-cols-3">
          <FeatureCard
            icon={<BookOpen className="h-5 w-5 text-cyan-600" />}
            title="Curriculum"
            description="Browse lessons, quizzes, and activities across all grades."
          />
          <FeatureCard
            icon={<Users className="h-5 w-5 text-cyan-600" />}
            title="Class Roster"
            description="Manage students and track enrolment for your school."
          />
          <FeatureCard
            icon={<BarChart2 className="h-5 w-5 text-cyan-600" />}
            title="Reports"
            description="View progress reports, quiz scores, and engagement metrics."
          />
        </div>

        <p className="mt-8 text-center text-xs text-gray-400">
          Want full access?{" "}
          <a
            href="/school"
            className="text-cyan-600 underline underline-offset-2 hover:text-cyan-800"
          >
            Learn about school accounts →
          </a>
        </p>
      </div>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border bg-white p-5 shadow-sm">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-50">
        {icon}
      </div>
      <h2 className="mb-1 text-sm font-semibold text-gray-900">{title}</h2>
      <p className="text-xs text-gray-500">{description}</p>
    </div>
  );
}
