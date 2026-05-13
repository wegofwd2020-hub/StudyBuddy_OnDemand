/**
 * PeriodicityTrendsScene — animated walkthrough of three periodic-table trends
 * over the same 18-group long-form table.
 *
 * Story arc:
 *   1. Title fades in. The empty table shell fades up: 18 columns × 7 rows of
 *      ghost-tiles. Symbols then reveal in a left-to-right sweep across each
 *      period (period 1 first, then 2, then 3, then 4 main groups).
 *   2. Tiles glow with their s/p/d/f block colour to anchor the structure.
 *   3. Trend 1 — atomic radius: each tile fills with a blue→red gradient
 *      based on (down + left). A directional arrow plays bottom-left.
 *      Strapline: "Atomic radius — biggest at bottom-left."
 *   4. Wash clears. Trend 2 — first ionisation enthalpy: same tiles now
 *      coloured red→blue (the reverse direction). Arrow flips to top-right.
 *      Strapline: "Ionisation enthalpy — peaks top-right."
 *   5. Wash clears. Trend 3 — electronegativity: tiles coloured pale-yellow
 *      → deep red, peaking at fluorine (period 2, group 17). A burst-glow
 *      lights up the F tile. Strapline: "Electronegativity — F is the global
 *      maximum (3.98)."
 *   6. Tag card: "Three trends, one driver — effective nuclear charge × shell
 *      number."
 *
 * Frames @ 30 fps (32 s total = 960 frames):
 *   0–60     title + subtitle fade in
 *   60–180   table shell + symbol reveal (sweep)
 *   180–270  block colours pulse (anchor s/p/d/f)
 *   270–450  trend 1 — atomic radius (180 frames = 6 s)
 *   450–630  trend 2 — ionisation enthalpy (180 frames = 6 s)
 *   630–840  trend 3 — electronegativity + F highlight (210 frames = 7 s)
 *   840–960  closing tag (120 frames = 4 s)
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Layout constants ────────────────────────────────────────────────────────
const STAGE_W = 1920;
const STAGE_H = 1080;

// Periodic-table grid: 18 cols × 7 rows visible in the main block, plus 2 f-block rows
const COLS = 18;
const TILE_W = 78;
const TILE_H = 78;
const TILE_GAP = 8;
const GRID_W = COLS * TILE_W + (COLS - 1) * TILE_GAP;
const GRID_X0 = (STAGE_W - GRID_W) / 2;
const GRID_Y0 = 230;

const tileX = (col: number) => GRID_X0 + col * (TILE_W + TILE_GAP);
const tileY = (row: number) => GRID_Y0 + row * (TILE_H + TILE_GAP);

// ── Element catalogue ──────────────────────────────────────────────────────
type Block = 's' | 'p' | 'd' | 'f';
type Element = {
  Z: number;
  symbol: string;
  col: number;        // 0-indexed group (0..17)
  row: number;        // 0-indexed period (0..6 main; 7..8 f-block extension)
  block: Block;
  // Trend numerics (used to colour washes)
  radius?: number;        // pm, atomic radius
  IE1?: number;           // kJ/mol, first ionisation enthalpy
  EN?: number;            // Pauling electronegativity
};

// Period 1
const PERIOD_1: Element[] = [
  { Z: 1, symbol: 'H', col: 0, row: 0, block: 's', radius: 53, IE1: 1312, EN: 2.20 },
  { Z: 2, symbol: 'He', col: 17, row: 0, block: 's', radius: 31, IE1: 2372 },
];
const PERIOD_2: Element[] = [
  { Z: 3, symbol: 'Li', col: 0, row: 1, block: 's', radius: 152, IE1: 520, EN: 0.98 },
  { Z: 4, symbol: 'Be', col: 1, row: 1, block: 's', radius: 112, IE1: 899, EN: 1.57 },
  { Z: 5, symbol: 'B', col: 12, row: 1, block: 'p', radius: 88, IE1: 801, EN: 2.04 },
  { Z: 6, symbol: 'C', col: 13, row: 1, block: 'p', radius: 77, IE1: 1086, EN: 2.55 },
  { Z: 7, symbol: 'N', col: 14, row: 1, block: 'p', radius: 75, IE1: 1402, EN: 3.04 },
  { Z: 8, symbol: 'O', col: 15, row: 1, block: 'p', radius: 73, IE1: 1314, EN: 3.44 },
  { Z: 9, symbol: 'F', col: 16, row: 1, block: 'p', radius: 72, IE1: 1681, EN: 3.98 },
  { Z: 10, symbol: 'Ne', col: 17, row: 1, block: 'p', radius: 71, IE1: 2081 },
];
const PERIOD_3: Element[] = [
  { Z: 11, symbol: 'Na', col: 0, row: 2, block: 's', radius: 186, IE1: 496, EN: 0.93 },
  { Z: 12, symbol: 'Mg', col: 1, row: 2, block: 's', radius: 160, IE1: 738, EN: 1.31 },
  { Z: 13, symbol: 'Al', col: 12, row: 2, block: 'p', radius: 143, IE1: 577, EN: 1.61 },
  { Z: 14, symbol: 'Si', col: 13, row: 2, block: 'p', radius: 117, IE1: 786, EN: 1.90 },
  { Z: 15, symbol: 'P', col: 14, row: 2, block: 'p', radius: 110, IE1: 1012, EN: 2.19 },
  { Z: 16, symbol: 'S', col: 15, row: 2, block: 'p', radius: 104, IE1: 999, EN: 2.58 },
  { Z: 17, symbol: 'Cl', col: 16, row: 2, block: 'p', radius: 99, IE1: 1251, EN: 3.16 },
  { Z: 18, symbol: 'Ar', col: 17, row: 2, block: 'p', radius: 97, IE1: 1521 },
];
const PERIOD_4_S: Element[] = [
  { Z: 19, symbol: 'K', col: 0, row: 3, block: 's', radius: 227, IE1: 419, EN: 0.82 },
  { Z: 20, symbol: 'Ca', col: 1, row: 3, block: 's', radius: 197, IE1: 590, EN: 1.00 },
];
const PERIOD_4_D: Element[] = [
  { Z: 21, symbol: 'Sc', col: 2, row: 3, block: 'd', radius: 162, IE1: 633, EN: 1.36 },
  { Z: 22, symbol: 'Ti', col: 3, row: 3, block: 'd', radius: 147, IE1: 659, EN: 1.54 },
  { Z: 23, symbol: 'V', col: 4, row: 3, block: 'd', radius: 134, IE1: 651, EN: 1.63 },
  { Z: 24, symbol: 'Cr', col: 5, row: 3, block: 'd', radius: 128, IE1: 653, EN: 1.66 },
  { Z: 25, symbol: 'Mn', col: 6, row: 3, block: 'd', radius: 127, IE1: 717, EN: 1.55 },
  { Z: 26, symbol: 'Fe', col: 7, row: 3, block: 'd', radius: 126, IE1: 762, EN: 1.83 },
  { Z: 27, symbol: 'Co', col: 8, row: 3, block: 'd', radius: 125, IE1: 760, EN: 1.88 },
  { Z: 28, symbol: 'Ni', col: 9, row: 3, block: 'd', radius: 124, IE1: 737, EN: 1.91 },
  { Z: 29, symbol: 'Cu', col: 10, row: 3, block: 'd', radius: 128, IE1: 745, EN: 1.90 },
  { Z: 30, symbol: 'Zn', col: 11, row: 3, block: 'd', radius: 134, IE1: 906, EN: 1.65 },
];
const PERIOD_4_P: Element[] = [
  { Z: 31, symbol: 'Ga', col: 12, row: 3, block: 'p', radius: 135, IE1: 579, EN: 1.81 },
  { Z: 32, symbol: 'Ge', col: 13, row: 3, block: 'p', radius: 122, IE1: 762, EN: 2.01 },
  { Z: 33, symbol: 'As', col: 14, row: 3, block: 'p', radius: 119, IE1: 947, EN: 2.18 },
  { Z: 34, symbol: 'Se', col: 15, row: 3, block: 'p', radius: 120, IE1: 941, EN: 2.55 },
  { Z: 35, symbol: 'Br', col: 16, row: 3, block: 'p', radius: 120, IE1: 1140, EN: 2.96 },
  { Z: 36, symbol: 'Kr', col: 17, row: 3, block: 'p', radius: 116, IE1: 1351 },
];
// Periods 5..7 main groups only — ghost shapes for visual completeness, no
// trend numerics, no labels animated.
const PERIODS_5_to_7_GHOST = [
  // Group 1, 2 down to row 6
  { col: 0, row: 4 }, { col: 1, row: 4 },
  { col: 0, row: 5 }, { col: 1, row: 5 },
  { col: 0, row: 6 }, { col: 1, row: 6 },
  // Groups 3..12 row 4..6 (transition)
  ...Array.from({ length: 10 }).flatMap((_, i) => [
    { col: 2 + i, row: 4 },
    { col: 2 + i, row: 5 },
    { col: 2 + i, row: 6 },
  ]),
  // Groups 13..18 row 4..6
  ...Array.from({ length: 6 }).flatMap((_, i) => [
    { col: 12 + i, row: 4 },
    { col: 12 + i, row: 5 },
    { col: 12 + i, row: 6 },
  ]),
];

const ALL_ELEMENTS: Element[] = [
  ...PERIOD_1,
  ...PERIOD_2,
  ...PERIOD_3,
  ...PERIOD_4_S,
  ...PERIOD_4_D,
  ...PERIOD_4_P,
];

// Reveal sweep order — left to right within each period, period by period
const REVEAL_ORDER: Element[] = [
  ...PERIOD_1.slice().sort((a, b) => a.col - b.col),
  ...PERIOD_2.slice().sort((a, b) => a.col - b.col),
  ...PERIOD_3.slice().sort((a, b) => a.col - b.col),
  ...PERIOD_4_S,
  ...PERIOD_4_D,
  ...PERIOD_4_P,
];

// ── Frame anchors ───────────────────────────────────────────────────────────
const F_TITLE_END = 60;
const F_REVEAL_START = 60;
const F_REVEAL_END = 180;
const F_BLOCKS_PULSE_END = 270;
const F_T1_START = 270;
const F_T1_END = 450;
const F_T2_START = 450;
const F_T2_END = 630;
const F_T3_START = 630;
const F_T3_END = 840;
const F_TAG_START = 840;

// ── Colour helpers ──────────────────────────────────────────────────────────
function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}
function lerpColor(hexA: string, hexB: string, t: number): string {
  const pa = parseInt(hexA.slice(1), 16);
  const pb = parseInt(hexB.slice(1), 16);
  const ar = (pa >> 16) & 0xff, ag = (pa >> 8) & 0xff, ab = pa & 0xff;
  const br = (pb >> 16) & 0xff, bg = (pb >> 8) & 0xff, bb = pb & 0xff;
  const r = Math.round(lerp(ar, br, t));
  const g = Math.round(lerp(ag, bg, t));
  const b = Math.round(lerp(ab, bb, t));
  return `rgb(${r}, ${g}, ${b})`;
}

function blockColor(block: Block): string {
  switch (block) {
    case 's': return PAI_THEME.colors.blockS;
    case 'p': return PAI_THEME.colors.blockP;
    case 'd': return PAI_THEME.colors.blockD;
    case 'f': return PAI_THEME.colors.blockF;
  }
}

// Map a value in [vMin, vMax] to a t in [0, 1].
function normalise(v: number, vMin: number, vMax: number): number {
  if (vMax <= vMin) return 0;
  return Math.max(0, Math.min(1, (v - vMin) / (vMax - vMin)));
}

// ── Component ───────────────────────────────────────────────────────────────
export const PeriodicityTrendsScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title fade
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  // Title shrinks slightly when trends start
  const titleSize = interpolate(frame, [F_T1_START, F_T1_START + 30], [56, 44], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // Reveal progress
  const revealProgress = interpolate(frame, [F_REVEAL_START, F_REVEAL_END], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const revealedCount = Math.floor(revealProgress * REVEAL_ORDER.length);

  // Block-colour pulse: tiles glow with their block colour at peak strength
  // around frame 220, then fade so the trend washes can take over.
  const blockGlow = interpolate(
    frame, [180, 220, 260, 300], [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  // Strapline opacity helpers
  const strapOp = (start: number, end: number) => {
    const fadeIn = interpolate(frame, [start, start + 30], [0, 1], {
      extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    });
    const fadeOut = interpolate(frame, [end - 30, end], [1, 0], {
      extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    });
    return fadeIn * fadeOut;
  };

  // Trend wash strengths (each ramps in over 30 frames, holds, then ramps out)
  const t1Wash = interpolate(
    frame, [F_T1_START, F_T1_START + 30, F_T1_END - 30, F_T1_END],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );
  const t2Wash = interpolate(
    frame, [F_T2_START, F_T2_START + 30, F_T2_END - 30, F_T2_END],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );
  const t3Wash = interpolate(
    frame, [F_T3_START, F_T3_START + 30, F_T3_END - 30, F_T3_END],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  // F-tile spotlight pulse for trend 3
  const fGlow = interpolate(
    frame, [F_T3_START + 60, F_T3_START + 100, F_T3_END - 60, F_T3_END - 30],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  // Tag card
  const tagOp = interpolate(frame, [F_TAG_START, F_TAG_START + 30], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // Trend numeric ranges (used for colour mapping)
  const radii = ALL_ELEMENTS.map((e) => e.radius!).filter((v) => v != null) as number[];
  const rMin = Math.min(...radii), rMax = Math.max(...radii);
  const ies = ALL_ELEMENTS.map((e) => e.IE1!).filter((v) => v != null) as number[];
  const ieMin = Math.min(...ies), ieMax = Math.max(...ies);
  const ens = ALL_ELEMENTS.map((e) => e.EN!).filter((v) => v != null) as number[];
  const enMin = Math.min(...ens), enMax = Math.max(...ens);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
        fontFamily: PAI_THEME.typography.fontFamily,
      }}
    >
      {/* ── Title ─────────────────────────────────────────────────── */}
      <div style={{ position: 'absolute', top: 36, left: 0, right: 0, textAlign: 'center' }}>
        <h1 style={{
          fontSize: titleSize, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleScale})`,
        }}>
          Periodicity — Three Trends, One Table
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          atomic radius  ·  ionisation enthalpy  ·  electronegativity
        </p>
      </div>

      {/* ── Periodic table grid ─────────────────────────────────────── */}
      <svg width={STAGE_W} height={STAGE_H} viewBox={`0 0 ${STAGE_W} ${STAGE_H}`}
        style={{ position: 'absolute', inset: 0 }}>

        {/* Ghost shells for periods 5..7 main groups */}
        {PERIODS_5_to_7_GHOST.map((g, i) => (
          <rect key={`ghost-${i}`}
            x={tileX(g.col)} y={tileY(g.row)} width={TILE_W} height={TILE_H}
            rx={6}
            fill={PAI_THEME.colors.backgroundDark}
            stroke={PAI_THEME.colors.textDark}
            strokeWidth={1}
            opacity={0.35} />
        ))}

        {/* Active tiles */}
        {ALL_ELEMENTS.map((el, i) => {
          // Reveal-order index of this element
          const rIdx = REVEAL_ORDER.findIndex((e) => e.Z === el.Z);
          const tileRevealed = rIdx < revealedCount;
          // Per-tile fade-in window (smooth sweep)
          const tileFrameIn = F_REVEAL_START + (rIdx / REVEAL_ORDER.length) * (F_REVEAL_END - F_REVEAL_START);
          const tileOp = interpolate(
            frame, [tileFrameIn, tileFrameIn + 12], [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );

          // Determine fill colour based on the active phase
          const baseFill = PAI_THEME.colors.backgroundDark;
          const blockFill = blockColor(el.block);

          // Trend washes
          let trendFill = baseFill;
          let trendStrength = 0;
          if (t1Wash > 0 && el.radius != null) {
            const tNorm = normalise(el.radius, rMin, rMax); // 0 small → 1 big
            // Atomic radius: small = cool blue, big = warm red
            trendFill = lerpColor('#1e3a8a', '#dc2626', tNorm);
            trendStrength = t1Wash;
          } else if (t2Wash > 0 && el.IE1 != null) {
            const tNorm = normalise(el.IE1, ieMin, ieMax); // 0 low → 1 high
            // Ionisation: low = cool blue, high = warm red (peaks top-right)
            trendFill = lerpColor('#1e3a8a', '#dc2626', tNorm);
            trendStrength = t2Wash;
          } else if (t3Wash > 0 && el.EN != null) {
            const tNorm = normalise(el.EN, enMin, enMax); // 0 low → 1 high
            // EN: pale yellow → deep red, peaks at F
            trendFill = lerpColor('#fef3c7', '#dc2626', tNorm);
            trendStrength = t3Wash;
          }

          // Composite fill: blockGlow overlays during 180–300 frames
          let fill: string = baseFill;
          if (trendStrength > 0) {
            // Cross-fade between the underlying base + the trend wash
            fill = trendFill;
          } else if (blockGlow > 0) {
            fill = lerpColor(baseFill, blockFill, blockGlow * 0.85);
          }

          // F-tile extra glow during trend 3
          const isF = el.symbol === 'F';
          const fHighlight = isF ? fGlow : 0;

          // Symbol colour: light when fill is dark, dark when fill is pale (trend 3 yellows)
          const symbolColor =
            t3Wash > 0 && el.EN != null && normalise(el.EN, enMin, enMax) < 0.5
              ? '#1a202c'
              : PAI_THEME.colors.text;

          return (
            <g key={el.Z} opacity={tileRevealed ? tileOp : 0}>
              <rect
                x={tileX(el.col)} y={tileY(el.row)} width={TILE_W} height={TILE_H}
                rx={6}
                fill={fill}
                stroke={isF && fHighlight > 0 ? '#fef08a' : PAI_THEME.colors.text}
                strokeWidth={isF && fHighlight > 0 ? 4 : 1.5}
                style={isF && fHighlight > 0
                  ? { filter: `drop-shadow(0 0 ${12 * fHighlight}px #fef08a)` }
                  : undefined} />

              <text
                x={tileX(el.col) + 8} y={tileY(el.row) + 18}
                fontSize={13} fill={symbolColor} opacity={0.85}>
                {el.Z}
              </text>
              <text
                x={tileX(el.col) + TILE_W / 2} y={tileY(el.row) + TILE_H / 2 + 9}
                fontSize={26} fontWeight={700} fill={symbolColor} textAnchor="middle">
                {el.symbol}
              </text>
            </g>
          );
        })}

        {/* ── Trend 1 — atomic radius arrow (down-left direction) ─────── */}
        {t1Wash > 0 && (
          <g opacity={t1Wash}>
            <defs>
              <marker id="t1-arr" viewBox="0 0 10 10" refX={9} refY={5} markerWidth={10} markerHeight={10} orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#dc2626" />
              </marker>
            </defs>
            {/* Arrow from upper-right to lower-left */}
            <line
              x1={tileX(15) + TILE_W / 2} y1={tileY(0) + TILE_H / 2}
              x2={tileX(0) + TILE_W / 2} y2={tileY(3) + TILE_H / 2}
              stroke="#dc2626" strokeWidth={5}
              markerEnd="url(#t1-arr)"
              opacity={0.85} />
            <text
              x={tileX(8)} y={tileY(0) - 14}
              fontSize={28} fontWeight={700} fill="#dc2626" textAnchor="middle">
              radius grows ↘ down + ← left
            </text>
          </g>
        )}

        {/* ── Trend 2 — ionisation enthalpy arrow (top-right) ─────────── */}
        {t2Wash > 0 && (
          <g opacity={t2Wash}>
            <defs>
              <marker id="t2-arr" viewBox="0 0 10 10" refX={9} refY={5} markerWidth={10} markerHeight={10} orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#facc15" />
              </marker>
            </defs>
            {/* Arrow from lower-left to upper-right */}
            <line
              x1={tileX(0) + TILE_W / 2} y1={tileY(3) + TILE_H / 2}
              x2={tileX(17) + TILE_W / 2} y2={tileY(0) + TILE_H / 2}
              stroke="#facc15" strokeWidth={5}
              markerEnd="url(#t2-arr)"
              opacity={0.9} />
            <text
              x={tileX(8)} y={tileY(0) - 14}
              fontSize={28} fontWeight={700} fill="#facc15" textAnchor="middle">
              IE₁ grows ↗ up + → right
            </text>
          </g>
        )}

        {/* ── Trend 3 — electronegativity arrow + F spotlight ─────────── */}
        {t3Wash > 0 && (
          <g opacity={t3Wash}>
            <defs>
              <marker id="t3-arr" viewBox="0 0 10 10" refX={9} refY={5} markerWidth={10} markerHeight={10} orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#dc2626" />
              </marker>
              <radialGradient id="f-spot" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#fef08a" stopOpacity={0.55} />
                <stop offset="60%" stopColor="#fef08a" stopOpacity={0.18} />
                <stop offset="100%" stopColor="#fef08a" stopOpacity={0} />
              </radialGradient>
            </defs>
            {/* F spotlight — large radial glow centred on F (period 2, group 17 → col 16, row 1) */}
            <circle
              cx={tileX(16) + TILE_W / 2} cy={tileY(1) + TILE_H / 2}
              r={160}
              fill="url(#f-spot)"
              opacity={fGlow} />

            <line
              x1={tileX(0) + TILE_W / 2} y1={tileY(3) + TILE_H / 2}
              x2={tileX(16) + TILE_W / 2} y2={tileY(1) + TILE_H / 2}
              stroke="#dc2626" strokeWidth={5}
              markerEnd="url(#t3-arr)"
              opacity={0.85} />
            <text
              x={tileX(16) + TILE_W / 2 + 18} y={tileY(1) - 14}
              fontSize={26} fontWeight={700} fill="#fef08a" textAnchor="end"
              opacity={fGlow}>
              F = 3.98 ★ peak
            </text>
          </g>
        )}
      </svg>

      {/* ── Strapline (bottom) ──────────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 880, left: 0, right: 0, textAlign: 'center',
        fontSize: 36, fontWeight: 700, color: PAI_THEME.colors.text,
        opacity: strapOp(F_T1_START + 20, F_T1_END - 20),
      }}>
        Atomic radius — biggest at <span style={{ color: PAI_THEME.colors.warning }}>bottom-left</span>.
      </div>
      <div style={{
        position: 'absolute', top: 880, left: 0, right: 0, textAlign: 'center',
        fontSize: 36, fontWeight: 700, color: PAI_THEME.colors.text,
        opacity: strapOp(F_T2_START + 20, F_T2_END - 20),
      }}>
        Ionisation enthalpy — peaks at <span style={{ color: '#facc15' }}>top-right</span>.
      </div>
      <div style={{
        position: 'absolute', top: 880, left: 0, right: 0, textAlign: 'center',
        fontSize: 36, fontWeight: 700, color: PAI_THEME.colors.text,
        opacity: strapOp(F_T3_START + 20, F_T3_END - 20),
      }}>
        Electronegativity — fluorine is the global maximum (Pauling 3.98).
      </div>

      {/* ── Block-anchor strapline during 180–270 ───────────────────── */}
      <div style={{
        position: 'absolute', top: 880, left: 0, right: 0, textAlign: 'center',
        fontSize: 32, fontWeight: 600, color: PAI_THEME.colors.textMuted,
        opacity: strapOp(195, 265),
      }}>
        <span style={{ color: PAI_THEME.colors.blockS }}>s-block</span>
        {'   '}·{'   '}
        <span style={{ color: PAI_THEME.colors.blockP }}>p-block</span>
        {'   '}·{'   '}
        <span style={{ color: PAI_THEME.colors.blockD }}>d-block</span>
        {'   '}·{'   '}
        <span style={{ color: PAI_THEME.colors.blockF }}>f-block</span>
        {'   '}— shape of orbital filling.
      </div>

      {/* ── Closing tag ─────────────────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 460, left: 0, right: 0, textAlign: 'center',
        opacity: tagOp,
      }}>
        <div style={{
          display: 'inline-block',
          padding: '32px 56px',
          borderRadius: 24,
          background: PAI_THEME.colors.warmWash,
          border: `3px solid ${PAI_THEME.colors.warning}`,
          backdropFilter: 'blur(4px)',
        }}>
          <div style={{
            fontSize: 50, fontWeight: 700, color: PAI_THEME.colors.text,
          }}>
            Three trends, one driver.
          </div>
          <div style={{
            fontSize: 30, color: PAI_THEME.colors.accentLight, marginTop: 16,
            fontStyle: 'italic',
          }}>
            effective nuclear charge  ×  shell number
          </div>
          <div style={{
            fontSize: 22, color: PAI_THEME.colors.textMuted, marginTop: 14,
          }}>
            More protons pulling, fewer shells in the way → tighter, more reactive atom.
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
