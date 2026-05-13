/**
 * FunctionalGroupsScene — animated tour through five functional groups.
 *
 * Same central idea, five family snapshots:
 *
 *   stage 0  (0–6s)    methane             CH₄                   alkane
 *   stage 1  (6–12s)   methanol            CH₃OH                 alcohol  (replace one H with OH)
 *   stage 2  (12–18s)  methanal            HCHO                  aldehyde (replace H + OH with =O)
 *   stage 3  (18–24s)  methanoic acid      HCOOH                 acid     (add OH back to the aldehyde C)
 *   stage 4  (24–30s)  methyl methanoate   HCOOCH₃               ester    (replace acid OH's H with CH₃)
 *   stage 5  (30–32s)  summary panel
 *
 * For each stage we keep a list of "slots" — atom positions on a fixed canvas
 * grid. As we morph from stage A to stage B, atoms in the same slot interpolate
 * their (x, y) coordinates and labels cross-fade. Atoms that exist in only one
 * stage fade in/out.
 *
 * Bonds are derived from the slot list per stage and drawn between current
 * positions; cross-fading bonds use the same in/out logic.
 *
 * 32 s @ 30 fps = 960 frames.
 */
import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { PAI_THEME } from '../theme';

// ── Stage timing (frames) ───────────────────────────────────────────────────
const FPS = 30;
const SEC = (s: number) => Math.round(s * FPS);

const F_TITLE_END    = SEC(1.5);
const F_STAGE0_START = SEC(2);
const F_STAGE0_HOLD  = SEC(6);
const F_STAGE1_START = SEC(8);
const F_STAGE1_HOLD  = SEC(12);
const F_STAGE2_START = SEC(14);
const F_STAGE2_HOLD  = SEC(18);
const F_STAGE3_START = SEC(20);
const F_STAGE3_HOLD  = SEC(24);
const F_STAGE4_START = SEC(26);
const F_STAGE4_HOLD  = SEC(30);
const F_SUMMARY_IN   = SEC(30);

// ── Canvas geometry ─────────────────────────────────────────────────────────
const CX = 960;
const CY = 600;
const ATOM_R = 32;
const C_R = 40;

type Element = 'C' | 'H' | 'O';

type AtomSpec = {
  // a stable slot key — atoms with the same key in different stages
  // will interpolate between positions
  key: string;
  el: Element;
  // pixel offsets relative to (CX, CY)
  x: number;
  y: number;
  // optional flag to highlight as "the functional group" in this stage
  highlight?: boolean;
};

type BondSpec = {
  from: string;       // slot key
  to: string;         // slot key
  order: 1 | 2;
  // does this bond belong to the highlighted functional group?
  highlight?: boolean;
};

type Stage = {
  name: string;
  formula: string;
  family: string;          // "Alkane" "Alcohol" …
  iupacSuffix: string;     // "-ane" "-ol" …
  caption: string;
  atoms: AtomSpec[];
  bonds: BondSpec[];
};

// ── Stage 0: Methane CH₄ ─────────────────────────────────────────────────
// Central C; four H's arranged around (we keep H1 left-of-C as "swap slot"
// so it can morph into OH/=O across stages). Other three H's at top, bottom-left, bottom-right.
const METHANE: Stage = {
  name: 'Methane',
  formula: 'CH₄',
  family: 'Alkane',
  iupacSuffix: '-ane',
  caption: 'CH₄ · 4 single bonds · no functional group · the simplest organic molecule',
  atoms: [
    { key: 'C',     el: 'C', x:    0, y:    0 },
    { key: 'H_top', el: 'H', x:    0, y: -150 },
    { key: 'H_bl',  el: 'H', x: -130, y:  100 },
    { key: 'H_br',  el: 'H', x:  130, y:  100 },
    // The "right slot" — this position will hold:
    //   methane:  H
    //   methanol: O (with attached H_oh)
    //   methanal: O (double-bonded)
    //   acid:     O (double-bonded; +OH below)
    //   ester:    O (double-bonded; ester O to right)
    { key: 'X1',    el: 'H', x:  170, y:    0 },
  ],
  bonds: [
    { from: 'C', to: 'H_top', order: 1 },
    { from: 'C', to: 'H_bl',  order: 1 },
    { from: 'C', to: 'H_br',  order: 1 },
    { from: 'C', to: 'X1',    order: 1 },
  ],
};

