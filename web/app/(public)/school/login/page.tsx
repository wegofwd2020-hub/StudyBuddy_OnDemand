import { redirect } from "next/navigation";

/**
 * /school/login is folded into the unified /signin page.
 *
 * Kept as a redirect so any external link (bookmarks, in-flight invitation
 * emails) continues to work. Safe to delete once those references have aged
 * out — but the redirect is cheap, so it can stay indefinitely.
 */
export default function SchoolLoginRedirect() {
  redirect("/signin");
}
