/**
 * Client-side helpers for the SSR session cookies.
 *
 * The student/teacher portal layouts are server components that read the
 * display name from a base64-encoded `{ name, email }` cookie set at login
 * (see `(public)/signin/page.tsx` `persistSession`). A profile display-name
 * change (PATCH /auth/settings) does not touch that cookie, so the header kept
 * showing the old name until the user logged out and back in (#467).
 *
 * `updateSessionName()` rewrites the name in whichever local session cookie is
 * present, preserving the email. Pair it with `router.refresh()` so the server
 * layout re-reads the cookie and the header updates immediately.
 *
 * Note: this only covers the local (school-provisioned) and demo session
 * cookies. Auth0 sessions are server-managed (httpOnly) and still require a
 * re-login to reflect a name change.
 */

// Local-auth + demo session cookies that carry { name, email }. Keep in sync
// with persistSession in (public)/signin/page.tsx and lib/dev-session.ts.
const NAME_BEARING_SESSION_COOKIES = [
  "sb_local_student_session",
  "sb_dev_session",
] as const;

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return match ? match.slice(name.length + 1) : null;
}

/**
 * Update the `name` field in any present local/demo session cookie, keeping the
 * existing email and cookie attributes. No-op on the server or when no such
 * cookie exists. Malformed cookies are left untouched.
 */
export function updateSessionName(name: string): void {
  if (typeof document === "undefined") return;
  const secure = location.protocol === "https:" ? "; Secure" : "";

  for (const cookieName of NAME_BEARING_SESSION_COOKIES) {
    const raw = readCookie(cookieName);
    if (!raw) continue;
    try {
      const data = JSON.parse(atob(raw)) as { name?: string; email?: string };
      const payload = btoa(JSON.stringify({ name, email: data.email ?? "" }));
      document.cookie = `${cookieName}=${payload}; path=/; SameSite=Strict; Max-Age=86400${secure}`;
    } catch {
      // Leave a malformed cookie alone rather than clobbering the session.
    }
  }
}
