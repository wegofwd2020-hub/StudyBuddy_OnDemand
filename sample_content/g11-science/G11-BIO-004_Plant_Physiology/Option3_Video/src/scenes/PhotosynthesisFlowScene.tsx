/**
 * PhotosynthesisFlowScene — Animated photosynthesis pipeline.
 *
 * Visual journey (32 s @ 30 fps = 960 frames):
 *
 *   0–60      Title fades in: "Photosynthesis — the engine of life"
 *   60–180    Stage 1: Sunlight hits a chloroplast
 *                photons rain down · chloroplast appears centre-stage
 *   180–360   Stage 2: Light reactions on the thylakoid membrane
 *                water (H2O) is split → O2 escapes upward
 *                ATP + NADPH icons appear and stack on the right
 *   360–540   Stage 3: Calvin cycle in the stroma
 *                CO2 enters from the air
 *                a circular cycle indicator turns 3 times
 *                ATP + NADPH are consumed (icons drain)
 *                G3P emerges
 *   540–720   Stage 4: G3P → glucose → starch
 *                G3P merges into a glucose ring → starch grain forms
 *   720–870   Summary equation tile fades in:
 *                6 CO2 + 6 H2O + light → C6H12O6 + 6 O2
 *   870–960   Closing tagline + chloroplast pulse
 *
 * Visual metaphor: a single chloroplast holds centre stage. The sunlit upper-half
 * is the thylakoid membrane (light reactions); the lower stroma half hosts a
 * spinning Calvin-cycle ring. Inputs (light, H2O, CO2) flow IN from the left/top;
 * outputs (O2, glucose, starch) flow OUT to the right/bottom. ATP/NADPH ferry
 * energy from top half to bottom half — the visual "shaft" of the energy pipeline.
 */
import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from 'remotion';
import { PAI_THEME } from '../theme';

const W = 1920;
const H = 1080;

// ── Frame anchors ───────────────────────────────────────────────────────
const F_TITLE_END = 60;
const F_S1_START = 60;
const F_S1_END = 180;       // photons strike chloroplast
const F_S2_START = 180;
const F_S2_END = 360;       // light reactions: water split, ATP+NADPH made
const F_S3_START = 360;
const F_S3_END = 540;       // Calvin cycle
const F_S4_START = 540;
const F_S4_END = 720;       // glucose + starch
const F_EQ_START = 720;
const F_EQ_END = 870;       // summary equation
const F_OUTRO_START = 870;

// Stage centre — the chloroplast lives here for the whole video
const CHLORO_CX = 960;
const CHLORO_CY = 560;
const CHLORO_RX = 360;
const CHLORO_RY = 200;

// ── Helpers ─────────────────────────────────────────────────────────────
const fadeIn = (frame: number, start: number, dur: number) =>
  interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

