/**
 * DynamicBalanceScene — particle-level animation of dynamic equilibrium.
 *
 * Composition id: equilibrium-dynamic-balance
 * Output: Equilibrium_DynamicBalance.mp4
 *
 * Pedagogical goal: show that "equilibrium" doesn't mean "stopped". A pool of
 * molecules continuously interconverts between reactant (A, orange) and product
 * (B, green). The forward and reverse rate counters climb together, with the
 * forward rate starting fast (lots of A) and the reverse rate catching up as B
 * accumulates. They lock onto a common value at t_eq — but conversions never
 * stop; they merely match.
 *
 * Reaction shown: A ⇌ B (1:1 stoichiometry for clarity).
 *
 * Layout (1920×1080):
 *   - Title + subtitle bar at top
 *   - Left: reaction flask (square arena) with N=30 dots, each A or B
 *   - Right: live rate-vs-time chart with both forward and reverse curves
 *     building up to a common plateau
 *   - Bottom: caption that fades in once equilibrium is reached
 *
 * Frames @ 30 fps (26 s total = 780 frames):
 *   0–60      title / subtitle fade in
 *   60–120    flask appears, all dots are A (orange)
 *   120–600   simulation runs: forward/reverse rates equalize
 *   600–720   highlight equilibrium region on the chart
 *   720–780   final caption fade in
 *
 * The simulation is deterministic — uses a small mulberry32 PRNG seeded with a
 * fixed value so every render produces identical pixels.
 */
