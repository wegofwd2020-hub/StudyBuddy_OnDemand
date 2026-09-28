/**
 * GET /build-id — which commit this web bundle was built from (#583).
 *
 * A green deploy used to prove only that commands exited 0; on 2026-08-14 the
 * box served a nine-day-old web image while the workflow reported success. The
 * deploy now asserts this value against the SHA it just built, so "did it ship?"
 * is a question CI can answer without anyone SSHing in.
 *
 * Build ID is written to .next/public/build-id.json during Docker build and
 * served as a static file. This returns it as JSON for CI verification.
 */
export async function GET() {
  try {
    const { readFile } = await import("fs/promises");
    const path = await import("path");
    const filePath = path.join(process.cwd(), ".next/public/build-id.json");
    const content = await readFile(filePath, "utf-8");
    const data = JSON.parse(content);
    return Response.json({ build_id: data.build_id ?? "dev" });
  } catch {
    return Response.json({ build_id: "dev" });
  }
}
