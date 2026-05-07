#!/usr/bin/env bun
/**
 * Validate visual-library sidecar `*.metadata.yaml` files.
 *
 * Spec: docs/VISUAL_LIBRARY_SIDECAR.md
 * Issue: #322 (Visual library — promotion CI + sidecar contract).
 *
 * Usage:
 *   bun scripts/validate_library_metadata.ts <glob-or-path>...
 *
 * Examples:
 *   bun scripts/validate_library_metadata.ts \
 *     sample_content/**\/Option2_Catalogue/**\/*.metadata.yaml
 *
 *   bun scripts/validate_library_metadata.ts \
 *     sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-4-projectile/trajectory.metadata.yaml
 *
 * Exit codes:
 *   0  all sidecars valid
 *   1  one or more validation errors
 *   2  bad invocation (no inputs, glob mismatch, etc.)
 *
 * Output: one error per violation, each line:
 *   <path>: <field>: <human-readable problem>
 */

import { readFileSync, existsSync, statSync } from "node:fs";
import { dirname, basename, extname, resolve } from "node:path";
import { Glob } from "bun";

// ── Closed enums (mirrored in backend/src/visuals/library.py::SUBJECTS) ─────

const SCHEMA_VERSION = 1;

const KINDS = ["image", "image-grid", "animated-svg", "video"] as const;
type Kind = (typeof KINDS)[number];

const SUBJECTS = [
  "physics",
  "chemistry",
  "math",
  "biology",
  "geography",
  "history",
  "languages",
] as const;

const LICENSES = ["platform-cc-by-sa", "platform-proprietary"] as const;

// kind → allowed asset file extensions (lowercase, with leading dot)
const EXT_BY_KIND: Record<Kind, string[]> = {
  "image": [".svg", ".png", ".jpg", ".jpeg", ".webp"],
  "image-grid": [".svg", ".png", ".jpg", ".jpeg", ".webp"],
  "animated-svg": [".svg"],
  "video": [".mp4", ".webm"],
};

const ID_RE = /^[a-z0-9-]+$/;
const KEYWORD_RE = /^[a-z0-9-]+$/;
const MAX_ID_LEN = 80;
const MAX_TOPIC_LEN = 200;

// ── Minimal YAML parser (avoid adding a dep for this slice) ─────────────────
//
// Sidecars are flat dicts with scalar + sequence values. This handles the
// subset we need: top-level "key: value" lines, quoted strings, and
// "key:\n  - item" sequences. If sidecars grow more complex we'll swap to
// a real YAML parser (js-yaml).

type YamlValue = string | number | boolean | YamlValue[] | { [k: string]: YamlValue };

function parseSimpleYaml(text: string): { [k: string]: YamlValue } {
  const out: { [k: string]: YamlValue } = {};
  const lines = text.split(/\r?\n/);
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      i++;
      continue;
    }
    const colon = line.indexOf(":");
    if (colon === -1) throw new Error(`Bad line ${i + 1}: ${line}`);
    const key = line.slice(0, colon).trim();
    const after = line.slice(colon + 1).trim();
    if (after === "" || after.startsWith("#")) {
      // Sequence on following indented lines
      const items: YamlValue[] = [];
      i++;
      while (i < lines.length) {
        const sub = lines[i];
        if (/^\s*-\s/.test(sub)) {
          const v = sub.replace(/^\s*-\s*/, "").trim();
          items.push(parseScalar(v));
          i++;
        } else if (sub.trim() === "" || sub.trim().startsWith("#")) {
          i++;
        } else {
          break;
        }
      }
      out[key] = items;
    } else {
      out[key] = parseScalar(after.replace(/\s*#.*$/, "").trim());
      i++;
    }
  }
  return out;
}

function parseScalar(raw: string): YamlValue {
  if (raw === "true") return true;
  if (raw === "false") return false;
  if (/^-?\d+$/.test(raw)) return Number.parseInt(raw, 10);
  if (/^-?\d+\.\d+$/.test(raw)) return Number.parseFloat(raw);
  // Strip matching quotes
  if ((raw.startsWith('"') && raw.endsWith('"')) || (raw.startsWith("'") && raw.endsWith("'"))) {
    return raw.slice(1, -1);
  }
  return raw;
}

// ── Validation ───────────────────────────────────────────────────────────────

interface Sidecar {
  schema_version?: unknown;
  id?: unknown;
  kind?: unknown;
  subject?: unknown;
  topic_phrase?: unknown;
  keywords?: unknown;
  license?: unknown;
  source_unit?: unknown;
}

interface ValidationError {
  path: string;
  field: string;
  message: string;
}

