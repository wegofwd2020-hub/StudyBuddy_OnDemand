import { redirect } from "next/navigation";

/**
 * /demo/login is folded into the unified /signin page.
 *
 * Demo credential emails sent before the cutover (see backend/src/email/service.py)
 * link here; keep this redirect alive at least until the demo TTL of any
 * already-issued credentials has lapsed (24h for students, 48h for teachers).
 */
export default function DemoLoginRedirect() {
  redirect("/signin");
}
