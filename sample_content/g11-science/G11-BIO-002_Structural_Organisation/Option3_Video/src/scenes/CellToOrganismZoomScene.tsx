/**
 * CellToOrganismZoomScene — Animated zoom from a whole human silhouette
 * down through the levels of biological organisation:
 *
 *   Organism (human silhouette)
 *      → Organ system (chest with circulatory tracery)
 *      → Organ (heart)
 *      → Tissue (cardiac muscle bundle)
 *      → Cell (single branched cardiac myocyte)
 *      → Nucleus (centre of the cell)
 *
 * Visual metaphor: a single "subject" — the chest of one person — is held
 * stationary on stage while the camera plunges into it, with each landing
 * revealing the next deeper structural level. A persistent ladder on the
 * left tracks how far we've zoomed; the active rung pulses.
 *
 * Frames @ 30fps (28 s total = 840 frames):
 *   0–60       Title fades in
 *   60–180     Level 5: Organism — full human silhouette
 *   180–300    Level 4: Organ system — chest with vessels
 *   300–420    Level 3: Organ — labelled heart
 *   420–540    Level 2: Tissue — cardiac muscle bundle
 *   540–680    Level 1: Cell — single cardiac myocyte
 *   680–780    Drill-in: Nucleus — DNA inside the cell
 *   780–840    Closing caption fades in
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Level data ────────────────────────────────────────────────────────────
type Level = {
  rank: number;        // 5 = organism, 4 = system, 3 = organ, 2 = tissue, 1 = cell, 0 = nucleus
  name: string;
  example: string;
  hint: string;
  color: string;
  // Approximate scale label, decorative
  scaleLabel: string;
};

const LEVELS: Level[] = [
  { rank: 5, name: 'Organism',     example: 'Human',                   hint: 'all systems integrated',           color: PAI_THEME.colors.organism, scaleLabel: '~1.7 m' },
  { rank: 4, name: 'Organ system', example: 'Circulatory system',      hint: 'organs cooperating',               color: PAI_THEME.colors.system,   scaleLabel: '~1 m' },
  { rank: 3, name: 'Organ',        example: 'Heart',                   hint: 'multiple tissues, one job',        color: PAI_THEME.colors.organ,    scaleLabel: '~12 cm' },
  { rank: 2, name: 'Tissue',       example: 'Cardiac muscle',          hint: 'similar cells, shared function',   color: PAI_THEME.colors.tissue,   scaleLabel: '~1 mm' },
  { rank: 1, name: 'Cell',         example: 'Cardiac myocyte',         hint: 'basic unit of life',               color: PAI_THEME.colors.cell,     scaleLabel: '~100 μm' },
  { rank: 0, name: 'Nucleus',      example: 'DNA inside myocyte',      hint: 'control centre — genes live here', color: PAI_THEME.colors.monera,   scaleLabel: '~6 μm' },
];

// Frame anchors — 30 fps.
const F_TITLE_END = 60;
const F_PER_LEVEL = 120;       // 4 s each for the first 5 levels
const F_NUCLEUS_DURATION = 100;
const F_CAPTION_START = F_TITLE_END + 5 * F_PER_LEVEL + F_NUCLEUS_DURATION; // = 760
const F_CAPTION_END = F_CAPTION_START + 60;

const W = 1920;
const H = 1080;

// Stage / camera layout
const STAGE_CX = 1100;          // centre of the zoom subject
const STAGE_CY = 540;
const STAGE_R = 380;            // circular viewport radius

// ── Helpers ───────────────────────────────────────────────────────────────
const getActiveLevel = (frame: number): { idx: number; t: number } => {
  const elapsed = Math.max(0, frame - F_TITLE_END);
  if (elapsed < 5 * F_PER_LEVEL) {
    const idx = Math.min(4, Math.floor(elapsed / F_PER_LEVEL));
    return { idx, t: (elapsed - idx * F_PER_LEVEL) / F_PER_LEVEL };
  }
  // Nucleus phase (idx 5)
  const e = elapsed - 5 * F_PER_LEVEL;
  return { idx: 5, t: Math.min(1, e / F_NUCLEUS_DURATION) };
};

// Each level reveal opacity — fades in over the first 30 frames of its window.
const levelOpacity = (frame: number, idx: number): number => {
  const { idx: cur } = getActiveLevel(frame);
  if (idx > cur) return 0;
  if (idx < cur) {
    // Cross-fade out as the next level fades in (over 20 frames at the boundary).
    const nextStart = F_TITLE_END + (idx + 1) * F_PER_LEVEL;
    return interpolate(frame, [nextStart, nextStart + 20], [1, 0], {
      extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    });
  }
  // idx === cur: fade in.
  const start = F_TITLE_END + idx * F_PER_LEVEL;
  return interpolate(frame, [start, start + 30], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
};

// ── Scene-specific renderers (each level draws a centred SVG sub-figure) ─

const HumanSilhouette: React.FC = () => (
  <g transform={`translate(${STAGE_CX}, ${STAGE_CY})`}>
    {/* Body silhouette — proportional, anatomical-ish */}
    <path
      d="M 0 -260 Q 36 -260 36 -224 Q 36 -200 22 -190 L 30 -150 L 90 -110 L 110 60 L 96 200 L 50 200 L 36 100 L 0 100 L -36 100 L -50 200 L -96 200 L -110 60 L -90 -110 L -30 -150 L -22 -190 Q -36 -200 -36 -224 Q -36 -260 0 -260 Z"
      fill={PAI_THEME.colors.accentLight}
      stroke={PAI_THEME.colors.organism}
      strokeWidth={5}
    />
    {/* Chest highlight — the region we'll zoom into */}
    <circle cx={0} cy={-30} r={70} fill="none" stroke={PAI_THEME.colors.error} strokeWidth={4} strokeDasharray="10 6" />
    <text x={0} y={-110} fill={PAI_THEME.colors.error} fontSize={22} fontWeight={700} textAnchor="middle">
      zoom target
    </text>
  </g>
);

