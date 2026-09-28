/**
 * GET /build-id — which commit this web bundle was built from (#583).
 *
 * A green deploy used to prove only that commands exited 0; on 2026-08-14 the
 * box served a nine-day-old web image while the workflow reported success. The
 * deploy now asserts this value against the SHA it just built, so "did it ship?"
 * is a question CI can answer without anyone SSHing in.
 *
 * Baked at build time via NEXT_PUBLIC_BUILD_ID env var. Since route has
 * force-static, process.env is captured at build time, not read at runtime.
 */
export const dynamic = "force-static";

export function GET() {
  return Response.json({ build_id: process.env.NEXT_PUBLIC_BUILD_ID ?? "dev" });
}
