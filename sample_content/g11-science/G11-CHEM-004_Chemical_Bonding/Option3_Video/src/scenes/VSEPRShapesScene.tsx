/**
 * VSEPRShapesScene — animated gallery of four VSEPR molecular geometries.
 *
 * The same central atom holds 4 valence directions. We morph the bond
 * directions and lone-pair "balloons" between four real molecules:
 *
 *   stage 0  (0–6s)   methane  CH₄    109.5° tetrahedral   (4 bonds, 0 LP)
 *   stage 1  (6–12s)  water    H₂O    104.5° bent          (2 bonds, 2 LP)
 *   stage 2  (12–18s) ammonia  NH₃    107°   trigonal pyr. (3 bonds, 1 LP)
 *   stage 3  (18–24s) CO₂                180°   linear        (2 bonds, 0 LP)
 *   stage 4  (24–28s) summary panel
 *
 * Bond directions interpolate smoothly between stages so the viewer sees
 * the geometry "morph". Bond-angle text counts up/down between targets.
 * H/N/O/C labels at each terminal swap as the molecule changes.
 *
 * 28 s @ 30 fps = 840 frames.
 */
import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  useVideoConfig,
  spring,
} from 'remotion';
import { PAI_THEME } from '../theme';

// ── Stage timing (frames) ───────────────────────────────────────────────────
const FPS = 30;
const SEC = (s: number) => Math.round(s * FPS);

const F_TITLE_END = SEC(1.5);
const F_STAGE0_START = SEC(2);    //   2 s — methane in
const F_STAGE0_HOLD  = SEC(6);    //   2–6 s hold methane
const F_STAGE1_START = SEC(8);    //   morph to water
const F_STAGE1_HOLD  = SEC(12);   //   8–12 s hold water
const F_STAGE2_START = SEC(14);   //   morph to ammonia
const F_STAGE2_HOLD  = SEC(18);   //   14–18 s hold ammonia
const F_STAGE3_START = SEC(20);   //   morph to CO2
const F_STAGE3_HOLD  = SEC(24);   //   20–24 s hold CO2
const F_SUMMARY_IN   = SEC(25);   //   summary fade in
// total duration set in Root.tsx: 28 s

// ── Geometry layout ─────────────────────────────────────────────────────────
const CX = 960;     // canvas centre
const CY = 600;
const BOND_LEN = 230;
const TERMINAL_R = 56;
const NUCLEUS_R = 70;

type MoleculeKey = 'CH4' | 'H2O' | 'NH3' | 'CO2';

type BondSpec = {
  // angle in degrees, 0° = right, 90° = up (mathematical convention),
  // we'll convert to SVG (y inverted) at draw time
  angleDeg: number;
  terminal: 'H' | 'O' | 'N' | 'C';
  // Bond order — affects how many parallel lines we draw for the bond
  order?: 1 | 2 | 3;
};

type LonePairSpec = {
  angleDeg: number;
};

type MoleculeShape = {
  key: MoleculeKey;
  name: string;             // "Methane"
  formula: string;          // "CH₄"
  centralAtom: 'C' | 'O' | 'N';
  axe: string;              // "AX₄"
  shapeName: string;        // "Tetrahedral"
  angleDeg: number;         // 109.5, 104.5, 107, 180
  angleLabel: string;       // "109.5°"
  bonds: BondSpec[];
  lonePairs: LonePairSpec[];
  caption: string;
};

// In SVG coords: 0° = right (x+), and our angleDeg is measured CCW from +x
// (so 90° = up in math sense = up on the screen since we'll handle Y inversion).

// Tetrahedral (CH4) — 4 bonds at 109.5° apart, 2D projection
// Use a "saw-horse" style: two front bonds in plane, one wedge (closer), one dash.
// For an animated planar approximation, place 4 bonds at 90, 210, 330 + back-out-of-plane.
// To stay in 2D we fan them: 60, 120, 240, 300 degrees (kite shape).
const METHANE: MoleculeShape = {
  key: 'CH4',
  name: 'Methane',
  formula: 'CH₄',
  centralAtom: 'C',
  axe: 'AX₄',
  shapeName: 'Tetrahedral',
  angleDeg: 109.5,
  angleLabel: '109.5°',
  bonds: [
    { angleDeg:  60, terminal: 'H' },
    { angleDeg: 120, terminal: 'H' },
    { angleDeg: 240, terminal: 'H' },
    { angleDeg: 300, terminal: 'H' },
  ],
  lonePairs: [],
  caption: 'CH₄ · sp³ · 0 lone pairs · all 109.5°',
};

