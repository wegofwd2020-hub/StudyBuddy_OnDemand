/**
 * BernoulliVenturiScene — animated venturi tube illustrating Bernoulli's principle.
 *
 * A horizontal venturi: wide section (area A) → throat (area A/3) → wide section (area A).
 * Incompressible fluid flow continuity: v_throat = 3·v_wide.
 * Bernoulli (horizontal, same height):  P + ½ρv² = const
 *   → ΔP = P_wide − P_throat = ½ρ(v_throat² − v_wide²) = 4·ρv_wide²
 * Three vertical manometer tubes show the pressure: the middle one (over the throat)
 * has a much shorter column than the outer two.
 *
 * Frames @ 30 fps (26 s = 780 frames):
 *   0–60     Title fades in
 *   60–180   Pipe + manometer tubes fade in (no fluid yet)
 *   180–360  Fluid fills, particles start moving — slow in wide section, fast in throat
 *   360–540  Manometer columns animate down for the throat, stay tall on the sides
 *   540–660  ΔP arrow + Bernoulli equation reveal
 *   660–780  Caption + recap fade
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Pipe geometry (px) — drawn into a 1700×500 SVG centred on the canvas ────
// Wide section radius (half-height): 90 px → diameter 180
// Throat radius: 30 px → diameter 60     (area ratio 3, so velocity ratio 3)
const SVG_W = 1700;
const SVG_H = 720;
const PIPE_LEFT = 80;
const PIPE_RIGHT = 1620;
const CENTER_Y = 480;
const WIDE_R = 90;
const THROAT_R = 30;

// X-positions of the four "shoulders" of the venturi
const X_INLET = PIPE_LEFT;
const X_THROAT_START = 700;
const X_THROAT_END = 1000;
const X_OUTLET = PIPE_RIGHT;

// Manometer tube positions (3 of them: over wide, over throat, over wide)
const MANO_X = [400, 850, 1300] as const;
const MANO_TUBE_TOP = 60;
const MANO_TUBE_BOTTOM = CENTER_Y - WIDE_R - 4; // attaches just above pipe
const MANO_TUBE_W = 36;
// Column heights: max height = full tube. We'll have wide-section column = 320 px tall
// (almost full); throat column only ~110 px tall.
const COL_WIDE_TARGET = 330; // px above the connection point
const COL_THROAT_TARGET = 120;

// Returns the half-height (radius) of the pipe at horizontal position x.
function radiusAt(x: number): number {
  if (x <= X_INLET || x >= X_OUTLET) return WIDE_R;
  if (x < X_THROAT_START) {
    // smooth transition wide → throat over 200 px
    const transStart = X_THROAT_START - 200;
    if (x < transStart) return WIDE_R;
    const t = (x - transStart) / 200;
    // smoothstep
    const s = t * t * (3 - 2 * t);
    return WIDE_R + (THROAT_R - WIDE_R) * s;
  }
  if (x <= X_THROAT_END) return THROAT_R;
  if (x < X_THROAT_END + 200) {
    const t = (x - X_THROAT_END) / 200;
    const s = t * t * (3 - 2 * t);
    return THROAT_R + (WIDE_R - THROAT_R) * s;
  }
  return WIDE_R;
}

// Cross-sectional area is proportional to π·r² → here r² is enough for ratios
function areaAt(x: number): number {
  const r = radiusAt(x);
  return Math.PI * r * r;
}

// Reference inlet area
const A_REF = Math.PI * WIDE_R * WIDE_R;

// Continuity: v(x) = v_ref · A_ref / A(x)
function speedScaleAt(x: number): number {
  return A_REF / areaAt(x);
}

// Number of streamline particles
const N_PARTICLES = 60;
const N_STREAMLINES = 7;

// Build the pipe top and bottom polylines
function buildPipeOutline(): { top: string; bottom: string; fill: string } {
  const samples = 200;
  const topPts: string[] = [];
  const bottomPts: string[] = [];
  for (let i = 0; i <= samples; i++) {
    const x = PIPE_LEFT + (PIPE_RIGHT - PIPE_LEFT) * (i / samples);
    const r = radiusAt(x);
    topPts.push(`${x.toFixed(1)},${(CENTER_Y - r).toFixed(1)}`);
    bottomPts.push(`${x.toFixed(1)},${(CENTER_Y + r).toFixed(1)}`);
  }
  const fill =
    `M ${topPts.join(' L ')} ` +
    `L ${bottomPts.slice().reverse().join(' L ')} Z`;
  return { top: topPts.join(' '), bottom: bottomPts.join(' '), fill };
}

const PIPE = buildPipeOutline();

export const BernoulliVenturiScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Phase opacity ─────────────────────────────────────────────────────────
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [30, 60], [0, 1], { extrapolateRight: 'clamp' });
  const pipeOp = interpolate(frame, [60, 180], [0, 1], { extrapolateRight: 'clamp' });
  const fluidOp = interpolate(frame, [180, 240], [0, 1], { extrapolateRight: 'clamp' });
  // Manometer columns: from 0 (empty) to target heights
  // Both side columns rise to their tall target between f=180 and 360.
  // The throat column ALSO rises tall first (uniform fill), then between f=360 and 540 it
  // falls down to its true low value as the fluid accelerates and pressure drops.
  const allColRise = interpolate(frame, [180, 360], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const throatColFall = interpolate(frame, [360, 540], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  const wideColH = COL_WIDE_TARGET * allColRise;
  const throatColH = COL_WIDE_TARGET * allColRise - (COL_WIDE_TARGET - COL_THROAT_TARGET) * throatColFall;

  const dpArrowOp = interpolate(frame, [540, 600], [0, 1], { extrapolateRight: 'clamp' });
  const eqOp = interpolate(frame, [600, 660], [0, 1], { extrapolateRight: 'clamp' });
  const captionOp = interpolate(frame, [660, 720], [0, 1], { extrapolateRight: 'clamp' });

  // ── Particles ─────────────────────────────────────────────────────────────
  // Each particle has a base streamline offset (vertical fraction of pipe radius)
  // and a phase. We integrate position numerically every frame (cheap enough).
  // To avoid stateful computation, derive each particle position from frame & seed.
  // We use a quasi-random offset and time-shifted x, then iteratively step using speedScale.

  // Velocity at the inlet (px per frame). We move slow in wide, fast in throat.
  const V_INLET_PX = 4; // arbitrary visual speed

  // For each particle, compute its current x by stepping a fixed-dt integration.
  // Total simulated frames = 540 (when motion is most active). For frames < 180, no motion.
  // For determinism we re-integrate from "particle birth" each render.
  const particles: { x: number; y: number; key: number; alpha: number }[] = [];
  const streamlines: { d: string; key: number }[] = [];

  const motionFrame = Math.max(0, frame - 180);

  // Streamlines (smooth curves bowing as pipe narrows)
  for (let s = 0; s < N_STREAMLINES; s++) {
    // streamline fraction from -1 (top) to +1 (bottom)
    const sf = (s - (N_STREAMLINES - 1) / 2) / ((N_STREAMLINES - 1) / 2);
    const samples = 120;
    const pts: string[] = [];
    for (let i = 0; i <= samples; i++) {
      const x = PIPE_LEFT + (PIPE_RIGHT - PIPE_LEFT) * (i / samples);
      const r = radiusAt(x);
      const y = CENTER_Y + sf * (r - 6);
      pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    streamlines.push({ d: pts.join(' '), key: s });
  }

  // Particles: spawn at evenly spaced phases, each follows one of the streamlines.
  for (let p = 0; p < N_PARTICLES; p++) {
    const streamlineIdx = p % N_STREAMLINES;
    const sf = (streamlineIdx - (N_STREAMLINES - 1) / 2) / ((N_STREAMLINES - 1) / 2);
    // Phase offset (in frames) so particles are evenly spread along pipe.
    const phaseOffset = (p / N_PARTICLES) * 360; // every 360 frames a full cycle

    // Step from PIPE_LEFT to current location using speed-scale at each step
    let x = PIPE_LEFT;
    const stepsPerFrame = 1;
    const totalSteps = Math.floor((motionFrame + phaseOffset) * stepsPerFrame);
    for (let k = 0; k < totalSteps; k++) {
      x += V_INLET_PX * speedScaleAt(x);
      if (x > PIPE_RIGHT) {
        x = PIPE_LEFT + (x - PIPE_RIGHT); // wrap
      }
    }
    const r = radiusAt(x);
    const y = CENTER_Y + sf * (r - 6);
    // Fade in particle as motionFrame grows
    const alpha = Math.min(1, motionFrame / 60);
    particles.push({ x, y, key: p, alpha });
  }

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      flexDirection: 'column', alignItems: 'center', padding: 30,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      <h1 style={{
        fontSize: 56, color: PAI_THEME.colors.text, margin: '12px 0 4px',
        opacity: titleOp, transform: `scale(${titleScale})`, textAlign: 'center',
      }}>
        Bernoulli's Principle — Venturi Tube
      </h1>
      <p style={{
        fontSize: 26, color: PAI_THEME.colors.accentLight, margin: '0 0 8px',
        opacity: subOp, fontStyle: 'italic',
      }}>
        Faster flow, lower pressure.    P + ½ρv² + ρgh = constant
      </p>

      <svg width={SVG_W} height={SVG_H} style={{ marginTop: 16 }}>
        <defs>
          <linearGradient id="bv-fluidgrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.35" />
            <stop offset="50%" stopColor="#60a5fa" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.35" />
          </linearGradient>
          <marker id="bv-redarr" markerWidth={14} markerHeight={14} refX={11} refY={5} orient="auto">
            <polygon points="0,0 12,5 0,10" fill={PAI_THEME.colors.error} />
          </marker>
          <marker id="bv-bluarr" markerWidth={14} markerHeight={14} refX={11} refY={5} orient="auto">
            <polygon points="0,0 12,5 0,10" fill={PAI_THEME.colors.info} />
          </marker>
        </defs>

        {/* Manometer tubes (drawn first so pipe sits on top) */}
        <g opacity={pipeOp}>
          {MANO_X.map((mx, idx) => (
            <g key={`mano-${idx}`}>
              <rect
                x={mx - MANO_TUBE_W / 2}
                y={MANO_TUBE_TOP}
                width={MANO_TUBE_W}
                height={MANO_TUBE_BOTTOM - MANO_TUBE_TOP}
                fill="none"
                stroke={PAI_THEME.colors.textMuted}
                strokeWidth={3}
                rx={4}
              />
              <text
                x={mx}
                y={MANO_TUBE_TOP - 14}
                fill={PAI_THEME.colors.text}
                fontSize={26}
                fontWeight={700}
                textAnchor="middle"
              >
                {idx === 1 ? 'P_throat' : `P_${idx === 0 ? '1' : '3'}`}
              </text>
            </g>
          ))}
        </g>

        {/* Manometer fluid columns */}
        <g opacity={fluidOp}>
          {MANO_X.map((mx, idx) => {
            const colH = idx === 1 ? throatColH : wideColH;
            // Column "top" is at MANO_TUBE_BOTTOM - colH
            const topY = MANO_TUBE_BOTTOM - colH;
            return (
              <rect
                key={`mano-fluid-${idx}`}
                x={mx - MANO_TUBE_W / 2 + 3}
                y={topY}
                width={MANO_TUBE_W - 6}
                height={Math.max(0, colH)}
                fill={PAI_THEME.colors.info}
                opacity={0.85}
              />
            );
          })}
        </g>

        {/* Pipe outline */}
        <path
          d={PIPE.fill}
          fill={`url(#bv-fluidgrad)`}
          stroke={PAI_THEME.colors.text}
          strokeWidth={4}
          opacity={pipeOp}
        />

        {/* Manometer connection nubs (small rectangles where tubes meet pipe) */}
        <g opacity={pipeOp}>
          {MANO_X.map((mx, idx) => {
            const r = radiusAt(mx);
            const yTop = CENTER_Y - r;
            return (
              <rect
                key={`nub-${idx}`}
                x={mx - 6}
                y={yTop - 2}
                width={12}
                height={6}
                fill={PAI_THEME.colors.text}
              />
            );
          })}
        </g>

        {/* Streamlines (very faint) */}
        <g opacity={fluidOp * 0.18}>
          {streamlines.map((s) => (
            <polyline
              key={`sl-${s.key}`}
              points={s.d}
              fill="none"
              stroke={PAI_THEME.colors.accentLight}
              strokeWidth={1}
            />
          ))}
        </g>

        {/* Particles (the actual fluid flow) */}
        <g opacity={fluidOp}>
          {particles.map((p) => (
            <circle
              key={`p-${p.key}`}
              cx={p.x}
              cy={p.y}
              r={4}
              fill={PAI_THEME.colors.accentLight}
              opacity={p.alpha}
            />
          ))}
        </g>

        {/* Section labels under pipe */}
        <g opacity={pipeOp}>
          <text x={400} y={CENTER_Y + WIDE_R + 56} fill={PAI_THEME.colors.text}
            fontSize={28} fontWeight={700} textAnchor="middle">Section 1: wide</text>
          <text x={400} y={CENTER_Y + WIDE_R + 90} fill={PAI_THEME.colors.info}
            fontSize={24} fontWeight={700} textAnchor="middle">v₁ slow · P₁ high</text>

          <text x={850} y={CENTER_Y + WIDE_R + 56} fill={PAI_THEME.colors.error}
            fontSize={28} fontWeight={700} textAnchor="middle">Throat: narrow (A/3)</text>
          <text x={850} y={CENTER_Y + WIDE_R + 90} fill={PAI_THEME.colors.error}
            fontSize={24} fontWeight={700} textAnchor="middle">v₂ FAST (3v₁) · P₂ LOW</text>

          <text x={1300} y={CENTER_Y + WIDE_R + 56} fill={PAI_THEME.colors.text}
            fontSize={28} fontWeight={700} textAnchor="middle">Section 3: wide</text>
          <text x={1300} y={CENTER_Y + WIDE_R + 90} fill={PAI_THEME.colors.info}
            fontSize={24} fontWeight={700} textAnchor="middle">v₃ slow · P recovers</text>
        </g>

        {/* ΔP arrow between manometer 1 and manometer 2 */}
        <g opacity={dpArrowOp}>
          {/* Horizontal dashed comparison line at the top of the throat column */}
          <line
            x1={MANO_X[0] + MANO_TUBE_W / 2 + 4}
            y1={MANO_TUBE_BOTTOM - throatColH}
            x2={MANO_X[1] - MANO_TUBE_W / 2 - 4}
            y2={MANO_TUBE_BOTTOM - throatColH}
            stroke={PAI_THEME.colors.warning}
            strokeWidth={2}
            strokeDasharray="6 6"
          />
          {/* Vertical ΔP double-arrow on the side of the throat tube */}
          <line
            x1={MANO_X[1] + MANO_TUBE_W / 2 + 24}
            y1={MANO_TUBE_BOTTOM - wideColH}
            x2={MANO_X[1] + MANO_TUBE_W / 2 + 24}
            y2={MANO_TUBE_BOTTOM - throatColH}
            stroke={PAI_THEME.colors.warning}
            strokeWidth={4}
            markerEnd="url(#bv-bluarr)"
          />
          <text
            x={MANO_X[1] + MANO_TUBE_W / 2 + 36}
            y={MANO_TUBE_BOTTOM - (wideColH + throatColH) / 2 + 6}
            fill={PAI_THEME.colors.warning}
            fontSize={26}
            fontWeight={700}
          >
            Δh ∝ ΔP
          </text>
        </g>
      </svg>

      {/* Bernoulli equation panel */}
      <div style={{
        marginTop: 4, opacity: eqOp, color: PAI_THEME.colors.text, fontSize: 28,
        textAlign: 'center', maxWidth: 1700,
      }}>
        Same fluid, same height:&nbsp;&nbsp;
        <span style={{ color: PAI_THEME.colors.info, fontWeight: 700 }}>P₁ + ½ρv₁²</span>
        &nbsp;=&nbsp;
        <span style={{ color: PAI_THEME.colors.error, fontWeight: 700 }}>P₂ + ½ρv₂²</span>
        &nbsp;&nbsp;⇒&nbsp;&nbsp;
        <span style={{ color: PAI_THEME.colors.warning, fontWeight: 700 }}>ΔP = ½ρ(v₂² − v₁²)</span>
      </div>

      {/* Caption */}
      <div style={{
        marginTop: 12, color: PAI_THEME.colors.textMuted, fontSize: 24,
        opacity: captionOp, textAlign: 'center', maxWidth: 1600, fontStyle: 'italic',
      }}>
        Where the pipe narrows, the fluid speeds up — and pressure drops.
        It's the same effect that lifts an aeroplane wing and powers a perfume atomiser.
      </div>
    </AbsoluteFill>
  );
};
