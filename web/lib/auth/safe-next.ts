/**
 * Where to send a user after sign-in when a page asked them to come back (#764).
 *
 * The enrolment invite link sends a signed-out student to
 * `/signin?next=/enrol/<code>`. Without honouring `next`, sign-in always went to
 * `/dashboard`, the link was forgotten and the student was never enrolled.
 *
 * `next` comes from the URL, so it is untrusted: accept only an absolute path on
 * this site. Rejected: protocol-relative `//host`, the `/\host` variant browsers
 * normalise to it, any scheme (`https:`, `javascript:`), and relative paths.
 */
export function safeNextPath(raw: string | null | undefined): string | null {
  if (!raw) return null;
  if (!raw.startsWith("/")) return null;
  if (raw.startsWith("//") || raw.startsWith("/\\")) return null;
  return raw;
}

/** A student's destination after a successful, non-first-login sign-in. */
export function studentSignInDestination(next: string | null | undefined): string {
  return safeNextPath(next) ?? "/dashboard";
}