// Water (H2O) — 2 bonds, 104.5° between them, opening downward.
// Place bond at -90+(104.5/2) and -90-(104.5/2) deg from horizontal — but in our convention
// 0° = +x. The H atoms sit below the O. We point bonds at 270+52.25 and 270-52.25 → 322.25 / 217.75.
const WATER: MoleculeShape = {
  key: 'H2O',
  name: 'Water',
  formula: 'H₂O',
  centralAtom: 'O',
  axe: 'AX₂E₂',
  shapeName: 'Bent',
  angleDeg: 104.5,
  angleLabel: '104.5°',
  bonds: [
    { angleDeg: 217.75, terminal: 'H' },
    { angleDeg: 322.25, terminal: 'H' },
  ],
  lonePairs: [
    // lone pairs above, splayed
    { angleDeg:  52.25 },
    { angleDeg: 127.75 },
  ],
  caption: 'H₂O · sp³ · 2 lone pairs squeeze H–O–H to 104.5°',
};

// Ammonia (NH3) — 3 bonds at ~107°, splay opens downward (umbrella-down).
// 1 bond pointing roughly down (270°), two more 107° apart from it.
const AMMONIA: MoleculeShape = {
  key: 'NH3',
  name: 'Ammonia',
  formula: 'NH₃',
  centralAtom: 'N',
  axe: 'AX₃E',
  shapeName: 'Trigonal pyramidal',
  angleDeg: 107,
  angleLabel: '107°',
  bonds: [
    { angleDeg: 270, terminal: 'H' },
    { angleDeg: 270 + 110, terminal: 'H' }, // ~20° (slightly more than 107 for projection)
    { angleDeg: 270 - 110, terminal: 'H' }, // ~160°
  ],
  lonePairs: [
    { angleDeg: 90 },
  ],
  caption: 'NH₃ · sp³ · 1 lone pair → H–N–H = 107°',
};

// CO2 — linear, two double bonds, 180°.
const CO2: MoleculeShape = {
  key: 'CO2',
  name: 'Carbon dioxide',
  formula: 'CO₂',
  centralAtom: 'C',
  axe: 'AX₂',
  shapeName: 'Linear',
  angleDeg: 180,
  angleLabel: '180°',
  bonds: [
    { angleDeg:   0, terminal: 'O', order: 2 },
    { angleDeg: 180, terminal: 'O', order: 2 },
  ],
  lonePairs: [],
  caption: 'CO₂ · sp · 0 lone pairs on C · linear, 180°',
};

const SHAPES: MoleculeShape[] = [METHANE, WATER, AMMONIA, CO2];

