import { redirect } from "next/navigation";
import { auth0 } from "@/lib/auth0";
import { getDevSession } from "@/lib/dev-session";
import { QueryProvider } from "@/lib/providers/QueryProvider";
import { PortalHeader } from "@/components/layout/PortalHeader";
import { PortalFooter } from "@/components/layout/PortalFooter";

/**
 * Layout for independent teacher pages (no school affiliation required).
 * Uses Auth0 session or dev session — same as the school layout but without
 * SchoolNav (which requires a school_id).
 */
export default async function TeacherLayout({ children }: { children: React.ReactNode }) {
  const session = (await auth0.getSession()) ?? (await getDevSession());

  if (!session) {
    redirect("/school/login");
  }

  const userName = session.user.name ?? session.user.email ?? undefined;

  return (
    <QueryProvider>
      <div className="flex min-h-screen flex-col bg-gray-50">
        <PortalHeader portal="school" userName={userName} />
        <main id="main-content" className="flex-1">{children}</main>
        <PortalFooter />
      </div>
    </QueryProvider>
  );
}