const CirculatorySystem: React.FC = () => (
  <g transform={`translate(${STAGE_CX}, ${STAGE_CY})`}>
    {/* Torso outline */}
    <path
      d="M -160 -260 Q -150 -240 -130 -210 L -110 60 L -100 240 L 100 240 L 110 60 L 130 -210 Q 150 -240 160 -260 L 80 -260 L 0 -240 L -80 -260 Z"
      fill={PAI_THEME.colors.accentLight}
      stroke={PAI_THEME.colors.system}
      strokeWidth={4}
      opacity={0.5}
    />
    {/* Heart icon (centred) */}
    <path
      d="M 0 -60 Q -30 -100 -70 -80 Q -110 -50 -90 0 Q -60 60 0 110 Q 60 60 90 0 Q 110 -50 70 -80 Q 30 -100 0 -60 Z"
      fill={PAI_THEME.colors.tissue}
      stroke={PAI_THEME.colors.cell}
      strokeWidth={4}
    />
    {/* Aorta arch */}
    <path d="M -10 -90 Q -20 -160 40 -180 Q 100 -180 100 -120" fill="none" stroke={PAI_THEME.colors.tissue} strokeWidth={14} />
    {/* SVC + IVC (blue) */}
    <line x1={-50} y1={-200} x2={-50} y2={-90} stroke={PAI_THEME.colors.organism} strokeWidth={14} />
    <line x1={-50} y1={120} x2={-50} y2={220} stroke={PAI_THEME.colors.organism} strokeWidth={14} />
    {/* Vascular tracery — arteries (red) */}
    <g stroke={PAI_THEME.colors.tissue} strokeWidth={4} fill="none">
      <path d="M 90 0 Q 130 30 150 80 Q 160 140 150 220" />
      <path d="M 60 60 Q 110 100 130 180" />
      <path d="M -90 0 Q -130 30 -150 80 Q -160 140 -150 220" />
      <path d="M -60 60 Q -110 100 -130 180" />
      <path d="M 60 -100 Q 110 -160 140 -240" />
      <path d="M -60 -100 Q -110 -160 -140 -240" />
    </g>
    {/* Veins (blue) */}
    <g stroke={PAI_THEME.colors.organism} strokeWidth={3} fill="none">
      <path d="M 100 -10 Q 140 20 160 80 Q 170 140 160 220" />
      <path d="M -100 -10 Q -140 20 -160 80 Q -170 140 -160 220" />
    </g>
    <text x={0} y={170} fill={PAI_THEME.colors.tissue} fontSize={20} fontWeight={700} textAnchor="middle">
      heart at the centre
    </text>
  </g>
);