import React, { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Geometry ─────────────────────────────────────────────────────────────────
const FPS = 30;

const FLASK_X = 120;
const FLASK_Y = 200;
const FLASK_W = 760;
const FLASK_H = 720;

const CHART_X = 1020;
const CHART_Y = 240;
const CHART_W = 800;
const CHART_H = 540;

const N_PARTICLES = 30;

// Frame anchors
const F_TITLE_END = 60;
const F_SUB_END = 120;
const F_SIM_END = 600;
const F_HILITE_END = 720;
const F_CAP_END = 780;

// ── Deterministic PRNG (mulberry32) ──────────────────────────────────────────
function mulberry32(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ── Particle simulation ─────────────────────────────────────────────────────
type ParticleSnapshot = {
  x: number;       // px (within flask)
  y: number;       // px (within flask)
  isB: boolean;    // false = reactant A, true = product B
};

type FrameState = {
  particles: ParticleSnapshot[];
  rateF: number;   // forward conversions per "second" (per 30-frame window)
  rateR: number;   // reverse conversions per same window
  countA: number;
  countB: number;
};

/**
 * Pre-compute the state of the simulation at every frame between 120 and 600.
 *
 * Model — at each frame:
 *   • Every particle drifts a small random step (Brownian wiggle, bounded).
 *   • Forward attempt: each A converts to B with probability k_f (per frame).
 *   • Reverse attempt: each B converts to A with probability k_r (per frame).
 *   • Rate counters: track conversions in a sliding 30-frame window.
 *
 * With N=30, k_f=0.020, k_r=0.040 the equilibrium fraction of B is
 *   K = k_f / k_r = 0.5  →  expected [B]/[A] = 0.5 at equilibrium
 *   B_eq ≈ N · k_f / (k_f + k_r) = 30 · 0.020/0.060 = 10
 *   A_eq ≈ 20.   r_eq ≈ k_f · 20 = 0.40 conversions/frame ≈ 12 /sec window.
 */
function buildSimulation(): FrameState[] {
  const rng = mulberry32(0x5EED1234);
  const SIM_FRAMES = F_SIM_END - F_SUB_END; // 480 frames
  const k_f = 0.020;
  const k_r = 0.040;

  // Initial particle positions — uniform within flask interior
  const margin = 40;
  const positions = Array.from({ length: N_PARTICLES }, () => ({
    x: margin + rng() * (FLASK_W - 2 * margin),
    y: margin + rng() * (FLASK_H - 2 * margin),
    isB: false,
  }));

  // Pre-compute small per-particle drift offsets (per frame, deterministic)
  const driftAmp = 6;

  const states: FrameState[] = [];
  const fWindow: number[] = []; // forward conversions per frame
  const rWindow: number[] = []; // reverse conversions per frame

  for (let f = 0; f < SIM_FRAMES; f++) {
    let fThis = 0, rThis = 0;

    // Drift each particle by a small random walk; clamp to flask interior.
    for (const p of positions) {
      const dx = (rng() - 0.5) * 2 * driftAmp;
      const dy = (rng() - 0.5) * 2 * driftAmp;
      p.x = Math.max(margin, Math.min(FLASK_W - margin, p.x + dx));
      p.y = Math.max(margin, Math.min(FLASK_H - margin, p.y + dy));

      // Conversion attempt
      if (!p.isB) {
        if (rng() < k_f) { p.isB = true; fThis++; }
      } else {
        if (rng() < k_r) { p.isB = false; rThis++; }
      }
    }

    fWindow.push(fThis);
    rWindow.push(rThis);
    if (fWindow.length > FPS) fWindow.shift();
    if (rWindow.length > FPS) rWindow.shift();

    const rateF = fWindow.reduce((s, v) => s + v, 0);
    const rateR = rWindow.reduce((s, v) => s + v, 0);
    const countB = positions.filter((p) => p.isB).length;
    const countA = N_PARTICLES - countB;

    states.push({
      particles: positions.map((p) => ({ x: p.x, y: p.y, isB: p.isB })),
      rateF,
      rateR,
      countA,
      countB,
    });
  }
  return states;
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function rateToY(rate: number, maxRate: number): number {
  // chart Y axis: top = high rate, bottom = 0
  const usable = CHART_H - 80;
  return CHART_Y + 20 + usable - (rate / maxRate) * usable;
}
function timeToX(simFrame: number, simFramesTotal: number): number {
  return CHART_X + 60 + (simFrame / simFramesTotal) * (CHART_W - 80);
}

// ── Component ────────────────────────────────────────────────────────────────
export const DynamicBalanceScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Build the simulation once per render (deterministic).
  const states = useMemo(buildSimulation, []);
  const SIM_FRAMES = F_SIM_END - F_SUB_END;

  // Title fade
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, F_TITLE_END], [0, 1], { extrapolateRight: 'clamp' });

  // Flask + chart fade in
  const flaskOp = interpolate(frame, [F_TITLE_END, F_SUB_END], [0, 1], { extrapolateRight: 'clamp' });

  // Current simulation index (clamped while sim is active or after end)
  const simIndex = Math.max(0, Math.min(SIM_FRAMES - 1, frame - F_SUB_END));
  const cur = states[simIndex];

  // For chart: build a polyline of all forward/reverse rates up to current sim frame
  const maxRate = 22; // visual ceiling (30 * (k_f+k_r) ≈ 1.8/frame * fps = 54, but plateau ≈ 12)
  const fPath = states.slice(0, simIndex + 1)
    .map((s, i) => `${i === 0 ? 'M' : 'L'} ${timeToX(i, SIM_FRAMES)} ${rateToY(s.rateF, maxRate)}`)
    .join(' ');
  const rPath = states.slice(0, simIndex + 1)
    .map((s, i) => `${i === 0 ? 'M' : 'L'} ${timeToX(i, SIM_FRAMES)} ${rateToY(s.rateR, maxRate)}`)
    .join(' ');

  // Equilibrium highlight (after the rates have visibly converged)
  const eqHiliteOp = interpolate(frame, [F_SIM_END - 60, F_HILITE_END], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  // Final caption
  const captionOp = interpolate(frame, [F_HILITE_END, F_CAP_END], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  // Counter pulses — small pulse each time the count flips
  const countPulse = (target: number, last: number) => (target !== last ? 1.18 : 1.0);
  const prev = states[Math.max(0, simIndex - 1)] ?? cur;
  const aPulse = countPulse(cur.countA, prev.countA);
  const bPulse = countPulse(cur.countB, prev.countB);

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      {/* ── Title ── */}
      <div style={{ position: 'absolute', top: 30, left: 0, right: 0, textAlign: 'center' }}>
        <h1 style={{
          fontSize: 56, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleScale})`,
        }}>
          Dynamic Equilibrium — Two Directions, One Standoff
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          A ⇌ B   ·   forward rate climbs, reverse rate catches up, both lock onto a common value.
        </p>
      </div>

      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: 'absolute', inset: 0, opacity: flaskOp }}>
        <defs>
          <marker id="db-arr-r" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">
            <path d="M 0 0 L 10 5 L 0 10 z" fill={PAI_THEME.colors.forwardArrow} />
          </marker>
          <marker id="db-arr-l" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse">
            <path d="M 10 0 L 0 5 L 10 10 z" fill={PAI_THEME.colors.reverseArrow} />
          </marker>
          <marker id="db-axis-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M 0 0 L 10 5 L 0 10 z" fill={PAI_THEME.colors.text} />
          </marker>
        </defs>

        {/* ─────────────────────── FLASK ─────────────────────── */}
        <g transform={`translate(${FLASK_X}, ${FLASK_Y})`}>
          {/* Flask body */}
          <rect x={0} y={0} width={FLASK_W} height={FLASK_H} rx={28} ry={28}
            fill={PAI_THEME.colors.backgroundDark}
            stroke={PAI_THEME.colors.textMuted}
            strokeWidth={3} />

          {/* Reaction equation banner inside flask */}
          <g transform="translate(380, 56)">
            <text x={-150} y={0} fontSize={42} fontWeight={700} fill={PAI_THEME.colors.reactant} textAnchor="middle">A</text>
            <line x1={-100} y1={-12} x2={100} y2={-12} stroke={PAI_THEME.colors.forwardArrow} strokeWidth={4} markerEnd="url(#db-arr-r)" />
            <line x1={100}  y1={6}   x2={-100} y2={6}   stroke={PAI_THEME.colors.reverseArrow} strokeWidth={4} markerEnd="url(#db-arr-l)" />
            <text x={150} y={0} fontSize={42} fontWeight={700} fill={PAI_THEME.colors.product} textAnchor="middle">B</text>
          </g>

          {/* Particles */}
          {cur.particles.map((p, i) => (
            <g key={i}>
              <circle
                cx={p.x}
                cy={p.y + 100} // shift below the equation banner
                r={14}
                fill={p.isB ? PAI_THEME.colors.product : PAI_THEME.colors.reactant}
                stroke={PAI_THEME.colors.text}
                strokeWidth={1.5} />
              <text
                x={p.x}
                y={p.y + 105}
                fontSize={14}
                fontWeight={700}
                fill={PAI_THEME.colors.text}
                textAnchor="middle">
                {p.isB ? 'B' : 'A'}
              </text>
            </g>
          ))}

          {/* Population counters (bottom of flask) */}
          <g transform={`translate(0, ${FLASK_H - 70})`}>
            <rect x={40} y={0} width={320} height={50} rx={8}
              fill={PAI_THEME.colors.reactantLight} opacity={0.18}
              stroke={PAI_THEME.colors.reactant} strokeWidth={1.5} />
            <text x={60}  y={32} fontSize={22} fontWeight={700} fill={PAI_THEME.colors.reactant}>[A] count =</text>
            <text x={290} y={32} fontSize={28} fontWeight={700} fill={PAI_THEME.colors.reactant}
              textAnchor="end" style={{ transform: `scale(${aPulse})`, transformOrigin: '290px 25px', transformBox: 'fill-box' }}>
              {cur.countA}
            </text>

            <rect x={400} y={0} width={320} height={50} rx={8}
              fill={PAI_THEME.colors.productLight} opacity={0.18}
              stroke={PAI_THEME.colors.product} strokeWidth={1.5} />
            <text x={420} y={32} fontSize={22} fontWeight={700} fill={PAI_THEME.colors.product}>[B] count =</text>
            <text x={650} y={32} fontSize={28} fontWeight={700} fill={PAI_THEME.colors.product}
              textAnchor="end" style={{ transform: `scale(${bPulse})`, transformOrigin: '650px 25px', transformBox: 'fill-box' }}>
              {cur.countB}
            </text>
          </g>
        </g>

        {/* ─────────────────────── CHART ─────────────────────── */}
        <g>
          {/* Chart frame */}
          <rect x={CHART_X - 20} y={CHART_Y - 60} width={CHART_W + 40} height={CHART_H + 120} rx={20}
            fill={PAI_THEME.colors.backgroundDark} stroke={PAI_THEME.colors.textMuted} strokeWidth={2} />

          <text x={CHART_X + CHART_W / 2} y={CHART_Y - 24} fontSize={28} fontWeight={700}
            fill={PAI_THEME.colors.text} textAnchor="middle">
            Forward and Reverse Rates vs Time
          </text>

          {/* Axes */}
          <line x1={CHART_X + 60} y1={CHART_Y + CHART_H - 60} x2={CHART_X + CHART_W - 20} y2={CHART_Y + CHART_H - 60}
            stroke={PAI_THEME.colors.text} strokeWidth={2} markerEnd="url(#db-axis-arr)" />
          <line x1={CHART_X + 60} y1={CHART_Y + CHART_H - 60} x2={CHART_X + 60} y2={CHART_Y + 20}
            stroke={PAI_THEME.colors.text} strokeWidth={2} markerEnd="url(#db-axis-arr)" />

          <text x={CHART_X + CHART_W - 50} y={CHART_Y + CHART_H - 24} fontSize={20} fontWeight={700}
            fill={PAI_THEME.colors.text} textAnchor="middle">time</text>
          <text x={CHART_X + 30} y={CHART_Y + 30} fontSize={20} fontWeight={700}
            fill={PAI_THEME.colors.text} textAnchor="middle">rate</text>

          {/* Reference dashed line at expected r_eq ≈ k_f * A_eq = 0.020 * 20 = 0.40/frame ≈ 12 over 30-frame window */}
          {(() => {
            const yEq = rateToY(12, maxRate);
            return (
              <g opacity={0.6}>
                <line x1={CHART_X + 60} y1={yEq} x2={CHART_X + CHART_W - 20} y2={yEq}
                  stroke={PAI_THEME.colors.textMuted} strokeWidth={1.5} strokeDasharray="6 6" />
                <text x={CHART_X + CHART_W - 30} y={yEq - 8} fontSize={18}
                  fill={PAI_THEME.colors.textMuted} textAnchor="end">r_eq</text>
              </g>
            );
          })()}

          {/* Equilibrium-region highlight (right portion of chart, fades in late) */}
          <rect
            x={timeToX(SIM_FRAMES * 0.55, SIM_FRAMES)}
            y={CHART_Y + 20}
            width={timeToX(SIM_FRAMES, SIM_FRAMES) - timeToX(SIM_FRAMES * 0.55, SIM_FRAMES)}
            height={CHART_H - 80}
            fill={PAI_THEME.colors.success}
            opacity={eqHiliteOp * 0.18} />
          <text
            x={(timeToX(SIM_FRAMES * 0.55, SIM_FRAMES) + timeToX(SIM_FRAMES, SIM_FRAMES)) / 2}
            y={CHART_Y + 60}
            fontSize={24} fontWeight={700} fill={PAI_THEME.colors.success}
            textAnchor="middle" opacity={eqHiliteOp}>
            EQUILIBRIUM
          </text>
          <text
            x={(timeToX(SIM_FRAMES * 0.55, SIM_FRAMES) + timeToX(SIM_FRAMES, SIM_FRAMES)) / 2}
            y={CHART_Y + 88}
            fontSize={18} fill={PAI_THEME.colors.success}
            textAnchor="middle" opacity={eqHiliteOp}>
            r_forward = r_reverse  ·  net change = 0
          </text>

          {/* Forward rate curve */}
          <path d={fPath} fill="none" stroke={PAI_THEME.colors.forwardArrow} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />
          {/* Reverse rate curve */}
          <path d={rPath} fill="none" stroke={PAI_THEME.colors.reverseArrow} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />

          {/* Live readout dots at the leading edge of each curve */}
          {(() => {
            const lx = timeToX(simIndex, SIM_FRAMES);
            const fy = rateToY(cur.rateF, maxRate);
            const ry = rateToY(cur.rateR, maxRate);
            return (
              <>
                <circle cx={lx} cy={fy} r={9} fill={PAI_THEME.colors.forwardArrow} stroke={PAI_THEME.colors.text} strokeWidth={2} />
                <circle cx={lx} cy={ry} r={9} fill={PAI_THEME.colors.reverseArrow} stroke={PAI_THEME.colors.text} strokeWidth={2} />
              </>
            );
          })()}

          {/* Legend */}
          <g transform={`translate(${CHART_X + 80}, ${CHART_Y + CHART_H + 20})`}>
            <rect x={0}   y={0} width={20} height={6} fill={PAI_THEME.colors.forwardArrow} />
            <text x={28}  y={8} fontSize={20} fill={PAI_THEME.colors.text}>forward rate (A → B)</text>

            <rect x={320} y={0} width={20} height={6} fill={PAI_THEME.colors.reverseArrow} />
            <text x={348} y={8} fontSize={20} fill={PAI_THEME.colors.text}>reverse rate (B → A)</text>
          </g>
        </g>
      </svg>

      {/* ── Final caption ── */}
      <div style={{
        position: 'absolute', bottom: 36, left: 0, right: 0, textAlign: 'center',
        fontSize: 30, fontWeight: 700, color: PAI_THEME.colors.text, opacity: captionOp,
      }}>
        At equilibrium the molecules never stop reacting — they just match each other, exactly.
      </div>
    </AbsoluteFill>
  );
};
