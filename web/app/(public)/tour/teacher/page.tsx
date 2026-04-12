import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";

export const metadata: Metadata = {
  title: "Teacher Tour — Coming Soon | StudyBuddy OnDemand",
};

export default function TeacherTourPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-6 text-center">
      <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-blue-500">
        Teacher tour
      </p>
      <h1 className="mb-3 text-2xl font-bold text-gray-900">Coming soon</h1>
      <p className="mb-8 max-w-sm text-sm text-gray-500">
        The teacher capability tour is under construction. In the meantime, you
        can log in directly with your school credentials.
      </p>
      <div className="flex flex-col items-center gap-3 sm:flex-row">
        <Link
          href="/school/login"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Teacher / Admin login
          <ArrowRight className="h-4 w-4" />
        </Link>
        <Link
          href="/tour"
          className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to role selector
        </Link>
      </div>
    </div>
  );
}