function validate(path: string, doc: Sidecar): ValidationError[] {
  const errors: ValidationError[] = [];
  const err = (field: string, message: string) =>
    errors.push({ path, field, message });

  // schema_version
  if (doc.schema_version !== SCHEMA_VERSION) {
    err("schema_version", `must be ${SCHEMA_VERSION}, got ${JSON.stringify(doc.schema_version)}`);
  }

  // id
  if (typeof doc.id !== "string") {
    err("id", "must be a string");
  } else if (!ID_RE.test(doc.id)) {
    err("id", `must match /^[a-z0-9-]+$/, got ${JSON.stringify(doc.id)}`);
  } else if (doc.id.length > MAX_ID_LEN) {
    err("id", `max ${MAX_ID_LEN} chars, got ${doc.id.length}`);
  }

  // kind
  if (typeof doc.kind !== "string" || !(KINDS as readonly string[]).includes(doc.kind)) {
    err("kind", `must be one of ${JSON.stringify(KINDS)}, got ${JSON.stringify(doc.kind)}`);
  }

  // subject
  if (typeof doc.subject !== "string" || !(SUBJECTS as readonly string[]).includes(doc.subject)) {
    err("subject", `must be one of ${JSON.stringify(SUBJECTS)}, got ${JSON.stringify(doc.subject)}`);
  }

  // topic_phrase
  if (typeof doc.topic_phrase !== "string" || doc.topic_phrase.trim() === "") {
    err("topic_phrase", "must be a non-empty string");
  } else if (doc.topic_phrase.length > MAX_TOPIC_LEN) {
    err("topic_phrase", `max ${MAX_TOPIC_LEN} chars, got ${doc.topic_phrase.length}`);
  }

  // keywords
  if (!Array.isArray(doc.keywords) || doc.keywords.length === 0) {
    err("keywords", "must be a non-empty list");
  } else {
    for (const [i, kw] of doc.keywords.entries()) {
      if (typeof kw !== "string") {
        err(`keywords[${i}]`, "must be a string");
      } else if (!KEYWORD_RE.test(kw)) {
        err(`keywords[${i}]`, `must match /^[a-z0-9-]+$/, got ${JSON.stringify(kw)}`);
      }
    }
  }

  // license
  if (typeof doc.license !== "string" || !(LICENSES as readonly string[]).includes(doc.license)) {
    err("license", `must be one of ${JSON.stringify(LICENSES)}, got ${JSON.stringify(doc.license)}`);
  }

  // source_unit (optional)
  if (doc.source_unit !== undefined && typeof doc.source_unit !== "string") {
    err("source_unit", "must be a string if present");
  }

  // Filesystem rules — sibling asset file with extension matching kind
  if (typeof doc.kind === "string" && (KINDS as readonly string[]).includes(doc.kind)) {
    const sidecarBase = basename(path); // e.g. "trajectory.metadata.yaml"
    const assetBase = sidecarBase.replace(/\.metadata\.ya?ml$/, "");
    const dir = dirname(path);
    const allowedExts = EXT_BY_KIND[doc.kind as Kind];

    // Find a sibling whose stem matches assetBase and whose ext is in allowedExts
    const candidates = allowedExts
      .map((ext) => resolve(dir, `${assetBase}${ext}`))
      .filter((p) => existsSync(p) && statSync(p).isFile());

    if (candidates.length === 0) {
      err(
        "asset",
        `no sibling asset found for stem ${JSON.stringify(assetBase)} with extension in ${JSON.stringify(allowedExts)}`,
      );
    } else if (candidates.length > 1) {
      err(
        "asset",
        `multiple sibling assets match ${JSON.stringify(assetBase)}: ${candidates.map((p) => extname(p)).join(", ")} — only one expected`,
      );
    }
  }

  return errors;
}

// ── Glob resolution ──────────────────────────────────────────────────────────

async function resolveInputs(args: string[]): Promise<string[]> {
  const out = new Set<string>();
  for (const arg of args) {
    if (arg.includes("*") || arg.includes("?")) {
      const glob = new Glob(arg);
      for await (const f of glob.scan({ cwd: process.cwd(), onlyFiles: true })) {
        out.add(resolve(process.cwd(), f));
      }
    } else if (existsSync(arg)) {
      const st = statSync(arg);
      if (st.isFile()) out.add(resolve(arg));
      else if (st.isDirectory()) {
        const glob = new Glob("**/*.metadata.{yaml,yml}");
        for await (const f of glob.scan({ cwd: arg, onlyFiles: true })) {
          out.add(resolve(arg, f));
        }
      }
    } else {
      console.error(`note: ${arg} did not match any path`);
    }
  }
  return [...out].sort();
}

// ── Cross-file id-uniqueness ─────────────────────────────────────────────────

function checkUniqueIds(
  parsed: Map<string, Sidecar>,
): ValidationError[] {
  const seen = new Map<string, string[]>();
  for (const [path, doc] of parsed) {
    if (typeof doc.id === "string") {
      const list = seen.get(doc.id) ?? [];
      list.push(path);
      seen.set(doc.id, list);
    }
  }
  const errors: ValidationError[] = [];
  for (const [id, paths] of seen) {
    if (paths.length > 1) {
      for (const path of paths) {
        errors.push({
          path,
          field: "id",
          message: `id ${JSON.stringify(id)} duplicated across ${paths.length} sidecars: ${paths.join(", ")}`,
        });
      }
    }
  }
  return errors;
}

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  const args = Bun.argv.slice(2);
  if (args.length === 0) {
    console.error("Usage: bun scripts/validate_library_metadata.ts <glob-or-path>...");
    process.exit(2);
  }

  const files = await resolveInputs(args);
  if (files.length === 0) {
    console.error("No matching sidecar files found.");
    process.exit(2);
  }

  const allErrors: ValidationError[] = [];
  const parsed = new Map<string, Sidecar>();

  for (const path of files) {
    let doc: Sidecar;
    try {
      doc = parseSimpleYaml(readFileSync(path, "utf-8")) as Sidecar;
    } catch (e) {
      allErrors.push({ path, field: "<yaml>", message: (e as Error).message });
      continue;
    }
    parsed.set(path, doc);
    allErrors.push(...validate(path, doc));
  }

  allErrors.push(...checkUniqueIds(parsed));

  if (allErrors.length === 0) {
    console.log(`✓ ${files.length} sidecar(s) valid`);
    process.exit(0);
  }

  for (const e of allErrors) {
    console.error(`${e.path}: ${e.field}: ${e.message}`);
  }
  console.error(`\n✗ ${allErrors.length} error(s) across ${files.length} sidecar(s)`);
  process.exit(1);
}

main();
