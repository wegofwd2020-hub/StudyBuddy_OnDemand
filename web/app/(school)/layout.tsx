import { redirect } from "next/navigation";
import { auth0 } from "@/lib/auth0";
import { SchoolNav } from "@/components/layout/SchoolNav";
import { QueryProvider } from "@/lib/providers/QueryProvider";

export default async function SchoolLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth0.getSession();

  if (!session) {
    redirect("/school/login");
  }

  return (
    <QueryProvider>
      <div className="flex min-h-screen bg-gray-50">
        <SchoolNav />
        <main id="main-content" className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </QueryProvider>
  );
}