// ── Stage 1: Methanol CH₃OH ──────────────────────────────────────────────
// Replace the X1 H with O–H (the alcohol functional group).
const METHANOL: Stage = {
  name: 'Methanol',
  formula: 'CH₃OH',
  family: 'Alcohol',
  iupacSuffix: '-ol',
  caption: 'CH₃OH · –OH replaces one H · the alcohol family · industrial solvent + fuel',
  atoms: [
    { key: 'C',     el: 'C', x:    0, y:    0 },
    { key: 'H_top', el: 'H', x:    0, y: -150 },
    { key: 'H_bl',  el: 'H', x: -130, y:  100 },
    { key: 'H_br',  el: 'H', x:  130, y:  100 },
    // X1 slot is now the O of OH
    { key: 'X1',    el: 'O', x:  170, y:    0, highlight: true },
    // New atom in this stage: the H of OH
    { key: 'H_oh',  el: 'H', x:  330, y:    0, highlight: true },
  ],
  bonds: [
    { from: 'C', to: 'H_top', order: 1 },
    { from: 'C', to: 'H_bl',  order: 1 },
    { from: 'C', to: 'H_br',  order: 1 },
    { from: 'C', to: 'X1',    order: 1, highlight: true },
    { from: 'X1', to: 'H_oh', order: 1, highlight: true },
  ],
};

// ── Stage 2: Methanal HCHO ───────────────────────────────────────────────
// One H is removed (H_bl gone), and X1's O–H is replaced by C=O double bond.
const METHANAL: Stage = {
  name: 'Methanal',
  formula: 'HCHO',
  family: 'Aldehyde',
  iupacSuffix: '-al',
  caption: 'HCHO · C=O at end of chain · the aldehyde family · pungent smell, e.g. formalin',
  atoms: [
    { key: 'C',     el: 'C', x:    0, y:    0 },
    { key: 'H_top', el: 'H', x:    0, y: -150 },
    { key: 'H_br',  el: 'H', x: -150, y:    0 }, // moved to "left of C" — terminal H
    // X1 slot now O double-bonded
    { key: 'X1',    el: 'O', x:  170, y:    0, highlight: true },
  ],
  bonds: [
    { from: 'C', to: 'H_top', order: 1 },
    { from: 'C', to: 'H_br',  order: 1 },
    { from: 'C', to: 'X1',    order: 2, highlight: true },
  ],
};

// ── Stage 3: Methanoic acid HCOOH ────────────────────────────────────────
// Aldehyde + a new –OH on the carbonyl C.
const METHANOIC_ACID: Stage = {
  name: 'Methanoic acid',
  formula: 'HCOOH',
  family: 'Carboxylic acid',
  iupacSuffix: '-oic acid',
  caption: 'HCOOH · –COOH = carbonyl + hydroxyl together · the acid family · ant venom, vinegar (with longer chain)',
  atoms: [
    { key: 'C',     el: 'C', x:    0, y:    0 },
    { key: 'H_top', el: 'H', x:    0, y: -150 },
    { key: 'H_br',  el: 'H', x: -150, y:    0 }, // the "lone H" attached to C
    // X1 = double-bonded O (top right)
    { key: 'X1',    el: 'O', x:  140, y:  -90, highlight: true },
    // New atom — single-bonded O (bottom right)
    { key: 'O2',    el: 'O', x:  140, y:   90, highlight: true },
    // the H attached to that O
    { key: 'H_oh',  el: 'H', x:  280, y:   90, highlight: true },
  ],
  bonds: [
    { from: 'C',  to: 'H_top', order: 1 },
    { from: 'C',  to: 'H_br',  order: 1 },
    { from: 'C',  to: 'X1',    order: 2, highlight: true },
    { from: 'C',  to: 'O2',    order: 1, highlight: true },
    { from: 'O2', to: 'H_oh',  order: 1, highlight: true },
  ],
};

