/**
 * pipeline/visual_templates/remotion_project.ts
 *
 * Generator for Remotion video projects (Option 3 catalogue clips).
 *
 * Stamps the byte-identical infra layer (package.json, tsconfig.json,
 * remotion.config.ts, src/index.ts, src/Root.tsx, src/theme.ts) given a
 * project spec. Scene component files are author-supplied — the generator
 * does NOT write `src/scenes/*.tsx`.
 *
 * Lifted from the 9 byte-identical infra layers across the Wave 1+2
 * Remotion clips (#342 phase E). Per the G11-PHYS-010 MEMO, the
 * package.json `zod` pin is corrected here to `4.3.6` (matches Remotion
 * CLI 4.0.458's expectation) — the existing 9 projects shipped with
 * `^3.23.8` which produced a non-blocking version-mismatch warning at
 * render time.
 *
 * Usage (programmatic — for #320 code-gen consumer):
 *   import { stampRemotionProject } from "./remotion_project.ts";
 *   stampRemotionProject(targetDir, {
 *     slug: "g9-kinematics-1d-video",
 *     packageName: "g9-kinematics-1d-video",
 *     scenes: [
 *       {
 *         id: "g9-motion-along-strip",
 *         componentName: "MotionAlongStripScene",
 *         componentFile: "MotionAlongStripScene",
 *         durationSec: 24,
 *         outputName: "G9_Kinematics_MotionAlongStrip.mp4",
 *         renderScriptKey: "motion-strip",
 *       },
 *     ],
 *   });
 *
 * After stamping, the author writes each scene file at
 * `${targetDir}/src/scenes/${componentFile}.tsx` and runs
 * `bun install && bun run render:all`.
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

export type RemotionScene = {
  /** Composition id used in <Composition id="..." /> and CLI render target. */
  id: string;
  /** React component name (e.g., "MotionAlongStripScene"). */
  componentName: string;
  /** File basename under src/scenes/, without .tsx (e.g., "MotionAlongStripScene"). */
  componentFile: string;
  /** Total clip length in seconds. Frames computed as `durationSec * fps`. */
  durationSec: number;
  /** MP4 output filename (relative to ~/Downloads). */
  outputName: string;
  /** Suffix for `render:<key>` script in package.json. */
  renderScriptKey: string;
};

export type RemotionProjectOptions = {
  /** Slug used as package.json `name` field. */
  slug: string;
  /** Composition list — one Composition entry per scene in Root.tsx. */
  scenes: RemotionScene[];
  /** Optional override; default 1920. */
  width?: number;
  /** Optional override; default 1080. */
  height?: number;
  /** Optional override; default 30. */
  fps?: number;
  /**
   * Optional Remotion CLI version pin. Default `^4.0.260` matches the
   * existing 9 projects. Update in lockstep with zod pin.
   */
  remotionVersion?: string;
  /**
   * zod pin. Default `^4.3.6` corrects the version-mismatch warning the
   * existing 9 projects emit (they ship `^3.23.8`). For *exact*
   * byte-equivalence with the existing projects, override to `^3.23.8`.
   */
  zodVersion?: string;
};

/**
 * Stamp the entire Remotion infra layer at `targetDir`. Creates the
 * directory if it doesn't exist. Does NOT overwrite scene files.
 *
 * Returns the list of files written, relative to targetDir.
 */
export function stampRemotionProject(
  targetDir: string,
  opts: RemotionProjectOptions,
): string[] {
  const W = opts.width ?? 1920;
  const H = opts.height ?? 1080;
  const FPS = opts.fps ?? 30;
  const remotionVersion = opts.remotionVersion ?? "^4.0.260";
  const zodVersion = opts.zodVersion ?? "^4.3.6";

  mkdirSync(targetDir, { recursive: true });
  mkdirSync(join(targetDir, "src"), { recursive: true });
  mkdirSync(join(targetDir, "src", "scenes"), { recursive: true });

  const written: string[] = [];

  const pkg = renderPackageJson(opts.slug, opts.scenes, remotionVersion, zodVersion);
  writeFileSync(join(targetDir, "package.json"), pkg, "utf-8");
  written.push("package.json");

  writeFileSync(join(targetDir, "tsconfig.json"), TSCONFIG, "utf-8");
  written.push("tsconfig.json");

  writeFileSync(join(targetDir, "remotion.config.ts"), REMOTION_CONFIG, "utf-8");
  written.push("remotion.config.ts");

  writeFileSync(join(targetDir, "src", "index.ts"), INDEX_TS, "utf-8");
  written.push("src/index.ts");

  writeFileSync(join(targetDir, "src", "Root.tsx"), renderRootTsx(opts.scenes, W, H, FPS), "utf-8");
  written.push("src/Root.tsx");

  writeFileSync(join(targetDir, "src", "theme.ts"), THEME_TS, "utf-8");
  written.push("src/theme.ts");

  return written;
}

