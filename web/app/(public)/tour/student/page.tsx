import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Student Tour — Coming Soon | StudyBuddy OnDemand",
};

export default function StudentTourPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-6 text-center">
      <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-green-500">
        Student tour
      </p>
      <h1 className="mb-3 text-2xl font-bold text-gray-900">Coming soon</h1>
      <p className="mb-8 max-w-sm text-sm text-gray-500">
        The student experience tour is under construction. Students access
        StudyBuddy through credentials provided by their school — ask your
        teacher or school admin for your login details.
      </p>
      <Link
        href="/tour"
        className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-700"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to role selector
      </Link>
    </div>
  );
}
