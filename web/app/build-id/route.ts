/**
 * GET /build-id — which commit this web bundle was built from (#583).
 *
 * A green deploy used to prove only that commands exited 0; on 2026-08-14 the
 * box served a nine-day-old web image while the workflow reported success. The
 * deploy now asserts this value against the SHA it just built, so "did it ship?"
 * is a question CI can answer without anyone SSHing in.
 *
 * Build ID is written to .next/public/build-id.json during Docker build.
 * This route reads and returns that static file.
 */
export const dynamic = "force-static";

export async function GET() {
  try {
    const data = await import("../../public/build-id.json");
    return Response.json({ build_id: data.build_id ?? "dev" });
  } catch {
    return Response.json({ build_id: "dev" });
  }
}