const HeartOrgan: React.FC = () => (
  <g transform={`translate(${STAGE_CX}, ${STAGE_CY})`}>
    {/* Aorta */}
    <path d="M -20 -180 Q -20 -300 80 -300 Q 180 -300 180 -180" fill="none" stroke={PAI_THEME.colors.tissue} strokeWidth={26} />
    {/* SVC + pulmonary artery */}
    <line x1={-150} y1={-300} x2={-150} y2={-160} stroke={PAI_THEME.colors.organism} strokeWidth={20} />
    <path d="M -60 -180 Q -60 -260 -110 -260" fill="none" stroke={PAI_THEME.colors.organism} strokeWidth={18} />
    {/* Heart silhouette */}
    <path
      d="M -180 -160 L -180 100 Q -150 220 0 240 Q 200 220 200 80 L 200 -160 Q 100 -210 0 -160 Q -120 -210 -180 -160 Z"
      fill={PAI_THEME.colors.accentLight}
      stroke={PAI_THEME.colors.cell}
      strokeWidth={5}
    />
    {/* Septum */}
    <line x1={0} y1={-140} x2={0} y2={220} stroke={PAI_THEME.colors.cell} strokeWidth={4} />
    {/* Right atrium */}
    <text x={-90} y={-50} fill={PAI_THEME.colors.organism} fontSize={22} fontWeight={700} textAnchor="middle">RA</text>
    {/* Left atrium */}
    <text x={90} y={-50} fill={PAI_THEME.colors.tissue} fontSize={22} fontWeight={700} textAnchor="middle">LA</text>
    {/* Right ventricle */}
    <text x={-80} y={130} fill={PAI_THEME.colors.organism} fontSize={22} fontWeight={700} textAnchor="middle">RV</text>
    {/* Left ventricle */}
    <text x={100} y={130} fill={PAI_THEME.colors.tissue} fontSize={22} fontWeight={700} textAnchor="middle">LV</text>
    {/* AV boundary */}
    <line x1={-180} y1={0} x2={200} y2={0} stroke={PAI_THEME.colors.cell} strokeWidth={3} strokeDasharray="6 4" />
    {/* Zoom-in target — wall of the LV */}
    <circle cx={140} cy={120} r={42} fill="none" stroke={PAI_THEME.colors.error} strokeWidth={4} strokeDasharray="8 5" />
    <text x={140} y={210} fill={PAI_THEME.colors.error} fontSize={18} fontWeight={700} textAnchor="middle">
      next zoom →
    </text>
  </g>
);

