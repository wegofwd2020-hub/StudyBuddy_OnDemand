import { PublicNav } from "@/components/layout/PublicNav";
import { PortalHeader } from "@/components/layout/PortalHeader";
import { PortalFooter } from "@/components/layout/PortalFooter";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    // sb-warm-neutrals re-tints gray/slate to a warm scale for public pages only
    // (see the block in app/globals.css). It is display:contents, so nav, main
    // and footer stay direct flex children of <body> and `flex-1` still works.
    <div className="sb-warm-neutrals">
      <PublicNav />
      <PortalHeader portal="public" />
      <main id="main-content" className="flex-1">
        {children}
      </main>
      <PortalFooter />
    </div>
  );
}
