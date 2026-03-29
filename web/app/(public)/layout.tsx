import { PublicNav } from "@/components/layout/PublicNav";
import { PortalHeader } from "@/components/layout/PortalHeader";
import { PortalFooter } from "@/components/layout/PortalFooter";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <PublicNav />
      <PortalHeader portal="public" />
      <main id="main-content" className="flex-1">
        {children}
      </main>
      <PortalFooter />
    </>
  );
}