const CardiacTissue: React.FC = () => (
  <g transform={`translate(${STAGE_CX}, ${STAGE_CY})`}>
    {/* Cardiac muscle bundle — branched cells, intercalated discs, single central nuclei */}
    {/* Row 1 */}
    <path d="M -300 -180 Q -260 -210 -180 -200 Q -120 -195 -110 -160 Q -120 -125 -180 -120 Q -250 -125 -300 -150 Z"
          fill={PAI_THEME.colors.warmWash} stroke={PAI_THEME.colors.cell} strokeWidth={3.5} />
    <path d="M -110 -160 Q -50 -210 50 -200 Q 110 -195 130 -160 Q 110 -125 50 -120 Q -50 -125 -110 -130 Z"
          fill={PAI_THEME.colors.warmWash} stroke={PAI_THEME.colors.cell} strokeWidth={3.5} />
    <path d="M 130 -160 Q 200 -210 290 -200 Q 340 -180 320 -140 Q 270 -120 200 -125 Q 140 -130 130 -150 Z"
          fill={PAI_THEME.colors.warmWash} stroke={PAI_THEME.colors.cell} strokeWidth={3.5} />
    {/* Row 2 */}
    <path d="M -300 -50 Q -260 -90 -180 -75 Q -120 -65 -110 -30 Q -120 0 -180 5 Q -260 0 -300 -20 Z"
          fill={PAI_THEME.colors.warmWash} stroke={PAI_THEME.colors.cell} strokeWidth={3.5} />
    <path d="M -110 -30 Q -50 -90 50 -75 Q 110 -65 130 -30 Q 110 0 50 5 Q -50 0 -110 0 Z"
          fill={PAI_THEME.colors.warmWash} stroke={PAI_THEME.colors.cell} strokeWidth={3.5} />
    <path d="M 130 -30 Q 200 -90 290 -75 Q 340 -55 320 -10 Q 270 5 200 0 Q 140 -5 130 -20 Z"
          fill={PAI_THEME.colors.warmWash} stroke={PAI_THEME.colors.cell} strokeWidth={3.5} />
    {/* Row 3 */}
    <path d="M -300 80 Q -260 50 -180 60 Q -120 70 -110 105 Q -120 140 -180 145 Q -260 140 -300 110 Z"
          fill={PAI_THEME.colors.warmWash} stroke={PAI_THEME.colors.cell} strokeWidth={3.5} />
    <path d="M -110 105 Q -50 50 50 65 Q 110 75 130 105 Q 110 140 50 145 Q -50 140 -110 135 Z"
          fill={PAI_THEME.colors.warmWash} stroke={PAI_THEME.colors.cell} strokeWidth={3.5} />
    <path d="M 130 105 Q 200 50 290 65 Q 340 90 320 130 Q 270 145 200 140 Q 140 135 130 125 Z"
          fill={PAI_THEME.colors.warmWash} stroke={PAI_THEME.colors.cell} strokeWidth={3.5} />

    {/* Intercalated discs */}
    <line x1={-110} y1={-170} x2={-110} y2={-130} stroke={PAI_THEME.colors.cell} strokeWidth={6} />
    <line x1={130} y1={-170} x2={130} y2={-130} stroke={PAI_THEME.colors.cell} strokeWidth={6} />
    <line x1={-110} y1={-40} x2={-110} y2={0} stroke={PAI_THEME.colors.cell} strokeWidth={6} />
    <line x1={130} y1={-40} x2={130} y2={0} stroke={PAI_THEME.colors.cell} strokeWidth={6} />
    <line x1={-110} y1={90} x2={-110} y2={140} stroke={PAI_THEME.colors.cell} strokeWidth={6} />
    <line x1={130} y1={90} x2={130} y2={140} stroke={PAI_THEME.colors.cell} strokeWidth={6} />

    {/* Single central nuclei */}
    {[
      [-220, -160], [10, -160], [220, -160],
      [-220, -25], [10, -25], [220, -25],
      [-220, 105], [10, 105], [220, 105],
    ].map(([x, y], i) => (
      <ellipse key={i} cx={x} cy={y} rx={14} ry={9} fill={PAI_THEME.colors.cell} />
    ))}

    {/* Zoom-in target on the centre cell */}
    <circle cx={10} cy={-25} r={64} fill="none" stroke={PAI_THEME.colors.error} strokeWidth={4} strokeDasharray="8 5" />
    <text x={10} y={210} fill={PAI_THEME.colors.error} fontSize={18} fontWeight={700} textAnchor="middle">
      one cell next →
    </text>
  </g>
);

