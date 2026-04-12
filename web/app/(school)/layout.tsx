import { redirect } from "next/navigation";
import { auth0 } from "@/lib/auth0";
import { getDevSession, getDemoTeacherSession, getLocalTeacherSession } from "@/lib/dev-session";
import { SchoolNav } from "@/components/layout/SchoolNav";
import { LimitWarningBanner } from "@/components/school/LimitWarningBanner";
import { LocalAuthGuard } from "@/components/school/LocalAuthGuard";
import { QueryProvider } from "@/lib/providers/QueryProvider";
import { PortalHeader } from "@/components/layout/PortalHeader";
import { PortalFooter } from "@/components/layout/PortalFooter";
import { HelpWidget } from "@/components/help/HelpWidget";

export default async function SchoolLayout({ children }: { children: React.ReactNode }) {
  // Phase A local-auth session — cookie set at login, validated client-side.
  // Check this first so local-auth users never hit the Auth0 redirect.
  const localSession = await getLocalTeacherSession();
  if (localSession) {
    const userName = localSession.user.name ?? localSession.user.email;
    return (
      <QueryProvider>
        {/* LocalAuthGuard validates sb_teacher_token from localStorage,
            enforces first_login redirect (pitfall #24), and renders the
            full portal layout only once the JWT check passes. */}
        <LocalAuthGuard userName={userName}>
          {children}
        </LocalAuthGuard>
      </QueryProvider>
    );
  }

  // Auth0 / dev / demo-teacher session paths (unchanged).
  const session =
    (await auth0.getSession()) ??
    (await getDevSession()) ??
    (await getDemoTeacherSession());

  if (!session) {
    redirect("/school/login");
  }

  const userName = session.user.name ?? session.user.email ?? undefined;

  return (
    <QueryProvider>
      <div className="flex min-h-screen bg-gray-50">
        <SchoolNav />
        <div className="flex flex-1 flex-col overflow-auto">
          <PortalHeader portal="school" userName={userName} />
          <main id="main-content" className="flex-1">
            <LimitWarningBanner />
            {children}
          </main>
          <PortalFooter />
        </div>
        <HelpWidget />
      </div>
    </QueryProvider>
  );
}
