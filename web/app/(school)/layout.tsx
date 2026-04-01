import { redirect } from "next/navigation";
import { auth0 } from "@/lib/auth0";
import { getDevSession, getDemoTeacherSession } from "@/lib/dev-session";
import { SchoolNav } from "@/components/layout/SchoolNav";
import { QueryProvider } from "@/lib/providers/QueryProvider";
import { PortalHeader } from "@/components/layout/PortalHeader";
import { PortalFooter } from "@/components/layout/PortalFooter";

export default async function SchoolLayout({ children }: { children: React.ReactNode }) {
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
            {children}
          </main>
          <PortalFooter />
        </div>
      </div>
    </QueryProvider>
  );
}