// ── Stage 4: Methyl methanoate HCOOCH₃ ───────────────────────────────────
// Replace the H of the acid –OH with a CH₃.
const METHYL_METHANOATE: Stage = {
  name: 'Methyl methanoate',
  formula: 'HCOOCH₃',
  family: 'Ester',
  iupacSuffix: '-oate',
  caption: 'HCOOCH₃ · acid –OH replaced by –OCH₃ · the ester family · fruit smells, perfumes, fats',
  atoms: [
    { key: 'C',     el: 'C', x:    0, y:    0 },
    { key: 'H_top', el: 'H', x:    0, y: -150 },
    { key: 'H_br',  el: 'H', x: -150, y:    0 },
    { key: 'X1',    el: 'O', x:  140, y:  -90, highlight: true },
    { key: 'O2',    el: 'O', x:  140, y:   90, highlight: true },
    // H_oh slot becomes the methyl carbon
    { key: 'H_oh',  el: 'C', x:  300, y:   90, highlight: true },
    // 3 H's on the methyl
    { key: 'Hm1',   el: 'H', x:  430, y:   30, highlight: true },
    { key: 'Hm2',   el: 'H', x:  430, y:  150, highlight: true },
    { key: 'Hm3',   el: 'H', x:  300, y:  220, highlight: true },
  ],
  bonds: [
    { from: 'C',  to: 'H_top', order: 1 },
    { from: 'C',  to: 'H_br',  order: 1 },
    { from: 'C',  to: 'X1',    order: 2, highlight: true },
    { from: 'C',  to: 'O2',    order: 1, highlight: true },
    { from: 'O2', to: 'H_oh',  order: 1, highlight: true },
    { from: 'H_oh', to: 'Hm1', order: 1, highlight: true },
    { from: 'H_oh', to: 'Hm2', order: 1, highlight: true },
    { from: 'H_oh', to: 'Hm3', order: 1, highlight: true },
  ],
};

const STAGES: Stage[] = [METHANE, METHANOL, METHANAL, METHANOIC_ACID, METHYL_METHANOATE];

// ── Helpers ─────────────────────────────────────────────────────────────────
function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function stageInterp(frame: number): { fromIdx: number; toIdx: number; t: number } {
  if (frame < F_STAGE0_START) return { fromIdx: 0, toIdx: 0, t: 0 };
  if (frame < F_STAGE0_HOLD)  return { fromIdx: 0, toIdx: 0, t: 0 };
  if (frame < F_STAGE1_START) {
    const t = (frame - F_STAGE0_HOLD) / (F_STAGE1_START - F_STAGE0_HOLD);
    return { fromIdx: 0, toIdx: 1, t: easeInOut(t) };
  }
  if (frame < F_STAGE1_HOLD) return { fromIdx: 1, toIdx: 1, t: 0 };
  if (frame < F_STAGE2_START) {
    const t = (frame - F_STAGE1_HOLD) / (F_STAGE2_START - F_STAGE1_HOLD);
    return { fromIdx: 1, toIdx: 2, t: easeInOut(t) };
  }
  if (frame < F_STAGE2_HOLD) return { fromIdx: 2, toIdx: 2, t: 0 };
  if (frame < F_STAGE3_START) {
    const t = (frame - F_STAGE2_HOLD) / (F_STAGE3_START - F_STAGE2_HOLD);
    return { fromIdx: 2, toIdx: 3, t: easeInOut(t) };
  }
  if (frame < F_STAGE3_HOLD) return { fromIdx: 3, toIdx: 3, t: 0 };
  if (frame < F_STAGE4_START) {
    const t = (frame - F_STAGE3_HOLD) / (F_STAGE4_START - F_STAGE3_HOLD);
    return { fromIdx: 3, toIdx: 4, t: easeInOut(t) };
  }
  return { fromIdx: 4, toIdx: 4, t: 0 };
}