// ─────────────────────────────────────────────────────────────────────────
// Per-project rendered files
// ─────────────────────────────────────────────────────────────────────────

function renderPackageJson(
  slug: string,
  scenes: RemotionScene[],
  remotionVersion: string,
  zodVersion: string,
): string {
  const renderScripts: Record<string, string> = {
    studio: "bunx remotion studio",
  };
  const renderAllParts: string[] = [];
  for (const s of scenes) {
    const key = `render:${s.renderScriptKey}`;
    renderScripts[key] = `bunx remotion render ${s.id} ~/Downloads/${s.outputName}`;
    renderAllParts.push(`bun run render:${s.renderScriptKey}`);
  }
  renderScripts["render:all"] = renderAllParts.join(" && ");

  const pkg = {
    name: slug,
    version: "1.0.0",
    private: true,
    scripts: renderScripts,
    dependencies: {
      "@remotion/cli": remotionVersion,
      react: "^18.3.1",
      "react-dom": "^18.3.1",
      remotion: remotionVersion,
      zod: zodVersion,
    },
    devDependencies: {
      "@types/react": "^18.3.0",
      typescript: "^5.4.0",
    },
  };
  return JSON.stringify(pkg, null, 2) + "\n";
}

function renderRootTsx(
  scenes: RemotionScene[],
  width: number,
  height: number,
  fps: number,
): string {
  const imports = scenes
    .map((s) => `import { ${s.componentName} } from './scenes/${s.componentFile}';`)
    .join("\n");

  // Single-scene projects render a bare <Composition />; multi-scene
  // projects wrap them in a <></> fragment. Indentation differs accordingly
  // to match the existing 9-project corpus byte-for-byte.
  const wrap = scenes.length > 1;
  const indent = wrap ? "      " : "    ";
  const compositions = scenes
    .map((s) => `${indent}<Composition
${indent}  id="${s.id}"
${indent}  component={${s.componentName}}
${indent}  durationInFrames={${fps} * ${s.durationSec}}
${indent}  fps={FPS}
${indent}  width={W}
${indent}  height={H}
${indent}  schema={schema}
${indent}  defaultProps={{}}
${indent}/>`)
    .join("\n");

  const body = wrap ? `    <>\n${compositions}\n    </>` : compositions;

  return `import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
${imports}

const schema = z.object({});

const FPS = ${fps};
const W = ${width};
const H = ${height};

export const RemotionRoot: React.FC = () => {
  return (
${body}
  );
};
`;
}

// ─────────────────────────────────────────────────────────────────────────
// Static infra files — byte-identical across all 9 Wave-1+2 projects
// ─────────────────────────────────────────────────────────────────────────

const TSCONFIG = `{
  "compilerOptions": {
    "target": "ES2018",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "lib": ["dom", "es2018"],
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "noEmit": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "allowSyntheticDefaultImports": true
  },
  "include": ["src/**/*"]
}
`;

const REMOTION_CONFIG = `import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setConcurrency(1);
`;

const INDEX_TS = `import { registerRoot } from 'remotion';
import { RemotionRoot } from './Root';

registerRoot(RemotionRoot);
`;

const THEME_TS = `/**
 * PAI Theme for Remotion — universal palette + typography across the
 * visual-library Option-3 catalogue. Lifted from the original
 * G11-PHYS-002_Kinematics/Option3_Video/src/theme.ts via #342 phase E.
 */

export const PAI_THEME = {
  colors: {
    background: '#0f172a',
    backgroundAlt: '#1e293b',
    backgroundDark: '#020617',

    accent: '#8b5cf6',
    accentLight: '#a78bfa',
    accentDark: '#7c3aed',
    accentMuted: '#6366f1',

    text: '#f1f5f9',
    textMuted: '#94a3b8',
    textDark: '#64748b',

    paperGround: '#F5F5F0',
    coolWash: 'rgba(139, 92, 246, 0.1)',
    warmWash: 'rgba(251, 191, 36, 0.1)',

    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
  },

  typography: {
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontFamilyMono: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',

    title: { fontSize: 72, fontWeight: 'bold' as const, lineHeight: 1.1 },
    subtitle: { fontSize: 48, fontWeight: '600' as const, lineHeight: 1.2 },
    heading: { fontSize: 36, fontWeight: '600' as const, lineHeight: 1.3 },
    body: { fontSize: 24, fontWeight: 'normal' as const, lineHeight: 1.5 },
    caption: { fontSize: 18, fontWeight: 'normal' as const, lineHeight: 1.4 },
    small: { fontSize: 14, fontWeight: 'normal' as const, lineHeight: 1.4 },
  },

  animation: {
    springFast: { damping: 15, stiffness: 150 },
    springDefault: { damping: 12, stiffness: 100 },
    springSlow: { damping: 10, stiffness: 80 },
    springBouncy: { damping: 8, stiffness: 120 },

    fadeFrames: 30,
    quickFade: 15,
    slowFade: 45,
  },
} as const;

export type PAITheme = typeof PAI_THEME;
`;
