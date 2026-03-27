import { redirect } from "next/navigation";
import { auth0 } from "@/lib/auth0";
import { StudentNav } from "@/components/layout/StudentNav";
import { QueryProvider } from "@/lib/providers/QueryProvider";
import { TrialBanner } from "@/components/student/TrialBanner";

export default async function StudentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth0.getSession();

  if (!session) {
    redirect("/login");
  }

  return (
    <QueryProvider>
      <div className="flex min-h-screen bg-gray-50">
        <StudentNav />
        <div className="flex flex-1 flex-col overflow-auto">
          <TrialBanner />
          <main id="main-content" className="flex-1">
            {children}
          </main>
        </div>
      </div>
    </QueryProvider>
  );
}