function atomColor(el: Element): string {
  switch (el) {
    case 'C': return PAI_THEME.colors.carbon;
    case 'O': return PAI_THEME.colors.oxygen;
    case 'H': return PAI_THEME.colors.hydrogen;
  }
}

function atomLabelColor(el: Element): string {
  return el === 'H' ? '#1a202c' : '#fff';
}

// Resolve an atom slot to a rendered position + opacity at frame t.
type ResolvedAtom = {
  key: string;
  el: Element;
  x: number;
  y: number;
  opacity: number;
  highlight: boolean;
};

function resolveAtom(
  key: string,
  from: Stage,
  to: Stage,
  t: number,
): ResolvedAtom | null {
  const a = from.atoms.find((x) => x.key === key) ?? null;
  const b = to.atoms.find((x) => x.key === key) ?? null;

  if (!a && !b) return null;

  if (a && b) {
    return {
      key,
      el: t < 0.5 ? a.el : b.el,
      x: lerp(a.x, b.x, t),
      y: lerp(a.y, b.y, t),
      opacity: 1,
      highlight: t < 0.5 ? !!a.highlight : !!b.highlight,
    };
  }
  if (a && !b) {
    return { key, el: a.el, x: a.x, y: a.y, opacity: 1 - t, highlight: !!a.highlight };
  }
  // a is null, b exists — fade in
  return { key: b!.key, el: b!.el, x: b!.x, y: b!.y, opacity: t, highlight: !!b!.highlight };
}

type ResolvedBond = {
  fromKey: string;
  toKey: string;
  order: 1 | 2;
  opacity: number;
  highlight: boolean;
};

function resolveBond(
  bond: BondSpec,
  presentInFrom: boolean,
  presentInTo: boolean,
  t: number,
): ResolvedBond {
  let opacity = 1;
  if (presentInFrom && !presentInTo) opacity = 1 - t;
  if (!presentInFrom && presentInTo) opacity = t;
  return { fromKey: bond.from, toKey: bond.to, order: bond.order, opacity, highlight: !!bond.highlight };
}

function bondsFor(stage: Stage): Set<string> {
  const set = new Set<string>();
  for (const b of stage.bonds) {
    const k1 = `${b.from}->${b.to}`;
    const k2 = `${b.to}->${b.from}`;
    set.add(k1);
    set.add(k2);
  }
  return set;
}

