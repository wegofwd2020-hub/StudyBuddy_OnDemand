import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { auth0 } from "@/lib/auth0";
import { getDevSession } from "@/lib/dev-session";
import { StudentNav } from "@/components/layout/StudentNav";
import { QueryProvider } from "@/lib/providers/QueryProvider";
import { TrialBanner } from "@/components/student/TrialBanner";
import { DemoBanner } from "@/components/demo/DemoBanner";
import { PortalHeader } from "@/components/layout/PortalHeader";
import { PortalFooter } from "@/components/layout/PortalFooter";
import { StudentPortalThemeProvider } from "@/lib/theme/SchoolThemeContext";

export const metadata: Metadata = {
  title: "Student | StudyBuddy",
};

export default async function StudentLayout({ children }: { children: React.ReactNode }) {
  const session = (await auth0.getSession()) ?? (await getDevSession());

  if (!session) {
    redirect("/login");
  }

  const userName = session.user.name ?? session.user.email ?? undefined;

  return (
    <QueryProvider>
      <StudentPortalThemeProvider>
        <div className="flex min-h-screen bg-gray-50">
          <StudentNav />
          <div className="flex flex-1 flex-col overflow-auto">
            <PortalHeader portal="student" userName={userName} />
            <DemoBanner />
            <TrialBanner />
            <main id="main-content" className="flex-1">
              {children}
            </main>
            <PortalFooter />
          </div>
        </div>
      </StudentPortalThemeProvider>
    </QueryProvider>
  );
}