// ── Helpers ─────────────────────────────────────────────────────────────────
function angleToXY(deg: number, r: number): { x: number; y: number } {
  // 0° = +x, increasing CCW. SVG y is inverted, so subtract sin.
  const rad = (deg * Math.PI) / 180;
  return {
    x: CX + r * Math.cos(rad),
    y: CY - r * Math.sin(rad),
  };
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

// Determine which two stages we're between, plus a 0..1 morph parameter.
function stageInterp(frame: number): {
  fromIdx: number;
  toIdx: number;
  t: number;
  inHold: boolean;
} {
  if (frame < F_STAGE0_START) {
    return { fromIdx: 0, toIdx: 0, t: 0, inHold: true };
  }
  if (frame < F_STAGE0_HOLD) return { fromIdx: 0, toIdx: 0, t: 0, inHold: true };
  if (frame < F_STAGE1_START) {
    const t = (frame - F_STAGE0_HOLD) / (F_STAGE1_START - F_STAGE0_HOLD);
    return { fromIdx: 0, toIdx: 1, t: easeInOut(t), inHold: false };
  }
  if (frame < F_STAGE1_HOLD) return { fromIdx: 1, toIdx: 1, t: 0, inHold: true };
  if (frame < F_STAGE2_START) {
    const t = (frame - F_STAGE1_HOLD) / (F_STAGE2_START - F_STAGE1_HOLD);
    return { fromIdx: 1, toIdx: 2, t: easeInOut(t), inHold: false };
  }
  if (frame < F_STAGE2_HOLD) return { fromIdx: 2, toIdx: 2, t: 0, inHold: true };
  if (frame < F_STAGE3_START) {
    const t = (frame - F_STAGE2_HOLD) / (F_STAGE3_START - F_STAGE2_HOLD);
    return { fromIdx: 2, toIdx: 3, t: easeInOut(t), inHold: false };
  }
  return { fromIdx: 3, toIdx: 3, t: 0, inHold: true };
}

// For a given pair of molecules, build "morph slots" so we can interpolate
// bond directions and lone-pair directions slot-by-slot, even if the bond
// counts differ. We pad with "ghost" slots that fade in/out.
type MorphSlot = {
  kind: 'bond' | 'lonePair';
  fromAngle: number | null;   // null = absent in source (fade in)
  toAngle: number | null;     // null = absent in dest (fade out)
  fromTerm: 'H' | 'O' | 'N' | 'C' | null;
  toTerm: 'H' | 'O' | 'N' | 'C' | null;
  fromOrder: 1 | 2 | 3;
  toOrder: 1 | 2 | 3;
};

function buildMorphSlots(from: MoleculeShape, to: MoleculeShape): MorphSlot[] {
  const slots: MorphSlot[] = [];
  // Bond slots: pair up by index sorted by angle for a stable ordering.
  const fb = [...from.bonds].sort((a, b) => a.angleDeg - b.angleDeg);
  const tb = [...to.bonds].sort((a, b) => a.angleDeg - b.angleDeg);
  const nB = Math.max(fb.length, tb.length);
  for (let i = 0; i < nB; i++) {
    slots.push({
      kind: 'bond',
      fromAngle: fb[i]?.angleDeg ?? null,
      toAngle: tb[i]?.angleDeg ?? null,
      fromTerm: fb[i]?.terminal ?? null,
      toTerm: tb[i]?.terminal ?? null,
      fromOrder: fb[i]?.order ?? 1,
      toOrder: tb[i]?.order ?? 1,
    });
  }
  // Lone-pair slots: same idea.
  const fl = [...from.lonePairs].sort((a, b) => a.angleDeg - b.angleDeg);
  const tl = [...to.lonePairs].sort((a, b) => a.angleDeg - b.angleDeg);
  const nL = Math.max(fl.length, tl.length);
  for (let i = 0; i < nL; i++) {
    slots.push({
      kind: 'lonePair',
      fromAngle: fl[i]?.angleDeg ?? null,
      toAngle: tl[i]?.angleDeg ?? null,
      fromTerm: null,
      toTerm: null,
      fromOrder: 1,
      toOrder: 1,
    });
  }
  return slots;
}

// Given a slot and t (0..1), return the rendered angle (with fallbacks if
// either side is null), the rendered opacity (fade in/out), and term/order.
function resolveSlot(slot: MorphSlot, t: number) {
  let angle: number;
  let opacity: number;
  if (slot.fromAngle !== null && slot.toAngle !== null) {
    // Smoothly interpolate angle along the shorter arc
    let delta = slot.toAngle - slot.fromAngle;
    if (delta > 180) delta -= 360;
    if (delta < -180) delta += 360;
    angle = slot.fromAngle + delta * t;
    opacity = 1;
  } else if (slot.fromAngle !== null) {
    angle = slot.fromAngle;
    opacity = 1 - t;          // fade out
  } else if (slot.toAngle !== null) {
    angle = slot.toAngle;
    opacity = t;              // fade in
  } else {
    angle = 0;
    opacity = 0;
  }
  // Terminal: prefer destination once t > 0.5
  const term = (t < 0.5 ? slot.fromTerm : slot.toTerm) ?? slot.fromTerm ?? slot.toTerm ?? 'H';
  // Bond order: same convention
  const order = (t < 0.5 ? slot.fromOrder : slot.toOrder) ?? 1;
  return { angle, opacity, term, order };
}

// Atom colour by element
function atomColor(el: 'C' | 'O' | 'N' | 'H'): string {
  switch (el) {
    case 'C': return PAI_THEME.colors.carbon;
    case 'O': return PAI_THEME.colors.oxygen;
    case 'N': return PAI_THEME.colors.nitrogen;
    case 'H': return PAI_THEME.colors.hydrogen;
  }
}

// ── Component ───────────────────────────────────────────────────────────────
export const VSEPRShapesScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title intro
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  // Stage interpolation
  const { fromIdx, toIdx, t } = stageInterp(frame);
  const fromShape = SHAPES[fromIdx];
  const toShape = SHAPES[toIdx];
  const slots = buildMorphSlots(fromShape, toShape);

  // Currently displayed name / formula / shape — flip at midpoint of morph
  const showShape = t < 0.5 ? fromShape : toShape;

  // Bond-angle number tween (numeric)
  const displayAngle = lerp(fromShape.angleDeg, toShape.angleDeg, t);

  // Stage entrance
  const moleculeOp = interpolate(
    frame, [F_TITLE_END, F_STAGE0_START], [0, 1],
    { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' },
  );

  // Summary panel
  const summaryOp = interpolate(
    frame, [F_SUMMARY_IN, F_SUMMARY_IN + 30], [0, 1],
    { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' },
  );

  // Caption
  const caption = showShape.caption;

  // Central atom letter follows the stage flip
  const centralLetter = showShape.centralAtom;
  const centralColor = atomColor(centralLetter);

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute', top: 30, left: 0, right: 0, textAlign: 'center',
      }}>
        <h1 style={{
          fontSize: 60, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleScale})`,
        }}>
          VSEPR — Why Molecules Have the Shapes They Do
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          Electron pairs repel · they spread out as far as possible · lone pairs squeeze the rest.
        </p>
      </div>

      {/* Molecule canvas */}
      <svg
        width={1920}
        height={1080}
        viewBox="0 0 1920 1080"
        style={{ position: 'absolute', inset: 0, opacity: moleculeOp }}
      >
        <defs>
          <radialGradient id="lp-grad" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor={PAI_THEME.colors.lonePair} stopOpacity={0.85} />
            <stop offset="60%"  stopColor={PAI_THEME.colors.lonePair} stopOpacity={0.5} />
            <stop offset="100%" stopColor={PAI_THEME.colors.lonePair} stopOpacity={0} />
          </radialGradient>
        </defs>

        {/* Bonds first (under atoms) */}
        {slots.filter((s) => s.kind === 'bond').map((slot, i) => {
          const { angle, opacity, term, order } = resolveSlot(slot, t);
          if (opacity < 0.01) return null;
          const tip = angleToXY(angle, BOND_LEN);
          // For double/triple bonds draw 2 or 3 parallel lines perpendicular to the bond.
          const perpRad = ((angle + 90) * Math.PI) / 180;
          const dx = Math.cos(perpRad);
          const dy = -Math.sin(perpRad);
          const offsets = order === 1 ? [0] : order === 2 ? [-7, 7] : [-10, 0, 10];
          return (
            <g key={`bond-${i}`} opacity={opacity}>
              {offsets.map((off, k) => (
                <line
                  key={k}
                  x1={CX + dx * off}
                  y1={CY + dy * off}
                  x2={tip.x + dx * off}
                  y2={tip.y + dy * off}
                  stroke={PAI_THEME.colors.bond}
                  strokeWidth={6}
                  strokeLinecap="round"
                />
              ))}
            </g>
          );
        })}

        {/* Lone pairs (cloud balloons) */}
        {slots.filter((s) => s.kind === 'lonePair').map((slot, i) => {
          const { angle, opacity } = resolveSlot(slot, t);
          if (opacity < 0.01) return null;
          // Place balloon at ~70% of bond length — closer to nucleus, "stubby"
          const r = BOND_LEN * 0.7;
          const center = angleToXY(angle, r);
          // Orient ellipse along the radial direction
          return (
            <g key={`lp-${i}`} opacity={opacity}>
              <ellipse
                cx={center.x}
                cy={center.y}
                rx={70}
                ry={42}
                fill="url(#lp-grad)"
                stroke={PAI_THEME.colors.accent}
                strokeWidth={3}
                transform={`rotate(${-angle} ${center.x} ${center.y})`}
              />
              {/* Two tiny dots representing the electron pair */}
              <circle cx={center.x - 8} cy={center.y} r={5} fill={PAI_THEME.colors.text} />
              <circle cx={center.x + 8} cy={center.y} r={5} fill={PAI_THEME.colors.text} />
            </g>
          );
        })}

        {/* Terminal atoms (drawn after bonds, before central) */}
        {slots.filter((s) => s.kind === 'bond').map((slot, i) => {
          const { angle, opacity, term } = resolveSlot(slot, t);
          if (opacity < 0.01) return null;
          const tip = angleToXY(angle, BOND_LEN);
          const colour = atomColor(term as 'H' | 'O' | 'N' | 'C');
          const labelColor = (term === 'H' || term === 'O' || term === 'N') ? '#fff' : '#fff';
          // 'H' often rendered on a soft yellow chip; we keep white labels for contrast
          return (
            <g key={`term-${i}`} opacity={opacity}>
              <circle
                cx={tip.x}
                cy={tip.y}
                r={TERMINAL_R}
                fill={colour}
                stroke={PAI_THEME.colors.text}
                strokeWidth={3}
              />
              <text
                x={tip.x}
                y={tip.y + 14}
                fontSize={42}
                fontWeight={700}
                fill={term === 'H' ? '#1a202c' : labelColor}
                textAnchor="middle"
              >
                {term}
              </text>
            </g>
          );
        })}

        {/* Central atom */}
        <g>
          <circle
            cx={CX}
            cy={CY}
            r={NUCLEUS_R}
            fill={centralColor}
            stroke={PAI_THEME.colors.text}
            strokeWidth={4}
          />
          <text
            x={CX}
            y={CY + 18}
            fontSize={56}
            fontWeight={700}
            fill="#fff"
            textAnchor="middle"
          >
            {centralLetter}
          </text>
        </g>

        {/* Bond-angle big number (top-right of canvas) */}
        <g>
          <rect x={1500} y={140} width={340} height={140} rx={16}
            fill={PAI_THEME.colors.backgroundAlt}
            stroke={PAI_THEME.colors.accent}
            strokeWidth={2} />
          <text x={1670} y={188} fontSize={22} fontWeight={600}
            fill={PAI_THEME.colors.textMuted} textAnchor="middle">
            bond angle
          </text>
          <text x={1670} y={252} fontSize={64} fontWeight={700}
            fill={PAI_THEME.colors.accentLight} textAnchor="middle">
            {displayAngle.toFixed(1)}°
          </text>
        </g>

        {/* Molecule meta panel (top-left) */}
        <g>
          <rect x={80} y={140} width={420} height={200} rx={16}
            fill={PAI_THEME.colors.backgroundAlt}
            stroke={PAI_THEME.colors.accent}
            strokeWidth={2} />
          <text x={290} y={188} fontSize={22} fontWeight={600}
            fill={PAI_THEME.colors.textMuted} textAnchor="middle">
            current molecule
          </text>
          <text x={290} y={236} fontSize={48} fontWeight={700}
            fill={PAI_THEME.colors.text} textAnchor="middle">
            {showShape.formula}
          </text>
          <text x={290} y={278} fontSize={26} fontWeight={600}
            fill={PAI_THEME.colors.warning} textAnchor="middle">
            {showShape.shapeName}
          </text>
          <text x={290} y={314} fontSize={22}
            fill={PAI_THEME.colors.textMuted} textAnchor="middle">
            {showShape.axe}  ·  {showShape.name}
          </text>
        </g>
      </svg>

      {/* Caption */}
      <div style={{
        position: 'absolute', top: 970, left: 0, right: 0, textAlign: 'center',
        fontSize: 30, fontWeight: 700,
        color: PAI_THEME.colors.text,
        opacity: moleculeOp,
      }}>
        {caption}
      </div>

      {/* Summary overlay (last 3 s) */}
      {summaryOp > 0 && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(15, 23, 42, 0.86)',
          opacity: summaryOp,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexDirection: 'column', gap: 24,
        }}>
          <div style={{
            fontSize: 56, fontWeight: 700,
            color: PAI_THEME.colors.text,
          }}>
            Same atom — different shape, different angle.
          </div>
          <div style={{
            fontSize: 36, color: PAI_THEME.colors.accentLight, marginTop: 8,
          }}>
            CH₄ 109.5°  ·  NH₃ 107°  ·  H₂O 104.5°  ·  CO₂ 180°
          </div>
          <div style={{
            fontSize: 26, color: PAI_THEME.colors.textMuted,
            maxWidth: 1200, textAlign: 'center', lineHeight: 1.5,
          }}>
            Lone pairs push harder than bond pairs. Subtract a lone pair, lose 2.5° of angle.
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
