import Link from "next/link";

/**
 * Sitewide footer.
 *
 * The help/legal links below satisfy WCAG 2.2 SC 3.2.6 (Consistent Help):
 * help and contact mechanisms must appear in the same location across pages.
 * Placing them here ensures they are present on every page that uses this layout.
 */
export function PortalFooter() {
  const year = new Date().getFullYear();

  return (
    <footer
      aria-label="Footer"
      className="flex-shrink-0 border-t border-gray-100 bg-gray-50"
    >
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-y-2 px-4 py-3 text-xs text-gray-400">
        <span>© {year} StudyBuddy</span>

        <nav aria-label="Footer links">
          <ul className="flex flex-wrap items-center gap-x-4 gap-y-1">
            {[
              { href: "/about", label: "About" },
              { href: "/accessibility", label: "Accessibility" },
              { href: "/privacy", label: "Privacy" },
              { href: "/terms", label: "Terms" },
              { href: "/contact", label: "Contact" },
            ].map(({ href, label }) => (
              <li key={href}>
                <Link
                  href={href}
                  className="transition-colors hover:text-gray-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                >
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
