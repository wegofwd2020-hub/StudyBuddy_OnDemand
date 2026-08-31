/**
 * The warm public palette must not cost us WCAG AA.
 *
 * app/globals.css remaps gray/slate to a warm scale inside .sb-warm-neutrals
 * (docs/DESIGN_kolibri_site_teardown.md "What to take" #4). Warmth is a taste
 * call; contrast is not — WCAG 2.1 AA is a project requirement (4.5:1 for normal
 * text, 3:1 for large). A future palette tweak is exactly the kind of change that
 * looks harmless and quietly drops body copy below AA, so the ratios are pinned
 * here rather than left in a comment.
 *
 * This parses the real CSS rather than restating the values, so editing the
 * palette without editing this file is what triggers the failure.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const CSS = readFileSync(join(process.cwd(), "app/globals.css"), "utf8");

/** The scoped override block. */
function warmBlock(): string {
  const start = CSS.indexOf(".sb-warm-neutrals {");
  expect(start, ".sb-warm-neutrals block missing from globals.css").toBeGreaterThan(-1);
  return CSS.slice(start, CSS.indexOf("\n}", start));
}

/** oklch(L% C H) -> linear-light sRGB triple. */
function oklchToRgb(L: number, C: number, hDeg: number): [number, number, number] {
  const h = (hDeg * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const lin: [number, number, number] = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
  // clamp into gamut, then to gamma-encoded sRGB and back to linear for luminance
  return lin.map((v) => Math.max(0, Math.min(1, v))) as [number, number, number];
}

function relativeLuminance([r, g, b]: [number, number, number]): number {
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: [number, number, number], b: [number, number, number]): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/** Pull a shade out of the warm block, e.g. shade("gray", "500"). */
function shade(family: "gray" | "slate", n: string): [number, number, number] {
  const re = new RegExp(
    `--color-${family}-${n}:\\s*oklch\\(([\\d.]+)%\\s+([\\d.]+)\\s+([\\d.]+)\\)`,
  );
  const m = warmBlock().match(re);
  expect(m, `--color-${family}-${n} not found in .sb-warm-neutrals`).not.toBeNull();
  return oklchToRgb(Number(m![1]) / 100, Number(m![2]), Number(m![3]));
}

const WHITE: [number, number, number] = [1, 1, 1];
const AA_NORMAL = 4.5;

describe("warm public neutrals keep WCAG AA", () => {
  // Body-copy shades, on white and on the bg-*-50 section ground. 500 is the
  // tightest and the most used (~104 occurrences on public pages), so it is the
  // one that actually decides whether this palette is shippable.
  // 400 is included since #189: it used to be the one text shade that failed,
  // at 2.59 on white against a 4.5 requirement -- and it is used 343 times as a
  // text colour, so it was never a legal level, just a legal-LOOKING one.
  it.each(["400", "500", "600", "700", "800", "900"])(
    "gray-%s clears AA on white and on the -50 ground",
    (n) => {
      expect(contrast(shade("gray", n), WHITE)).toBeGreaterThanOrEqual(AA_NORMAL);
      expect(contrast(shade("gray", n), shade("gray", "50"))).toBeGreaterThanOrEqual(
        AA_NORMAL,
      );
    },
  );

  it("slate body shades clear AA too", () => {
    for (const n of ["400", "500", "600", "700", "800", "900"]) {
      expect(contrast(shade("slate", n), WHITE)).toBeGreaterThanOrEqual(AA_NORMAL);
    }
  });

  it("does not regress the cool palette it replaced", () => {
    // The whole claim of this change is "warmer, same legibility". Cool gray-500
    // measured 4.84 on white and 4.63 on gray-50; allow a small tolerance but
    // refuse a real drop, which is how a warm palette usually goes wrong.
    expect(contrast(shade("gray", "500"), WHITE)).toBeGreaterThan(4.7);
    expect(contrast(shade("gray", "500"), shade("gray", "50"))).toBeGreaterThan(4.5);
  });

  it("still reads as warm, not cool", () => {
    // Hue is the point of the exercise. Tailwind's stock gray sits at 257-265deg
    // (blue); a warm neutral belongs roughly in 20-110deg. If someone reverts the
    // values to a cool scale this fails loudly instead of silently undoing item #4.
    const block = warmBlock();
    const hues = [
      ...block.matchAll(/--color-gray-\d+:\s*oklch\([\d.]+%\s+[\d.]+\s+([\d.]+)\)/g),
    ].map((m) => Number(m[1]));
    expect(hues.length).toBeGreaterThanOrEqual(10);
    for (const h of hues) {
      expect(h, `hue ${h}deg is not warm`).toBeGreaterThan(15);
      expect(h, `hue ${h}deg is not warm`).toBeLessThan(120);
    }
  });

  it("remaps slate as well, so public pages carry one neutral family", () => {
    // 42 slate utilities survive on public pages. Leaving them cool would mean a
    // page mixing a warm neutral with a blue one, which is more visible than
    // either alone.
    expect(warmBlock()).toMatch(/--color-slate-500:/);
    const g = shade("gray", "600");
    const s = shade("slate", "600");
    expect(Math.abs(contrast(g, WHITE) - contrast(s, WHITE))).toBeLessThan(0.01);
  });
});

describe("the override stays scoped", () => {
  it("is applied by the public layout", () => {
    const layout = readFileSync(join(process.cwd(), "app/(public)/layout.tsx"), "utf8");
    expect(layout).toContain("sb-warm-neutrals");
  });

  it("is applied to the school portal via its theme provider", () => {
    // Not in app/(school)/layout.tsx: that layout returns from two branches
    // (local-auth and Auth0) and both wrap in SchoolPortalThemeProvider, so one
    // wrapper there cannot drift out of sync the way two copies would.
    const ctx = readFileSync(
      join(process.cwd(), "lib/theme/SchoolThemeContext.tsx"),
      "utf8",
    );
    const school = ctx.slice(
      ctx.indexOf("export function SchoolPortalThemeProvider"),
      ctx.indexOf("export function StudentPortalThemeProvider"),
    );
    expect(school).toContain("sb-warm-neutrals");
  });

  it("is applied to the student portal via its theme provider", () => {
    // Warmed after the school portal. The same file holds three uses of the same
    // context, so each provider is asserted BY NAME rather than by counting
    // occurrences -- wrapping the wrong one produces an identical-looking diff.
    const ctx = readFileSync(
      join(process.cwd(), "lib/theme/SchoolThemeContext.tsx"),
      "utf8",
    );
    const student = ctx.slice(ctx.indexOf("export function StudentPortalThemeProvider"));
    expect(student).toContain("sb-warm-neutrals");
  });

  it("is NOT applied to the admin console", () => {
    // The one remaining exclusion, and now the whole rule: every CUSTOMER-FACING
    // surface is warm; the internal operations console is not. If admin is ever
    // warmed too, this stops being a scope and the block belongs on :root.
    const layout = readFileSync(join(process.cwd(), "app/(admin)/layout.tsx"), "utf8");
    expect(layout).not.toContain("sb-warm-neutrals");
  });

  it("uses display:contents so it adds no layout box", () => {
    // <body> is `flex min-h-full flex-col` and <main> relies on flex-1. A wrapper
    // with a real box would break the sticky footer.
    expect(warmBlock()).toMatch(/display:\s*contents/);
  });

  it("does not leak into the portals", () => {
    // A bare `:root`/`body`/`*` override would re-tint the ~2,826 neutral
    // utilities in (admin)/(school)/(student) as a side effect.
    const start = CSS.indexOf(".sb-warm-neutrals {");
    const before = CSS.slice(0, start);
    expect(before).not.toMatch(/--color-gray-500:/);
  });
});

describe("no customer-facing page keeps a sub-AA text colour we already fixed", () => {
  it("text-blue-100 is gone from the blue CTA sections (#189)", () => {
    // 4.31 on bg-blue-600, against 4.5 for normal text. It passed only where the
    // text happened to be large. blue-50 scores 4.82 and keeps the tint, where
    // plain white (5.26) would read harsher than the design intends.
    //
    // One of the eight sites was a line added earlier in this same session --
    // which is the argument for asserting it rather than remembering it.
    const roots = ["app/(public)", "app/(school)", "app/(student)", "components"];
    const offenders: string[] = [];
    for (const root of roots) {
      for (const file of walk(join(process.cwd(), root))) {
        if (readFileSync(file, "utf8").includes("text-blue-100")) {
          offenders.push(file.replace(process.cwd() + "/", ""));
        }
      }
    }
    expect(offenders).toEqual([]);
  });
});

/** Every .tsx under a directory. */
function walk(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full));
    else if (entry.name.endsWith(".tsx")) out.push(full);
  }
  return out;
}

describe("the 400 level is legal outside the warm scope too (#189)", () => {
  it("globals.css remaps gray-400/slate-400 at the theme level", () => {
    // The warm scope covers the customer-facing surfaces. The admin console is
    // deliberately NOT warm, and #189 names its Dashboard and Content Review --
    // so the AA fix has to sit ABOVE the scope or admin keeps the 2.59 shade.
    // Anchor on the RULE, not the name: the explanatory comment above the
    // @theme block mentions .sb-warm-neutrals too, and slicing at the first
    // mention cuts before the declarations this is asserting.
    const theme = CSS.slice(0, CSS.indexOf(".sb-warm-neutrals {"));
    expect(theme, "gray-400 must be remapped outside the warm scope").toMatch(
      /--color-gray-400:\s*oklch\(55\.1%/,
    );
    expect(theme).toMatch(/--color-slate-400:\s*oklch\(55\.1%/);
  });

  it("the warm scope still re-tints 400, so the portals stay warm", () => {
    expect(warmBlock()).toMatch(/--color-gray-400:\s*oklch\(55\.3%/);
  });
});