const CardiacCell: React.FC = () => (
  <g transform={`translate(${STAGE_CX}, ${STAGE_CY})`}>
    {/* One branched cardiac myocyte — large, centred */}
    <path
      d="M -340 -40 Q -320 -160 -180 -150 Q -50 -150 -10 -50 Q 60 -160 220 -130 Q 320 -90 290 30 Q 320 130 200 160 Q 80 200 -20 110 Q -80 200 -200 160 Q -310 130 -340 40 Z"
      fill={PAI_THEME.colors.warmWash}
      stroke={PAI_THEME.colors.cell}
      strokeWidth={5}
    />
    {/* Striations (faint) */}
    <g stroke={PAI_THEME.colors.cell} strokeWidth={1.4} opacity={0.7}>
      <line x1={-280} y1={-100} x2={-260} y2={130} />
      <line x1={-220} y1={-130} x2={-200} y2={150} />
      <line x1={-160} y1={-140} x2={-140} y2={160} />
      <line x1={-100} y1={-145} x2={-80} y2={170} />
      <line x1={-40} y1={-140} x2={-20} y2={170} />
      <line x1={20} y1={-140} x2={40} y2={170} />
      <line x1={80} y1={-130} x2={100} y2={160} />
      <line x1={140} y1={-110} x2={160} y2={140} />
      <line x1={200} y1={-90} x2={220} y2={130} />
      <line x1={260} y1={-50} x2={270} y2={100} />
    </g>
    {/* Single central nucleus (highlighted) */}
    <ellipse cx={20} cy={20} rx={56} ry={36} fill={PAI_THEME.colors.cell} stroke={PAI_THEME.colors.tissue} strokeWidth={4} />
    {/* Nucleolus inside */}
    <circle cx={20} cy={20} r={14} fill={PAI_THEME.colors.text} opacity={0.5} />

    {/* Zoom target — the nucleus */}
    <circle cx={20} cy={20} r={70} fill="none" stroke={PAI_THEME.colors.error} strokeWidth={4} strokeDasharray="8 5" />
    <text x={20} y={120} fill={PAI_THEME.colors.error} fontSize={20} fontWeight={700} textAnchor="middle">
      into the nucleus →
    </text>

    {/* Annotations */}
    <line x1={-200} y1={-120} x2={-380} y2={-220} stroke={PAI_THEME.colors.cell} strokeWidth={2} />
    <text x={-380} y={-228} fill={PAI_THEME.colors.cell} fontSize={20} fontWeight={700} textAnchor="end">
      branched
    </text>
    <line x1={140} y1={-100} x2={300} y2={-220} stroke={PAI_THEME.colors.cell} strokeWidth={2} />
    <text x={300} y={-228} fill={PAI_THEME.colors.cell} fontSize={20} fontWeight={700}>
      striated
    </text>
  </g>
);