const fadeOut = (frame: number, start: number, dur: number) =>
  interpolate(frame, [start, start + dur], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

const stageOpacity = (frame: number, start: number, end: number, fadeFrames = 20): number => {
  if (frame < start - fadeFrames) return 0;
  if (frame > end + fadeFrames) return 0;
  if (frame < start) return fadeIn(frame, start - fadeFrames, fadeFrames);
  if (frame > end) return fadeOut(frame, end, fadeFrames);
  return 1;
};

// ── Sub-components ──────────────────────────────────────────────────────

/** The persistent chloroplast — drawn for the entire video. */
const Chloroplast: React.FC<{ frame: number }> = ({ frame }) => {
  // Slight pulse during light-reaction phase
  const pulseT = Math.max(0, Math.min(1, (frame - F_S2_START) / 60));
  const pulse = 1 + 0.02 * Math.sin(pulseT * Math.PI * 4);

  return (
    <g transform={`translate(${CHLORO_CX}, ${CHLORO_CY}) scale(${pulse}) translate(${-CHLORO_CX}, ${-CHLORO_CY})`}>
      {/* Outer envelope */}
      <ellipse
        cx={CHLORO_CX}
        cy={CHLORO_CY}
        rx={CHLORO_RX}
        ry={CHLORO_RY}
        fill={PAI_THEME.colors.chloroplastBody}
        stroke={PAI_THEME.colors.chloroplastDark}
        strokeWidth={6}
        opacity={0.9}
      />
      {/* Inner envelope */}
      <ellipse
        cx={CHLORO_CX}
        cy={CHLORO_CY}
        rx={CHLORO_RX - 14}
        ry={CHLORO_RY - 12}
        fill={PAI_THEME.colors.stroma}
        stroke={PAI_THEME.colors.accentDark}
        strokeWidth={2}
      />

      {/* Grana (stacks of thylakoids) — three stacks distributed across stroma */}
      {[
        { x: CHLORO_CX - 200, y: CHLORO_CY - 30, n: 5 },
        { x: CHLORO_CX - 60, y: CHLORO_CY - 50, n: 6 },
        { x: CHLORO_CX + 80, y: CHLORO_CY - 30, n: 5 },
        { x: CHLORO_CX + 220, y: CHLORO_CY - 20, n: 4 },
      ].map((g, i) => (
        <g key={i}>
          {Array.from({ length: g.n }).map((_, j) => (
            <ellipse
              key={j}
              cx={g.x}
              cy={g.y + j * 14}
              rx={42}
              ry={7}
              fill={PAI_THEME.colors.thylakoid}
              stroke={PAI_THEME.colors.chloroplastDark}
              strokeWidth={1.2}
            />
          ))}
        </g>
      ))}

      {/* Stroma lamellae connecting grana */}
      <path
        d={`M ${CHLORO_CX - 200} ${CHLORO_CY - 10} Q ${CHLORO_CX - 130} ${CHLORO_CY + 10} ${CHLORO_CX - 60} ${CHLORO_CY - 30}`}
        fill="none"
        stroke={PAI_THEME.colors.thylakoid}
        strokeWidth={5}
      />
      <path
        d={`M ${CHLORO_CX - 60} ${CHLORO_CY + 10} Q ${CHLORO_CX + 10} ${CHLORO_CY + 30} ${CHLORO_CX + 80} ${CHLORO_CY - 10}`}
        fill="none"
        stroke={PAI_THEME.colors.thylakoid}
        strokeWidth={5}
      />
      <path
        d={`M ${CHLORO_CX + 80} ${CHLORO_CY + 30} Q ${CHLORO_CX + 150} ${CHLORO_CY + 50} ${CHLORO_CX + 220} ${CHLORO_CY + 20}`}
        fill="none"
        stroke={PAI_THEME.colors.thylakoid}
        strokeWidth={5}
      />

      {/* Chloroplast label always visible (subtle) */}
      <text
        x={CHLORO_CX}
        y={CHLORO_CY + CHLORO_RY + 50}
        fill={PAI_THEME.colors.accentLight}
        fontSize={28}
        fontWeight={700}
        textAnchor="middle"
        opacity={frame > F_S1_END - 30 ? 1 : 0}
      >
        chloroplast
      </text>
    </g>
  );
};

/** Photons raining down from upper-left — Stage 1. */
const Sunlight: React.FC<{ frame: number; opacity: number }> = ({ frame, opacity }) => {
  if (opacity <= 0) return null;
  const t = (frame - F_S1_START) / 30; // animation time

  return (
    <g opacity={opacity}>
      {/* Sun in upper-left */}
      <circle cx={220} cy={180} r={70} fill={PAI_THEME.colors.sunlightHot} />
      <circle cx={220} cy={180} r={50} fill={PAI_THEME.colors.sunlight} />
      {/* Sun rays */}
      {Array.from({ length: 12 }).map((_, i) => {
        const a = (i / 12) * Math.PI * 2;
        return (
          <line
            key={i}
            x1={220 + Math.cos(a) * 76}
            y1={180 + Math.sin(a) * 76}
            x2={220 + Math.cos(a) * 100}
            y2={180 + Math.sin(a) * 100}
            stroke={PAI_THEME.colors.sunlight}
            strokeWidth={5}
            strokeLinecap="round"
          />
        );
      })}
      <text x={220} y={290} fill={PAI_THEME.colors.sunlight} fontSize={26} fontWeight={700} textAnchor="middle">
        SUN
      </text>

      {/* Photons travelling diagonally toward chloroplast */}
      {Array.from({ length: 8 }).map((_, i) => {
        // Each photon emits with a delay
        const offset = i * 0.18;
        const localT = Math.max(0, t - offset) % 2.0; // loops
        const progress = Math.min(1, localT / 1.4);
        const startX = 280 + i * 4;
        const startY = 240 + i * 6;
        const targetX = CHLORO_CX - 200 + (i * 60);
        const targetY = CHLORO_CY - 60;
        const x = interpolate(progress, [0, 1], [startX, targetX]);
        const y = interpolate(progress, [0, 1], [startY, targetY]);
        const op = progress < 0.95 ? 1 : 1 - (progress - 0.95) * 20;

        return (
          <g key={i} opacity={Math.max(0, op)}>
            <circle cx={x} cy={y} r={10} fill={PAI_THEME.colors.sunlight} opacity={0.4} />
            <circle cx={x} cy={y} r={5} fill={PAI_THEME.colors.sunlightHot} />
          </g>
        );
      })}

      <text
        x={500}
        y={420}
        fill={PAI_THEME.colors.sunlight}
        fontSize={22}
        fontWeight={700}
        transform="rotate(28 500 420)"
      >
        photons (light energy)
      </text>
    </g>
  );
};

/** Stage 2: water-splitting on thylakoids → O2 + ATP + NADPH */
const LightReactions: React.FC<{ frame: number; opacity: number }> = ({ frame, opacity }) => {
  if (opacity <= 0) return null;
  const t = (frame - F_S2_START) / (F_S2_END - F_S2_START);

  // Water drops entering from the left
  const waterX = interpolate(Math.max(0, t * 1.2), [0, 0.5], [80, CHLORO_CX - CHLORO_RX + 30], {
    extrapolateRight: 'clamp',
  });
  const waterOp = interpolate(t, [0, 0.1, 0.5, 0.6], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // O2 bubbles rising from the chloroplast
  const o2T = Math.max(0, t - 0.3);

  return (
    <g opacity={opacity}>
      {/* H2O input panel */}
      <rect x={40} y={520} width={140} height={86} rx={12} fill={PAI_THEME.colors.waterDeep} stroke={PAI_THEME.colors.water} strokeWidth={3} />
      <text x={110} y={560} fill={PAI_THEME.colors.text} fontSize={32} fontWeight={700} textAnchor="middle">
        H₂O
      </text>
      <text x={110} y={590} fill={PAI_THEME.colors.oxygen} fontSize={16} textAnchor="middle">
        from soil
      </text>

      {/* Water drop in transit */}
      <g opacity={waterOp}>
        <path
          d={`M ${waterX} 540 Q ${waterX - 14} 555 ${waterX - 14} 568 Q ${waterX - 14} 580 ${waterX} 580 Q ${waterX + 14} 580 ${waterX + 14} 568 Q ${waterX + 14} 555 ${waterX} 540 Z`}
          fill={PAI_THEME.colors.water}
          stroke={PAI_THEME.colors.waterDeep}
          strokeWidth={2}
        />
      </g>

      {/* Water-splitting flash on the thylakoid */}
      {t > 0.4 && t < 0.7 && (
        <g>
          <circle cx={CHLORO_CX - 200} cy={CHLORO_CY - 30} r={50} fill={PAI_THEME.colors.sunlight} opacity={0.4} />
          <text x={CHLORO_CX - 200} y={CHLORO_CY - 90} fill={PAI_THEME.colors.sunlightHot} fontSize={22} fontWeight={700} textAnchor="middle">
            2 H₂O → 4 H⁺ + 4 e⁻ + O₂
          </text>
        </g>
      )}

      {/* O2 bubbles rising up + out of the leaf */}
      {Array.from({ length: 4 }).map((_, i) => {
        const offset = i * 0.18;
        const localT = Math.max(0, o2T - offset) % 1.5;
        const progress = Math.min(1, localT / 1.0);
        const startY = CHLORO_CY - 80;
        const endY = 200;
        const y = interpolate(progress, [0, 1], [startY, endY]);
        const x = CHLORO_CX - 230 + i * 18 + Math.sin(localT * 6) * 6;
        const r = interpolate(progress, [0, 1], [10, 18]);
        const op = progress < 0.85 ? interpolate(progress, [0, 0.1], [0, 1], { extrapolateRight: 'clamp' }) : 1 - (progress - 0.85) * 6;

        return (
          <g key={i} opacity={Math.max(0, op)}>
            <circle cx={x} cy={y} r={r} fill={PAI_THEME.colors.oxygen} stroke={PAI_THEME.colors.water} strokeWidth={2} />
            <text x={x} y={y + 5} fill={PAI_THEME.colors.waterDeep} fontSize={12} fontWeight={700} textAnchor="middle">
              O₂
            </text>
          </g>
        );
      })}

      {/* "O2 out" sign at the top */}
      <text x={CHLORO_CX - 200} y={140} fill={PAI_THEME.colors.oxygen} fontSize={22} fontWeight={700} textAnchor="middle">
        O₂ released ↑
      </text>

      {/* ATP + NADPH icons being produced — accumulate on the right side */}
      {[0, 1, 2].map((i) => {
        const iconStart = 0.3 + i * 0.15;
        const iconT = Math.max(0, (t - iconStart) * 4);
        const iconOp = Math.min(1, iconT);
        if (iconOp <= 0) return null;
        const x = CHLORO_CX + 280 + i * 90;
        const y = CHLORO_CY - 60;
        return (
          <g key={`atp-${i}`} opacity={iconOp}>
            <rect x={x - 32} y={y - 24} width={64} height={48} rx={8} fill={PAI_THEME.colors.atp} stroke={PAI_THEME.colors.atpStroke} strokeWidth={2.5} />
            <text x={x} y={y + 6} fill={PAI_THEME.colors.atpStroke} fontSize={18} fontWeight={700} textAnchor="middle">
              ATP
            </text>
          </g>
        );
      })}
      {[0, 1, 2].map((i) => {
        const iconStart = 0.4 + i * 0.15;
        const iconT = Math.max(0, (t - iconStart) * 4);
        const iconOp = Math.min(1, iconT);
        if (iconOp <= 0) return null;
        const x = CHLORO_CX + 280 + i * 90;
        const y = CHLORO_CY + 20;
        return (
          <g key={`nadph-${i}`} opacity={iconOp}>
            <rect x={x - 38} y={y - 24} width={76} height={48} rx={8} fill={PAI_THEME.colors.nadph} stroke={PAI_THEME.colors.nadphStroke} strokeWidth={2.5} />
            <text x={x} y={y + 6} fill={PAI_THEME.colors.nadphStroke} fontSize={16} fontWeight={700} textAnchor="middle">
              NADPH
            </text>
          </g>
        );
      })}

      {/* Phase label */}
      <text x={CHLORO_CX} y={200} fill={PAI_THEME.colors.text} fontSize={36} fontWeight={700} textAnchor="middle">
        Stage 1 — Light Reactions
      </text>
      <text x={CHLORO_CX} y={236} fill={PAI_THEME.colors.accentLight} fontSize={22} textAnchor="middle">
        light splits water · makes ATP + NADPH · releases O₂
      </text>
    </g>
  );
};

/** Stage 3: Calvin cycle — CO2 enters, the cycle turns, G3P emerges. */
const CalvinCycle: React.FC<{ frame: number; opacity: number }> = ({ frame, opacity }) => {
  if (opacity <= 0) return null;
  const t = (frame - F_S3_START) / (F_S3_END - F_S3_START);

  // The cycle ring rotates 3 times across the phase
  const rotation = t * 360 * 3;

  // CO2 entering from above-right
  const co2Op = interpolate(t, [0, 0.1, 0.7, 0.85], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const co2X = interpolate(t, [0, 0.4], [1700, CHLORO_CX + 100], { extrapolateRight: 'clamp' });
  const co2Y = interpolate(t, [0, 0.4], [200, CHLORO_CY + 50], { extrapolateRight: 'clamp' });

  // G3P pop-out at the end
  const g3pOp = interpolate(t, [0.6, 0.85], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <g opacity={opacity}>
      {/* Phase label */}
      <text x={CHLORO_CX} y={200} fill={PAI_THEME.colors.text} fontSize={36} fontWeight={700} textAnchor="middle">
        Stage 2 — Calvin Cycle (in stroma)
      </text>
      <text x={CHLORO_CX} y={236} fill={PAI_THEME.colors.accentLight} fontSize={22} textAnchor="middle">
        CO₂ + ATP + NADPH → G3P (sugar precursor)
      </text>

      {/* CO2 input */}
      <rect x={1660} y={200} width={180} height={100} rx={12} fill={PAI_THEME.colors.background} stroke={PAI_THEME.colors.co2} strokeWidth={3} />
      <text x={1750} y={250} fill={PAI_THEME.colors.text} fontSize={36} fontWeight={700} textAnchor="middle">
        CO₂
      </text>
      <text x={1750} y={282} fill={PAI_THEME.colors.textMuted} fontSize={16} textAnchor="middle">
        from atmosphere
      </text>

      {/* CO2 traveling in */}
      <g opacity={co2Op}>
        <circle cx={co2X} cy={co2Y} r={22} fill={PAI_THEME.colors.co2} opacity={0.7} />
        <text x={co2X} y={co2Y + 6} fill={PAI_THEME.colors.background} fontSize={16} fontWeight={700} textAnchor="middle">
          CO₂
        </text>
      </g>

      {/* The Calvin cycle ring (in the lower / stroma half of the chloroplast) */}
      <g transform={`translate(${CHLORO_CX}, ${CHLORO_CY + 80}) rotate(${rotation})`}>
        <circle cx={0} cy={0} r={110} fill="none" stroke={PAI_THEME.colors.glucoseStroke} strokeWidth={4} strokeDasharray="14 8" />
        {/* Three carbon-fixation points */}
        {[0, 1, 2].map((i) => {
          const a = (i / 3) * Math.PI * 2 - Math.PI / 2;
          const x = Math.cos(a) * 110;
          const y = Math.sin(a) * 110;
          return (
            <g key={i}>
              <circle cx={x} cy={y} r={18} fill={PAI_THEME.colors.glucose} stroke={PAI_THEME.colors.glucoseStroke} strokeWidth={3} />
              <text x={x} y={y + 5} fontSize={14} fontWeight={700} fill={PAI_THEME.colors.glucoseStroke} textAnchor="middle">
                C
              </text>
            </g>
          );
        })}
      </g>

      {/* Centre label of the ring (NOT rotating) */}
      <text x={CHLORO_CX} y={CHLORO_CY + 76} fill={PAI_THEME.colors.glucoseStroke} fontSize={20} fontWeight={700} textAnchor="middle">
        Calvin
      </text>
      <text x={CHLORO_CX} y={CHLORO_CY + 96} fill={PAI_THEME.colors.glucoseStroke} fontSize={20} fontWeight={700} textAnchor="middle">
        cycle
      </text>

      {/* ATP + NADPH being consumed (drain arrows pointing into the ring from above) */}
      <text x={CHLORO_CX - 240} y={CHLORO_CY - 100} fill={PAI_THEME.colors.atpStroke} fontSize={18} fontWeight={700}>
        ATP →
      </text>
      <text x={CHLORO_CX + 200} y={CHLORO_CY - 100} fill={PAI_THEME.colors.nadphStroke} fontSize={18} fontWeight={700}>
        ← NADPH
      </text>
      <line x1={CHLORO_CX - 180} y1={CHLORO_CY - 90} x2={CHLORO_CX - 80} y2={CHLORO_CY + 40} stroke={PAI_THEME.colors.atpStroke} strokeWidth={2} />
      <line x1={CHLORO_CX + 250} y1={CHLORO_CY - 90} x2={CHLORO_CX + 80} y2={CHLORO_CY + 40} stroke={PAI_THEME.colors.nadphStroke} strokeWidth={2} />

      {/* G3P emerges at the bottom-right */}
      <g opacity={g3pOp}>
        <rect x={1620} y={CHLORO_CY + 60} width={200} height={86} rx={12} fill={PAI_THEME.colors.glucose} stroke={PAI_THEME.colors.glucoseStroke} strokeWidth={3} />
        <text x={1720} y={CHLORO_CY + 100} fill={PAI_THEME.colors.glucoseStroke} fontSize={32} fontWeight={700} textAnchor="middle">
          G3P
        </text>
        <text x={1720} y={CHLORO_CY + 130} fill={PAI_THEME.colors.glucoseStroke} fontSize={14} textAnchor="middle">
          3-carbon sugar
        </text>
        {/* Arrow from ring to G3P */}
        <line x1={CHLORO_CX + 110} y1={CHLORO_CY + 80} x2={1620} y2={CHLORO_CY + 100} stroke={PAI_THEME.colors.glucoseStroke} strokeWidth={3} strokeDasharray="6 4" />
        <polygon points={`${1614},${CHLORO_CY + 96} ${1622},${CHLORO_CY + 100} ${1614},${CHLORO_CY + 104}`} fill={PAI_THEME.colors.glucoseStroke} />
      </g>
    </g>
  );
};

/** Stage 4: G3P → glucose → starch grain */
const SugarSynthesis: React.FC<{ frame: number; opacity: number }> = ({ frame, opacity }) => {
  if (opacity <= 0) return null;
  const t = (frame - F_S4_START) / (F_S4_END - F_S4_START);

  // Glucose ring assembling
  const glucoseOp = interpolate(t, [0, 0.3], [0, 1], { extrapolateRight: 'clamp' });
  const glucoseScale = spring({ frame: frame - F_S4_START, fps: 30, config: PAI_THEME.animation.springDefault });

  // Starch grain growing
  const starchOp = interpolate(t, [0.4, 0.7], [0, 1], { extrapolateRight: 'clamp' });
  const starchScale = interpolate(t, [0.4, 1], [0.4, 1.4], { extrapolateRight: 'clamp' });

  return (
    <g opacity={opacity}>
      {/* Phase label */}
      <text x={CHLORO_CX} y={200} fill={PAI_THEME.colors.text} fontSize={36} fontWeight={700} textAnchor="middle">
        Stage 3 — Build Glucose · Store as Starch
      </text>
      <text x={CHLORO_CX} y={236} fill={PAI_THEME.colors.accentLight} fontSize={22} textAnchor="middle">
        2 × G3P → 1 glucose (C₆H₁₂O₆) · many glucose → starch grain
      </text>

      {/* G3P → Glucose ring transformation (left of centre) */}
      <g transform={`translate(${CHLORO_CX - 280}, ${CHLORO_CY + 240}) scale(${glucoseScale})`} opacity={glucoseOp}>
        {/* Hexagonal glucose ring */}
        <polygon
          points="0,-50 43,-25 43,25 0,50 -43,25 -43,-25"
          fill={PAI_THEME.colors.glucose}
          stroke={PAI_THEME.colors.glucoseStroke}
          strokeWidth={4}
        />
        {/* Carbons at vertices */}
        {[0, 60, 120, 180, 240, 300].map((deg, i) => {
          const a = (deg - 90) * Math.PI / 180;
          const x = Math.cos(a) * 50;
          const y = Math.sin(a) * 50;
          return (
            <g key={i}>
              <circle cx={x} cy={y} r={8} fill={PAI_THEME.colors.glucoseStroke} />
            </g>
          );
        })}
        <text x={0} y={6} fill={PAI_THEME.colors.glucoseStroke} fontSize={20} fontWeight={700} textAnchor="middle">
          glucose
        </text>
      </g>

      {/* Arrow from glucose to starch */}
      <line x1={CHLORO_CX - 200} y1={CHLORO_CY + 240} x2={CHLORO_CX + 100} y2={CHLORO_CY + 240} stroke={PAI_THEME.colors.glucoseStroke} strokeWidth={3} opacity={starchOp} />
      <polygon points={`${CHLORO_CX + 96},${CHLORO_CY + 236} ${CHLORO_CX + 104},${CHLORO_CY + 240} ${CHLORO_CX + 96},${CHLORO_CY + 244}`} fill={PAI_THEME.colors.glucoseStroke} opacity={starchOp} />
      <text x={CHLORO_CX - 50} y={CHLORO_CY + 226} fill={PAI_THEME.colors.glucoseStroke} fontSize={18} fontStyle="italic" textAnchor="middle" opacity={starchOp}>
        polymerise
      </text>

      {/* Starch grain (right of centre) */}
      <g transform={`translate(${CHLORO_CX + 240}, ${CHLORO_CY + 240}) scale(${starchScale})`} opacity={starchOp}>
        <ellipse cx={0} cy={0} rx={70} ry={50} fill={PAI_THEME.colors.atp} stroke={PAI_THEME.colors.atpStroke} strokeWidth={4} />
        {/* Starch granule rings */}
        <ellipse cx={0} cy={0} rx={50} ry={36} fill="none" stroke={PAI_THEME.colors.atpStroke} strokeWidth={1.5} opacity={0.6} />
        <ellipse cx={0} cy={0} rx={30} ry={22} fill="none" stroke={PAI_THEME.colors.atpStroke} strokeWidth={1.5} opacity={0.5} />
        <text x={0} y={6} fill={PAI_THEME.colors.atpStroke} fontSize={20} fontWeight={700} textAnchor="middle">
          starch
        </text>
      </g>

      {/* Footnote: where the energy came from */}
      <text x={CHLORO_CX} y={CHLORO_CY + 380} fill={PAI_THEME.colors.textMuted} fontSize={20} fontStyle="italic" textAnchor="middle">
        Sunlight energy is now stored in chemical bonds — the food chain begins here.
      </text>
    </g>
  );
};

/** Summary equation tile — fades in at the end. */
const SummaryEquation: React.FC<{ frame: number; opacity: number }> = ({ frame, opacity }) => {
  if (opacity <= 0) return null;

  return (
    <g opacity={opacity}>
      {/* Background tile */}
      <rect x={260} y={400} width={1400} height={300} rx={20} fill={PAI_THEME.colors.background} stroke={PAI_THEME.colors.accent} strokeWidth={5} />

      <text x={CHLORO_CX} y={460} fill={PAI_THEME.colors.text} fontSize={42} fontWeight={700} textAnchor="middle">
        The Photosynthesis Equation
      </text>

      {/* Equation: 6 CO2 + 6 H2O + light → C6H12O6 + 6 O2 */}
      <g transform={`translate(${CHLORO_CX}, 540)`}>
        <text x={-560} y={0} fill={PAI_THEME.colors.co2} fontSize={56} fontWeight={700} textAnchor="middle">
          6 CO₂
        </text>
        <text x={-440} y={0} fill={PAI_THEME.colors.text} fontSize={56} fontWeight={700} textAnchor="middle">
          +
        </text>
        <text x={-300} y={0} fill={PAI_THEME.colors.water} fontSize={56} fontWeight={700} textAnchor="middle">
          6 H₂O
        </text>
        <text x={-180} y={0} fill={PAI_THEME.colors.text} fontSize={56} fontWeight={700} textAnchor="middle">
          +
        </text>
        <text x={-40} y={0} fill={PAI_THEME.colors.sunlight} fontSize={56} fontWeight={700} textAnchor="middle">
          light
        </text>
        <text x={120} y={0} fill={PAI_THEME.colors.accentLight} fontSize={64} fontWeight={700} textAnchor="middle">
          →
        </text>
        <text x={310} y={0} fill={PAI_THEME.colors.glucoseStroke} fontSize={56} fontWeight={700} textAnchor="middle">
          C₆H₁₂O₆
        </text>
        <text x={460} y={0} fill={PAI_THEME.colors.text} fontSize={56} fontWeight={700} textAnchor="middle">
          +
        </text>
        <text x={580} y={0} fill={PAI_THEME.colors.oxygen} fontSize={56} fontWeight={700} textAnchor="middle">
          6 O₂
        </text>
      </g>

      {/* Labels under equation */}
      <text x={CHLORO_CX - 560} y={620} fill={PAI_THEME.colors.textMuted} fontSize={20} textAnchor="middle">
        from air
      </text>
      <text x={CHLORO_CX - 300} y={620} fill={PAI_THEME.colors.textMuted} fontSize={20} textAnchor="middle">
        from soil
      </text>
      <text x={CHLORO_CX - 40} y={620} fill={PAI_THEME.colors.textMuted} fontSize={20} textAnchor="middle">
        from sun
      </text>
      <text x={CHLORO_CX + 310} y={620} fill={PAI_THEME.colors.textMuted} fontSize={20} textAnchor="middle">
        sugar (food)
      </text>
      <text x={CHLORO_CX + 580} y={620} fill={PAI_THEME.colors.textMuted} fontSize={20} textAnchor="middle">
        oxygen (we breathe)
      </text>

      <text x={CHLORO_CX} y={680} fill={PAI_THEME.colors.accentLight} fontSize={26} fontStyle="italic" textAnchor="middle">
        Light energy → chemical energy.  This is the engine of every food chain.
      </text>
    </g>
  );
};

// ── Main scene ──────────────────────────────────────────────────────────
export const PhotosynthesisFlowScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleSpring = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30, F_TITLE_END, F_TITLE_END + 40], [0, 1, 1, 0.4], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const subOp = interpolate(frame, [20, 60, F_TITLE_END + 30, F_TITLE_END + 60], [0, 1, 1, 0.3], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const stage1Op = stageOpacity(frame, F_S1_START, F_S1_END);
  const stage2Op = stageOpacity(frame, F_S2_START, F_S2_END);
  const stage3Op = stageOpacity(frame, F_S3_START, F_S3_END);
  const stage4Op = stageOpacity(frame, F_S4_START, F_S4_END);
  const eqOp = stageOpacity(frame, F_EQ_START, F_EQ_END, 25);

  const outroOp = interpolate(frame, [F_OUTRO_START, F_OUTRO_START + 40], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
        fontFamily: PAI_THEME.typography.fontFamily,
      }}
    >
      {/* ── Title ─────────────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 50,
          left: 0,
          right: 0,
          textAlign: 'center',
          zIndex: 5,
          pointerEvents: 'none',
        }}
      >
        <h1
          style={{
            fontSize: 64,
            color: PAI_THEME.colors.text,
            margin: 0,
            opacity: titleOp,
            transform: `scale(${titleSpring})`,
          }}
        >
          Photosynthesis — the Engine of Life
        </h1>
        <p
          style={{
            fontSize: 28,
            color: PAI_THEME.colors.accentLight,
            marginTop: 10,
            fontStyle: 'italic',
            opacity: subOp,
          }}
        >
          Sunlight + water + CO₂ → sugar + oxygen, inside one chloroplast.
        </p>
      </div>

      {/* ── Single SVG canvas for all stage layers ─────────────── */}
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        style={{ position: 'absolute', inset: 0 }}
      >
        {/* The chloroplast is always on stage */}
        <Chloroplast frame={frame} />

        {/* Stage 1: sunlight */}
        <Sunlight frame={frame} opacity={stage1Op} />

        {/* Stage 1 caption */}
        {stage1Op > 0 && (
          <g opacity={stage1Op}>
            <text x={CHLORO_CX} y={200} fill={PAI_THEME.colors.text} fontSize={36} fontWeight={700} textAnchor="middle">
              Step 1 — Sunlight strikes the chloroplast
            </text>
            <text x={CHLORO_CX} y={236} fill={PAI_THEME.colors.accentLight} fontSize={22} textAnchor="middle">
              chlorophyll absorbs photons (mostly red + blue light)
            </text>
          </g>
        )}

        {/* Stage 2: light reactions */}
        <LightReactions frame={frame} opacity={stage2Op} />

        {/* Stage 3: Calvin cycle */}
        <CalvinCycle frame={frame} opacity={stage3Op} />

        {/* Stage 4: glucose + starch */}
        <SugarSynthesis frame={frame} opacity={stage4Op} />

        {/* Summary equation */}
        <SummaryEquation frame={frame} opacity={eqOp} />
      </svg>

      {/* ── Outro caption ─────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 980,
          left: 0,
          right: 0,
          textAlign: 'center',
          fontSize: 28,
          fontWeight: 700,
          color: PAI_THEME.colors.text,
          opacity: outroOp,
        }}
      >
        Every breath you take · every grain you eat · was once sunlight in a leaf.
      </div>
    </AbsoluteFill>
  );
};
