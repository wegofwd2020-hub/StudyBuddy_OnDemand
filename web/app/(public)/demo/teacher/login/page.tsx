import { redirect } from "next/navigation";

/**
 * /demo/teacher/login is folded into the unified /signin page.
 *
 * Demo credential emails sent before the cutover link here; keep this redirect
 * alive at least until the 48h teacher demo TTL has lapsed.
 */
export default function DemoTeacherLoginRedirect() {
  redirect("/signin");
}
