/**
 * GET /build-id — which commit this web bundle was built from (#583).
 *
 * A green deploy used to prove only that commands exited 0; on 2026-08-14 the
 * box served a nine-day-old web image while the workflow reported success. The
 * deploy now asserts this value against the SHA it just built, so "did it ship?"
 * is a question CI can answer without anyone SSHing in.
 *
 * Build ID is baked into a JSON file during Docker build, not read from env
 * at runtime — a runtime lookup would report the deployed config rather than
 * the built code, which is the very thing that went stale.
 */
import buildId from "./build-id.json";

export const dynamic = "force-static";

export function GET() {
  return Response.json({ build_id: buildId.id ?? "dev" });
}
