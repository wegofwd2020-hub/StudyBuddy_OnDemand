/**
 * Every URL the web client calls must exist in the API.
 *
 * Four contract mismatches have shipped past CI this way:
 *   #524  "Submit answer" posted to a path the API didn't serve — dead button
 *   #600  the lesson thumbs widget posted to `/feedback/submit` — 404, and the
 *         feedback table stayed empty for the life of the deployment
 *   #600  the admin feedback list read `{items,...}` from an API returning
 *         `{feedback_items,...}` — a page that could never render
 *   #603  the admin "resolve" button posts to an endpoint that does not exist
 *
 * None were caught, because frontend tests mock the HTTP client and backend
 * tests call the router directly — so no test ever exercised the *pair*. This
 * closes that gap by checking the paths in `lib/api/` against the committed
 * OpenAPI schema, which is generated from FastAPI itself.
 *
 * It cannot verify request/response *shapes* — `types.gen.ts` and the API
 * Contract CI job cover that. This is specifically about existence: does the
 * thing we call exist, with the method we use.
 */

import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const API_DIR = join(__dirname, "../../lib/api");
const OPENAPI = join(__dirname, "../../openapi.json");

/**
 * Known-broken call sites, each with the issue tracking the fix. A non-empty
 * allowlist is deliberate: these are real defects this check found, listed
 * here so the check can be enforcing today rather than after every one is
 * fixed. Remove an entry when its issue closes — do NOT add one to silence a
 * new failure.
 */
const KNOWN_BROKEN = new Map<string, string>([
  // Found by this check on first run; all 404 against a live API. Six are wired
  // into UI (see #604) — the admin Audit page and the dashboard's subscription
  // analytics among them. Listed so the check can enforce from day one.
  [
    "GET /api/v1/subscription/status",
    "#604 — student subscriptions dropped in migration 0027",
  ],
  [
    "POST /api/v1/subscription/checkout",
    "#604 — student subscriptions dropped in migration 0027",
  ],
  ["GET /api/v1/subscription/billing-portal", "#604 — dropped in migration 0027"],
  ["POST /api/v1/subscription/cancel", "#604 — dropped in migration 0027"],
  [
    "GET /api/v1/admin/private-teachers",
    "#604 — private teachers dropped in migration 0026",
  ],
  ["POST /api/v1/auth/consent", "#604 — never implemented"],
  ["POST /api/v1/school/enrol/confirm", "#604 — never implemented"],
]);

/**
 * Paths deliberately absent from the schema. The health probes are registered
 * with `include_in_schema=False` (see src/core/observability.py), so their
 * absence is intentional and not drift.
 */
const NOT_IN_SCHEMA_BY_DESIGN = [/^\/api\/v1\/health(z)?$/, /^\/api\/v1\/readyz$/];

/** Methods worth checking; `request`/`head` etc. are not used in this codebase. */
const METHODS = ["get", "post", "put", "patch", "delete"] as const;

interface CallSite {
  method: string;
  path: string;
  file: string;
}

/** `${anything}` and OpenAPI's `{param}` both collapse to `{}` so they compare. */
function normalise(path: string): string {
  return (
    path
      // A nested template (`` `/admin/streams${qs ? `?${qs}` : ""}` ``) truncates
      // at the inner backtick, leaving an unterminated `${`. Cut from there.
      .replace(/\$\{[^}]*$/, "")
      // A trailing interpolation not preceded by "/" is an appended query
      // string (`/admin/streams${qs}`), not a path segment — drop it.
      .replace(/(?<!\/)\$\{[^}]*\}$/, "")
      .replace(/\$\{[^}]*\}/g, "{}")
      .replace(/\{[^}]*\}/g, "{}")
      .replace(/\?.*$/, "")
      .replace(/\/+$/, "")
  );
}

/** Resolve same-file `const NAME = "/literal"` so `${BASE}/x` becomes `/literal/x`. */
function resolveLocalConstants(source: string, path: string): string {
  return path.replace(/\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (whole, name: string) => {
    const decl = new RegExp(`const\\s+${name}\\s*=\\s*["'\`]([^"'\`]+)["'\`]`).exec(
      source,
    );
    return decl ? decl[1] : whole;
  });
}

function collectCallSites(): CallSite[] {
  const files = readdirSync(API_DIR).filter((f) => f.endsWith(".ts"));
  const sites: CallSite[] = [];

  for (const file of files) {
    const source = readFileSync(join(API_DIR, file), "utf8");
    // client.method<Generic>("path" | `path`
    const call = new RegExp(
      `\\b\\w*[aA]pi\\.(${METHODS.join("|")})\\s*(?:<[^>(]*>)?\\s*\\(\\s*(["'\`])([^"'\`]+)\\2`,
      "g",
    );
    let m: RegExpExecArray | null;
    while ((m = call.exec(source)) !== null) {
      const [, method, , rawPath] = m;
      const resolved = resolveLocalConstants(source, rawPath);
      // Only absolute API paths — skip anything still fully dynamic.
      if (!resolved.startsWith("/")) continue;
      const withPrefix = resolved.startsWith("/api/v1") ? resolved : `/api/v1${resolved}`;
      sites.push({ method: method.toUpperCase(), path: normalise(withPrefix), file });
    }
  }
  return sites;
}

function collectSchemaRoutes(): Set<string> {
  const schema = JSON.parse(readFileSync(OPENAPI, "utf8")) as {
    paths: Record<string, Record<string, unknown>>;
  };
  const routes = new Set<string>();
  for (const [path, ops] of Object.entries(schema.paths ?? {})) {
    for (const method of Object.keys(ops)) {
      routes.add(`${method.toUpperCase()} ${normalise(path)}`);
    }
  }
  return routes;
}

describe("API contract — every client path exists in the schema", () => {
  const sites = collectCallSites();
  const routes = collectSchemaRoutes();

  it("finds call sites to check (guards against the extractor silently matching nothing)", () => {
    expect(sites.length).toBeGreaterThan(50);
    expect(routes.size).toBeGreaterThan(50);
  });

  it("every path the client calls is served by the API", () => {
    const missing = sites
      .map((s) => ({ ...s, key: `${s.method} ${s.path}` }))
      .filter((s) => !routes.has(s.key))
      .filter((s) => !KNOWN_BROKEN.has(s.key))
      .filter((s) => !NOT_IN_SCHEMA_BY_DESIGN.some((re) => re.test(s.path)));

    const report = missing.map((s) => `  ${s.key}   (${s.file})`).join("\n");
    expect(missing, `Client calls endpoints the API does not serve:\n${report}`).toEqual(
      [],
    );
  });

  it("the known-broken list has no stale entries", () => {
    const stale = [...KNOWN_BROKEN.keys()].filter((key) => routes.has(key));
    expect(
      stale,
      `These are fixed — remove them from KNOWN_BROKEN:\n${stale.join("\n")}`,
    ).toEqual([]);
  });
});
