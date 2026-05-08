/**
 * Theme tokens for the hydrocarbon-bonding clips.
 *
 * Mirrors the existing chemistry-video themes (G11-CHEM-002 Structure of Atom)
 * and locks the functional-group palette from
 * `pipeline/visual_templates/organic_chemistry.ts` so colour conventions
 * stay consistent with the static SVG catalogue.
 */

export const PAI_THEME = {
  colors: {
    // Stage palette
    background: "#0f172a",
    backgroundAlt: "#1e293b",
    text: "#f1f5f9",
    textMuted: "#94a3b8",
    textDark: "#64748b",
    paperGround: "#F5F5F0",

    // Brand accents
    accent: "#8b5cf6",
    accentLight: "#a78bfa",
    accentDark: "#7c3aed",

    // Status
    success: "#10b981",
    warning: "#f59e0b",
    error: "#ef4444",
    info: "#3b82f6",

    // Atoms
    carbon: "#1f2937", // dark slate — the C atoms in skeletal structures
    hydrogen: "#e5e7eb", // light grey
    bondInk: "#1a202c", // bond-stroke colour from organic_chemistry.ts
    bondInkOnDark: "#e2e8f0", // bond stroke when rendered on the dark stage

    // Bond components
    sigma: "#3b82f6", // σ bond — blue (electron-pair-style line)
    pi: "#a855f7", // π bond — purple (above-and-below electron cloud)
    delocalised: "#f59e0b", // delocalised π cloud — amber

    // Functional groups (locked palette — same as organic_chemistry.ts)
    fgRing: "#7c3aed", // aromatic ring — purple
    fgHydroxyl: "#ef4444", // OH — red (unused here but kept for future)
  },

  typography: {
    fontFamily:
      'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontFamilyMono:
      'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',

    title: { fontSize: 72, fontWeight: "bold" as const, lineHeight: 1.1 },
    subtitle: { fontSize: 36, fontWeight: 600 as const, lineHeight: 1.2 },
    caption: { fontSize: 30, fontWeight: 400 as const, lineHeight: 1.4 },
    label: { fontSize: 24, fontWeight: 600 as const, lineHeight: 1.3 },
    formula: { fontSize: 56, fontWeight: 700 as const, lineHeight: 1.0 },
  },

  animation: {
    springDefault: { damping: 12, stiffness: 100 },
    springFast: { damping: 15, stiffness: 150 },
    springBouncy: { damping: 8, stiffness: 120 },
  },
} as const;

// ── Bond geometry primitives ─────────────────────────────────────────────
// Lifted from `pipeline/visual_templates/organic_chemistry.ts` (which
// emits SVG strings); here we return JSX <line> / <g> elements suitable
// for Remotion frame-by-frame rendering.

export function singleBondLine(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  color: string = PAI_THEME.colors.bondInkOnDark,
  width: number = 4,
  opacity: number = 1,
) {
  return (
    <line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      stroke={color}
      strokeWidth={width}
      strokeLinecap="round"
      opacity={opacity}
    />
  );
}

/**
 * Two parallel lines with a perpendicular offset of ~5 px from the axis.
 * The double bond is drawn slightly inset on both ends so the inner line
 * doesn't touch the atom labels.
 */
export function doubleBondLines(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  color: string = PAI_THEME.colors.bondInkOnDark,
  width: number = 4,
  offset: number = 6,
  opacity: number = 1,
) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy);
  const nx = -dy / len; // perpendicular unit
  const ny = dx / len;
  const inset = 0.18;
  const ix = dx * inset;
  const iy = dy * inset;
  return (
    <g opacity={opacity}>
      {/* outer line — primary axis */}
      <line
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke={color}
        strokeWidth={width}
        strokeLinecap="round"
      />
      {/* inner line — parallel, inset on each end */}
      <line
        x1={x1 + ix + nx * offset}
        y1={y1 + iy + ny * offset}
        x2={x2 - ix + nx * offset}
        y2={y2 - iy + ny * offset}
        stroke={color}
        strokeWidth={width}
        strokeLinecap="round"
      />
    </g>
  );
}

/** Three parallel lines for triple bond — outer axis + two perpendicular insets. */
export function tripleBondLines(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  color: string = PAI_THEME.colors.bondInkOnDark,
  width: number = 4,
  offset: number = 8,
  opacity: number = 1,
) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy);
  const nx = -dy / len;
  const ny = dx / len;
  const inset = 0.20;
  const ix = dx * inset;
  const iy = dy * inset;
  return (
    <g opacity={opacity}>
      {/* central axis */}
      <line
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke={color}
        strokeWidth={width}
        strokeLinecap="round"
      />
      {/* upper inset line */}
      <line
        x1={x1 + ix + nx * offset}
        y1={y1 + iy + ny * offset}
        x2={x2 - ix + nx * offset}
        y2={y2 - iy + ny * offset}
        stroke={color}
        strokeWidth={width}
        strokeLinecap="round"
      />
      {/* lower inset line */}
      <line
        x1={x1 + ix - nx * offset}
        y1={y1 + iy - ny * offset}
        x2={x2 - ix - nx * offset}
        y2={y2 - iy - ny * offset}
        stroke={color}
        strokeWidth={width}
        strokeLinecap="round"
      />
    </g>
  );
}

export const FPS = 30;
export const SCENE_DURATION_FRAMES = 720; // 24 s per scene
