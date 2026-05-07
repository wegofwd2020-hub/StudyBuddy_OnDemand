#!/usr/bin/env bun
/**
 * Asset migration for issue #318 — copy the legacy exemplar binaries from
 * web/public/sample-visuals/<UNIT>/ to content_store_data/visuals/_legacy/<UNIT>/
 * and update the tutorial_en.json URL strings from
 *   /sample-visuals/<UNIT>/<file>
 * to
 *   /visuals/_legacy/<UNIT>/<file>
 *
 * After this runs:
 *   - Backend serves /visuals/* via the StaticFiles mount (app_factory.py).
 *   - Next.js proxies /visuals/* to the backend (next.config.ts).
 *   - The browser request /visuals/_legacy/G11-MATH-001/union.svg resolves
 *     to content_store_data/visuals/_legacy/G11-MATH-001/union.svg.
 *
 * Run from repo root:
 *   bun scripts/migrate_legacy_visuals_to_storage.ts
 *
 * Idempotent: re-running is safe — files already in the destination are not
 * re-copied; tutorial JSON URLs already in the new shape are left alone.
 */

import { readdirSync, readFileSync, writeFileSync, mkdirSync, copyFileSync, existsSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..");
const SOURCE_BASE = join(ROOT, "web", "public", "sample-visuals");
const DEST_BASE = join(ROOT, "content_store_data", "visuals", "_legacy");

const UNITS = ["G11-MATH-001", "G11-PHYS-002"];
const CURRICULA = ["default-2026-g11-science"];

// Step 1: copy binaries
let copied = 0;
let skipped = 0;
for (const unit of UNITS) {
  const src = join(SOURCE_BASE, unit);
  if (!existsSync(src)) {
    console.log(`  (no source for ${unit})`);
    continue;
  }
  const dst = join(DEST_BASE, unit);
  mkdirSync(dst, { recursive: true });
  for (const f of readdirSync(src)) {
    const sp = join(src, f);
    const dp = join(dst, f);
    if (!statSync(sp).isFile()) continue;
    if (existsSync(dp) && statSync(dp).size === statSync(sp).size) {
      skipped++;
      continue;
    }
    copyFileSync(sp, dp);
    copied++;
  }
}
console.log(`copy: ${copied} new, ${skipped} already present`);

// Step 2: rewrite tutorial_en.json URLs
let rewritten = 0;
for (const curriculum of CURRICULA) {
  for (const unit of UNITS) {
    const path = join(
      ROOT,
      "content_store_data",
      "curricula",
      curriculum,
      unit,
      "tutorial_en.json",
    );
    if (!existsSync(path)) continue;
    const text = readFileSync(path, "utf-8");
    const replaced = text.replace(
      /\/sample-visuals\/([^"\\]+)/g,
      "/visuals/_legacy/$1",
    );
    if (replaced !== text) {
      writeFileSync(path, replaced);
      rewritten++;
      console.log(`  rewrote URLs in ${curriculum}/${unit}/tutorial_en.json`);
    }
  }
}
console.log(`rewrite: ${rewritten} tutorial JSON file(s) updated`);

// Step 3: verification scan — confirm no /sample-visuals/ URLs remain
let remaining = 0;
for (const curriculum of CURRICULA) {
  for (const unit of UNITS) {
    const path = join(
      ROOT,
      "content_store_data",
      "curricula",
      curriculum,
      unit,
      "tutorial_en.json",
    );
    if (!existsSync(path)) continue;
    const text = readFileSync(path, "utf-8");
    const matches = text.match(/\/sample-visuals\/[^"\\]+/g);
    if (matches) remaining += matches.length;
  }
}
if (remaining > 0) {
  console.error(`⚠  ${remaining} legacy /sample-visuals/* URL(s) still in tutorial JSON`);
  process.exit(1);
}
console.log("ok — no legacy URLs remain in tutorial JSON");