const Nucleus: React.FC<{ progress: number }> = ({ progress }) => {
  // Nucleus expands and a stylised DNA helix unspools at progress > 0.4
  const size = interpolate(progress, [0, 0.5], [80, 320], { extrapolateRight: 'clamp' });
  const dnaOp = interpolate(progress, [0.4, 1], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <g transform={`translate(${STAGE_CX}, ${STAGE_CY})`}>
      {/* Nuclear envelope */}
      <circle cx={0} cy={0} r={size} fill={PAI_THEME.colors.coolWash} stroke={PAI_THEME.colors.monera} strokeWidth={6} />
      <circle cx={0} cy={0} r={size - 10} fill="none" stroke={PAI_THEME.colors.monera} strokeWidth={2} strokeDasharray="3 4" />
      {/* Nuclear pores (small dots around the rim) */}
      {Array.from({ length: 18 }).map((_, i) => {
        const a = (i / 18) * Math.PI * 2;
        return (
          <circle
            key={i}
            cx={Math.cos(a) * size}
            cy={Math.sin(a) * size}
            r={5}
            fill={PAI_THEME.colors.background}
            stroke={PAI_THEME.colors.monera}
            strokeWidth={2}
          />
        );
      })}
      {/* Nucleolus */}
      <circle cx={0} cy={0} r={Math.max(20, size * 0.18)} fill={PAI_THEME.colors.monera} opacity={0.6} />

      {/* DNA double helix — two interleaved sine waves with rungs */}
      <g opacity={dnaOp} transform={`translate(${-size * 0.7}, 0)`}>
        {Array.from({ length: 24 }).map((_, i) => {
          const x = i * (size * 1.4 / 24);
          const yA = Math.sin(i * 0.6) * 28;
          const yB = -Math.sin(i * 0.6) * 28;
          return (
            <g key={i}>
              <line x1={x} y1={yA} x2={x} y2={yB} stroke={PAI_THEME.colors.accentMuted} strokeWidth={2} />
              <circle cx={x} cy={yA} r={4} fill={PAI_THEME.colors.error} />
              <circle cx={x} cy={yB} r={4} fill={PAI_THEME.colors.info} />
            </g>
          );
        })}
        {/* Two backbone curves */}
        <path
          d={`M 0 0 ${Array.from({ length: 24 }).map((_, i) => `L ${i * (size * 1.4 / 24)} ${Math.sin(i * 0.6) * 28}`).join(' ')}`}
          fill="none"
          stroke={PAI_THEME.colors.error}
          strokeWidth={3}
        />
        <path
          d={`M 0 0 ${Array.from({ length: 24 }).map((_, i) => `L ${i * (size * 1.4 / 24)} ${-Math.sin(i * 0.6) * 28}`).join(' ')}`}
          fill="none"
          stroke={PAI_THEME.colors.info}
          strokeWidth={3}
        />
      </g>

      <text x={0} y={size + 50} fill={PAI_THEME.colors.text} fontSize={26} fontWeight={700} textAnchor="middle">
        DNA — the cell&apos;s instructions
      </text>
    </g>
  );
};

