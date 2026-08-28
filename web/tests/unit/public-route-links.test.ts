/**
 * tests/unit/public-route-links.test.ts
 *
 * Every internal link on a public page must resolve to a real route (#663).
 *
 * The sign-in page linked to `/demo` for months. `app/(public)/demo/` held only
 * subroutes — `login`, `verify/[token]`, the story pages — and no `page.tsx` of
 * its own, so the link 404'd on the page in front of every prospective school.
 * Nothing caught it: the link is valid TypeScript, the target is a plausible
 * path, and no test renders a public page and follows its hrefs.
 *
 * This walks the App Router tree, builds the set of routes that actually exist,
 * then checks every literal internal href in the public pages against it. It is
 * deliberately limited to LITERAL hrefs — a template string is skipped rather
 * than guessed at, because a false failure here would train people to ignore
 * the test.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

import { describe, expect, it } from "vitest";

const APP_DIR = join(__dirname, "..", "..", "app");

/** Directories App Router treats as grouping only — they add no URL segment. */
function isGroupSegment(name: string): boolean {
  return name.startsWith("(") && name.endsWith(")");
}

/** A dynamic segment: [id], [...slug], [[...slug]]. */
function isDynamicSegment(name: string): boolean {
  return name.startsWith("[");
}

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (entry === "node_modules" || entry.startsWith(".")) continue;
      walk(full, out);
    } else if (entry === "page.tsx" || entry === "route.ts") {
      out.push(full);
    }
  }
  return out;
}

/** URL path for a page file, or null when it sits under a dynamic segment. */
function routeForPageFile(file: string): { path: string; dynamic: boolean } {
  const rel = relative(APP_DIR, file);
  const parts = rel.split(sep).slice(0, -1); // drop page.tsx
  const segments = parts.filter((p) => !isGroupSegment(p));
  const dynamic = segments.some(isDynamicSegment);
  return { path: "/" + segments.join("/"), dynamic };
}

const pageFiles = walk(APP_DIR);
const routes = pageFiles.map(routeForPageFile);
const staticRoutes = new Set(routes.filter((r) => !r.dynamic).map((r) => r.path));
// Prefixes that have a dynamic child, e.g. /demo/verify for /demo/verify/[token].
const dynamicPrefixes = routes
  .filter((r) => r.dynamic)
  .map((r) => r.path.slice(0, r.path.indexOf("/[")));

/** Public pages are the ones an unauthenticated visitor can reach. */
const publicPages = pageFiles.filter((f) => f.includes(`${sep}(public)${sep}`));

const HREF_RE = /href=["'](\/[^"'{}\s]*)["']/g;

function internalHrefs(file: string): string[] {
  const src = readFileSync(file, "utf8");
  const found = new Set<string>();
  for (const m of src.matchAll(HREF_RE)) {
    // Strip query and hash — routing only cares about the path.
    const path = m[1].split("?")[0].split("#")[0];
    if (path) found.add(path);
  }
  return [...found];
}

/**
 * Paths served by the backend through nginx, not by the App Router.
 *
 * `/auth/login` is the Auth0 redirect handler. It is a real destination, so it
 * does not belong in this test's "route does not exist" bucket — but note it
 * currently returns 500 on the demo (#585), which this test deliberately does
 * NOT assert on: its job is whether a route exists, not whether it is healthy.
 */
const PROXIED_PREFIXES = ["/auth/", "/api/"];

function resolves(path: string): boolean {
  if (PROXIED_PREFIXES.some((p) => path.startsWith(p))) return true;
  const clean = path.length > 1 && path.endsWith("/") ? path.slice(0, -1) : path;
  if (staticRoutes.has(clean)) return true;
  // A dynamic route covers its prefix: /demo/verify/abc matches /demo/verify/[token].
  return dynamicPrefixes.some((p) => p !== "" && clean.startsWith(p + "/"));
}

describe("public pages link only to routes that exist (#663)", () => {
  it("finds the app router tree", () => {
    // Guards the test itself: a broken walk would make every case vacuously pass.
    expect(pageFiles.length).toBeGreaterThan(20);
    expect(publicPages.length).toBeGreaterThan(5);
    expect(staticRoutes.has("/signin")).toBe(true);
  });

  it("has a page at /demo, the link the sign-in page has always carried", () => {
    // The specific regression: subroutes existed, the parent route did not.
    expect(staticRoutes.has("/demo")).toBe(true);
  });

  it.each(publicPages.map((f) => [relative(APP_DIR, f), f] as const))(
    "%s",
    (_label, file) => {
      const broken = internalHrefs(file).filter((h) => !resolves(h));
      expect(broken, `dead internal links in ${relative(APP_DIR, file)}`).toEqual([]);
    },
  );
});