// ── Component ───────────────────────────────────────────────────────────────
export const FunctionalGroupsScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title intro
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  const { fromIdx, toIdx, t } = stageInterp(frame);
  const fromStage = STAGES[fromIdx];
  const toStage = STAGES[toIdx];

  // Combined set of slot keys
  const slotKeys = new Set<string>();
  fromStage.atoms.forEach((a) => slotKeys.add(a.key));
  toStage.atoms.forEach((a) => slotKeys.add(a.key));

  // Resolve all atoms
  const atoms: ResolvedAtom[] = [];
  slotKeys.forEach((k) => {
    const a = resolveAtom(k, fromStage, toStage, t);
    if (a) atoms.push(a);
  });
  const atomMap = new Map(atoms.map((a) => [a.key, a]));

  // Combined bond list
  const fromBondSet = bondsFor(fromStage);
  const toBondSet = bondsFor(toStage);
  const allBondsRaw: BondSpec[] = [...fromStage.bonds, ...toStage.bonds];
  // deduplicate by sorted (from,to,order) key
  const seen = new Set<string>();
  const allBonds: BondSpec[] = [];
  for (const b of allBondsRaw) {
    const k = `${[b.from, b.to].sort().join('|')}|${b.order}`;
    if (!seen.has(k)) { seen.add(k); allBonds.push(b); }
  }
  const resolvedBonds: ResolvedBond[] = allBonds.map((b) => {
    const inFrom = fromBondSet.has(`${b.from}->${b.to}`);
    const inTo = toBondSet.has(`${b.from}->${b.to}`);
    // bond order may differ between stages — pick whichever stage is "active" at t
    let order = b.order;
    if (inFrom && inTo) {
      const fromOrder = fromStage.bonds.find(
        (x) => (x.from === b.from && x.to === b.to) || (x.from === b.to && x.to === b.from),
      )?.order ?? b.order;
      const toOrder = toStage.bonds.find(
        (x) => (x.from === b.from && x.to === b.to) || (x.from === b.to && x.to === b.from),
      )?.order ?? b.order;
      order = (t < 0.5 ? fromOrder : toOrder) as 1 | 2;
    }
    const fromHighlight = fromStage.bonds.find(
      (x) => (x.from === b.from && x.to === b.to) || (x.from === b.to && x.to === b.from),
    )?.highlight;
    const toHighlight = toStage.bonds.find(
      (x) => (x.from === b.from && x.to === b.to) || (x.from === b.to && x.to === b.from),
    )?.highlight;
    return resolveBond(
      { ...b, order, highlight: t < 0.5 ? fromHighlight : toHighlight },
      inFrom,
      inTo,
      t,
    );
  });

  // Currently displayed metadata — flip at midpoint
  const showStage = t < 0.5 ? fromStage : toStage;

  // Stage entrance
  const moleculeOp = interpolate(
    frame,
    [F_TITLE_END, F_STAGE0_START],
    [0, 1],
    { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' },
  );

  // Summary panel
  const summaryOp = interpolate(
    frame,
    [F_SUMMARY_IN, F_SUMMARY_IN + 30],
    [0, 1],
    { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' },
  );

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
          Functional Groups — One Carbon, Five Families
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          Watch what changes as we add oxygen step by step. Same carbon — entirely different chemistry.
        </p>
      </div>

      {/* Molecule canvas */}
      <svg
        width={1920}
        height={1080}
        viewBox="0 0 1920 1080"
        style={{ position: 'absolute', inset: 0, opacity: moleculeOp }}
      >
        {/* Bonds first (under atoms) */}
        {resolvedBonds.map((b, i) => {
          if (b.opacity < 0.01) return null;
          const a = atomMap.get(b.fromKey);
          const c = atomMap.get(b.toKey);
          if (!a || !c) return null;
          const x1 = CX + a.x;
          const y1 = CY + a.y;
          const x2 = CX + c.x;
          const y2 = CY + c.y;
          const stroke = b.highlight ? PAI_THEME.colors.fgHighlight : PAI_THEME.colors.bond;
          if (b.order === 2) {
            // perpendicular offset for 2 lines
            const dx = x2 - x1;
            const dy = y2 - y1;
            const L = Math.sqrt(dx * dx + dy * dy) || 1;
            const px = -dy / L * 8;
            const py =  dx / L * 8;
            return (
              <g key={`b-${i}`} opacity={b.opacity}>
                <line x1={x1 + px} y1={y1 + py} x2={x2 + px} y2={y2 + py}
                  stroke={stroke} strokeWidth={6} strokeLinecap="round" />
                <line x1={x1 - px} y1={y1 - py} x2={x2 - px} y2={y2 - py}
                  stroke={stroke} strokeWidth={6} strokeLinecap="round" />
              </g>
            );
          }
          return (
            <line key={`b-${i}`} x1={x1} y1={y1} x2={x2} y2={y2}
              stroke={stroke} strokeWidth={6} strokeLinecap="round" opacity={b.opacity} />
          );
        })}

        {/* Atoms */}
        {atoms.map((a) => {
          if (a.opacity < 0.01) return null;
          const cx = CX + a.x;
          const cy = CY + a.y;
          const r = a.el === 'C' ? C_R : ATOM_R;
          const fill = atomColor(a.el);
          const stroke = a.highlight ? PAI_THEME.colors.fgHighlight : PAI_THEME.colors.text;
          const strokeWidth = a.highlight ? 5 : 3;
          return (
            <g key={`a-${a.key}`} opacity={a.opacity}>
              <circle cx={cx} cy={cy} r={r}
                fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
              <text x={cx} y={cy + (a.el === 'C' ? 14 : 10)}
                fontSize={a.el === 'C' ? 36 : 28}
                fontWeight={700}
                fill={atomLabelColor(a.el)}
                textAnchor="middle">
                {a.el}
              </text>
            </g>
          );
        })}

        {/* Family meta panel (top-left) */}
        <g>
          <rect x={80} y={140} width={460} height={220} rx={16}
            fill={PAI_THEME.colors.backgroundAlt}
            stroke={PAI_THEME.colors.accent}
            strokeWidth={2} />
          <text x={310} y={188} fontSize={22} fontWeight={600}
            fill={PAI_THEME.colors.textMuted} textAnchor="middle">
            current family
          </text>
          <text x={310} y={244} fontSize={52} fontWeight={700}
            fill={PAI_THEME.colors.fgHighlight} textAnchor="middle">
            {showStage.family}
          </text>
          <text x={310} y={290} fontSize={32} fontWeight={700}
            fill={PAI_THEME.colors.text} textAnchor="middle">
            {showStage.formula}
          </text>
          <text x={310} y={328} fontSize={22}
            fill={PAI_THEME.colors.textMuted} textAnchor="middle">
            IUPAC suffix: {showStage.iupacSuffix}
          </text>
        </g>

        {/* Step counter (top-right) */}
        <g>
          <rect x={1380} y={140} width={460} height={140} rx={16}
            fill={PAI_THEME.colors.backgroundAlt}
            stroke={PAI_THEME.colors.accent}
            strokeWidth={2} />
          <text x={1610} y={188} fontSize={22} fontWeight={600}
            fill={PAI_THEME.colors.textMuted} textAnchor="middle">
            stage
          </text>
          <text x={1610} y={252} fontSize={56} fontWeight={700}
            fill={PAI_THEME.colors.accentLight} textAnchor="middle">
            {Math.min(toIdx + 1, STAGES.length)} / {STAGES.length}
          </text>
        </g>
      </svg>

      {/* Caption */}
      <div style={{
        position: 'absolute', top: 970, left: 0, right: 0, textAlign: 'center',
        fontSize: 30, fontWeight: 700,
        color: PAI_THEME.colors.text,
        opacity: moleculeOp,
        padding: '0 80px',
      }}>
        {showStage.caption}
      </div>

      {/* Summary overlay (last 2 s) */}
      {summaryOp > 0 && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(15, 23, 42, 0.86)',
          opacity: summaryOp,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexDirection: 'column', gap: 24,
        }}>
          <div style={{ fontSize: 56, fontWeight: 700, color: PAI_THEME.colors.text }}>
            One carbon · five worlds.
          </div>
          <div style={{ fontSize: 36, color: PAI_THEME.colors.accentLight, marginTop: 8 }}>
            alkane → alcohol → aldehyde → acid → ester
          </div>
          <div style={{
            fontSize: 26, color: PAI_THEME.colors.textMuted,
            maxWidth: 1280, textAlign: 'center', lineHeight: 1.5,
          }}>
            Each functional group brings new reactivity — same skeleton, new chemistry. That's
            why "functional group" is the most useful idea in organic chemistry.
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