// ── Main scene ───────────────────────────────────────────────────────────
export const CellToOrganismZoomScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleSpring = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  const { idx: activeIdx, t: activeT } = getActiveLevel(frame);

  const captionOp = interpolate(
    frame,
    [F_CAPTION_START, F_CAPTION_END],
    [0, 1],
    { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' },
  );

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      {/* ── Title ─────────────────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 30, left: 0, right: 0, textAlign: 'center',
      }}>
        <h1 style={{
          fontSize: 56, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleSpring})`,
        }}>
          From Whole Body to Single Cell
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          Six steps zoom from one human all the way down to the DNA inside a heart-muscle cell.
        </p>
      </div>

      {/* ── Ladder of levels (left side) ──────────────────────── */}
      <svg
        width={W} height={H} viewBox={`0 0 ${W} ${H}`}
        style={{ position: 'absolute', inset: 0 }}
      >
        {/* Backbone */}
        <line
          x1={120}
          y1={180}
          x2={120}
          y2={180 + LEVELS.length * 110}
          stroke={PAI_THEME.colors.textDark}
          strokeWidth={3}
        />
        <text
          x={70}
          y={420}
          fill={PAI_THEME.colors.textMuted}
          fontSize={20}
          fontWeight={700}
          textAnchor="middle"
          transform={`rotate(-90 70 420)`}
        >
          large → small
        </text>

        {LEVELS.map((lvl, i) => {
          const yTop = 180 + i * 110;
          const revealStart = F_TITLE_END + (i === 5 ? 5 * F_PER_LEVEL : i * F_PER_LEVEL);
          const revealEnd = revealStart + 30;

          const rowOp = interpolate(
            frame, [revealStart, revealEnd], [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );

          // Active rung pulses
          const pulse = i === activeIdx
            ? interpolate(
                activeT, [0, 0.2, 1], [1.0, 1.08, 1.0],
                { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
              )
            : 1.0;

          const cx = 130;
          const cy = yTop + 38;

          return (
            <g key={lvl.name} opacity={rowOp}>
              <g transform={`translate(${cx}, ${cy}) scale(${pulse}) translate(${-cx}, ${-cy})`}>
                <rect
                  x={70}
                  y={yTop}
                  width={520}
                  height={86}
                  rx={10}
                  fill={lvl.color}
                  opacity={i === activeIdx ? 0.28 : 0.12}
                  stroke={lvl.color}
                  strokeWidth={i === activeIdx ? 4 : 2}
                />
                <text
                  x={92}
                  y={yTop + 30}
                  fill={lvl.color}
                  fontSize={22}
                  fontWeight={700}
                >
                  {`Level ${lvl.rank}`}
                </text>
                <text
                  x={92}
                  y={yTop + 60}
                  fill={PAI_THEME.colors.text}
                  fontSize={28}
                  fontWeight={700}
                >
                  {lvl.name}
                </text>
                <text
                  x={92}
                  y={yTop + 80}
                  fill={PAI_THEME.colors.textMuted}
                  fontSize={14}
                  fontStyle="italic"
                >
                  {lvl.hint}
                </text>
                <text
                  x={580}
                  y={yTop + 30}
                  fill={lvl.color}
                  fontSize={16}
                  fontWeight={700}
                  textAnchor="end"
                >
                  {lvl.scaleLabel}
                </text>
                <text
                  x={580}
                  y={yTop + 60}
                  fill={PAI_THEME.colors.text}
                  fontSize={20}
                  textAnchor="end"
                >
                  {lvl.example}
                </text>
              </g>
            </g>
          );
        })}

        {/* ── Stage viewport (right) ──────────────────────────── */}
        {/* Outer viewport ring */}
        <circle
          cx={STAGE_CX}
          cy={STAGE_CY}
          r={STAGE_R}
          fill={PAI_THEME.colors.backgroundDark}
          stroke={LEVELS[activeIdx].color}
          strokeWidth={6}
        />
        {/* Clipping mask so each level's drawing is constrained to the viewport */}
        <defs>
          <clipPath id="stageClip">
            <circle cx={STAGE_CX} cy={STAGE_CY} r={STAGE_R - 4} />
          </clipPath>
        </defs>

        <g clipPath="url(#stageClip)">
          {/* Each level renders, scaled in based on its level transition */}
          <g opacity={levelOpacity(frame, 0)} transform={`translate(${(1 - 1) * 0}, 0) scale(${interpolate(frame, [F_TITLE_END, F_TITLE_END + 30], [0.7, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })})`} style={{ transformOrigin: `${STAGE_CX}px ${STAGE_CY}px`, transformBox: 'fill-box' }}>
            <HumanSilhouette />
          </g>

          <g opacity={levelOpacity(frame, 1)}>
            <CirculatorySystem />
          </g>

          <g opacity={levelOpacity(frame, 2)}>
            <HeartOrgan />
          </g>

          <g opacity={levelOpacity(frame, 3)}>
            <CardiacTissue />
          </g>

          <g opacity={levelOpacity(frame, 4)}>
            <CardiacCell />
          </g>

          <g opacity={levelOpacity(frame, 5)}>
            <Nucleus progress={activeIdx === 5 ? activeT : 0} />
          </g>
        </g>

        {/* Stage caption */}
        <text
          x={STAGE_CX}
          y={STAGE_CY - STAGE_R - 30}
          fill={LEVELS[activeIdx].color}
          fontSize={28}
          fontWeight={700}
          textAnchor="middle"
        >
          {LEVELS[activeIdx].example}
        </text>
        <text
          x={STAGE_CX}
          y={STAGE_CY + STAGE_R + 40}
          fill={PAI_THEME.colors.textMuted}
          fontSize={20}
          textAnchor="middle"
        >
          {LEVELS[activeIdx].scaleLabel}
        </text>
      </svg>

      {/* ── Closing caption ───────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 990, left: 0, right: 0, textAlign: 'center',
        fontSize: 28, fontWeight: 700,
        color: PAI_THEME.colors.text,
        opacity: captionOp,
      }}>
        Same body, six magnifications. Each level is built from the level below.
      </div>
    </AbsoluteFill>
  );
};
