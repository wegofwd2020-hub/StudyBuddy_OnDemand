/**
 * ShmScene — mass-on-spring undergoing simple harmonic motion.
 *
 * Physics:
 *   x(t) = A cos(ω t),  ω = 2π / T,  T = 4 s,  A = 180 px
 *   v(t) = -A ω sin(ω t)
 *
 * Layout:
 *   Title + equation (top)
 *   Mass-on-spring illustration (middle): wall on left, zigzag spring, mass.
 *   Phase plot below, x(t) tracing in real time as the mass moves.
 *
 * Frames @ 30fps (24s total = 720 frames):
 *   0–60   title + equation fade in
 *   60–660 oscillation runs (20 s of physics → 5 full cycles at T=4s)
 *   660–720 caption fade
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';
import { PlotFrame, xToPx, yToPx, buildPath, type Plot } from '../plot';

// ── Physics constants ────────────────────────────────────────────────────────
const A_PX = 180;          // Amplitude in pixels (visual scale)
const PERIOD_S = 4;        // Seconds per cycle
const OMEGA = (2 * Math.PI) / PERIOD_S;
const T_MOTION_END_FRAMES = 660;
const T_MOTION_START_FRAMES = 60;

// ── Spring drawing ───────────────────────────────────────────────────────────
function springPath(x0: number, x1: number, y: number, coils = 18, amp = 24): string {
  // Zigzag from (x0, y) to (x1, y), `coils` triangles tall ±amp.
  const dx = (x1 - x0) / (coils * 2);
  const pts: string[] = [`M ${x0},${y}`];
  for (let i = 1; i <= coils * 2; i++) {
    const xi = x0 + i * dx;
    const yi = y + (i % 2 === 0 ? 0 : (i % 4 === 1 ? -amp : amp));
    pts.push(`L ${xi.toFixed(1)},${yi.toFixed(1)}`);
  }
  pts.push(`L ${x1},${y}`);
  return pts.join(' ');
}

export const ShmScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Timing ─────────────────────────────────────────────────────────────────
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });
  const captionOp = interpolate(frame, [600, 660], [0, 1], { extrapolateRight: 'clamp' });

  // Physics-time t (only ticks during the motion window).
  const motionFrame = Math.max(0, Math.min(frame - T_MOTION_START_FRAMES, T_MOTION_END_FRAMES - T_MOTION_START_FRAMES));
  const t = motionFrame / fps; // seconds since motion began
  const x = A_PX * Math.cos(OMEGA * t);

  // ── Spring + mass geometry ─────────────────────────────────────────────────
  const wallX = 360;
  const equilibriumX = 960;
  const massX = equilibriumX + x;
  const massY = 360;
  const massSize = 110;

  // ── Phase plot below ───────────────────────────────────────────────────────
  const PW = 1400, PH = 360;
  const plot: Plot = {
    width: PW, height: PH,
    pad: { l: 100, r: 60, t: 30, b: 80 },
    xRange: [0, 20],
    yRange: [-A_PX, A_PX],
    xTicks: [0, 4, 8, 12, 16, 20],
    yTicks: [-A_PX, 0, A_PX],
    xLabel: 't (seconds)',
    yLabel: 'x (displacement)',
  };
  // Reveal-fraction is the fraction of the 20-second t-axis we've traversed.
  const reveal = Math.max(0, Math.min(t / 20, 1));

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      flexDirection: 'column', alignItems: 'center', padding: 40,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      <h1 style={{
        fontSize: 56, color: PAI_THEME.colors.text, margin: '20px 0 4px',
        opacity: titleOp, transform: `scale(${titleScale})`, textAlign: 'center',
      }}>
        Simple Harmonic Motion
      </h1>
      <p style={{
        fontSize: 28, color: PAI_THEME.colors.accentLight, margin: '0 0 16px',
        opacity: subOp, fontStyle: 'italic',
      }}>
        x(t) = A cos(ω t)    ·    ω = 2π / T    ·    T = 4 s
      </p>

      {/* Mass-on-spring illustration */}
      <svg width={1600} height={460} style={{ marginTop: 8 }}>
        {/* Wall hatching */}
        <rect x={wallX - 60} y={massY - 110} width={60} height={220}
          fill={PAI_THEME.colors.backgroundAlt} stroke={PAI_THEME.colors.textDark} strokeWidth={2} />
        {Array.from({ length: 9 }).map((_, i) => (
          <line key={i}
            x1={wallX - 60} y1={massY - 110 + (i + 1) * 22}
            x2={wallX} y2={massY - 110 + (i + 1) * 22 - 22}
            stroke={PAI_THEME.colors.textMuted} strokeWidth={1.5} />
        ))}
        {/* Equilibrium-line marker */}
        <line x1={equilibriumX} y1={massY + 80} x2={equilibriumX} y2={massY + 130}
          stroke={PAI_THEME.colors.textDark} strokeDasharray="6 6" strokeWidth={2} />
        <text x={equilibriumX} y={massY + 158}
          fill={PAI_THEME.colors.textMuted} fontSize={18} textAnchor="middle">
          equilibrium (x = 0)
        </text>
        {/* Spring */}
        <path d={springPath(wallX, massX - massSize / 2, massY)}
          fill="none" stroke={PAI_THEME.colors.accentLight} strokeWidth={4}
          strokeLinejoin="round" strokeLinecap="round" />
        {/* Mass */}
        <rect x={massX - massSize / 2} y={massY - massSize / 2}
          width={massSize} height={massSize}
          rx={14} ry={14}
          fill={PAI_THEME.colors.accent} stroke={PAI_THEME.colors.accentDark} strokeWidth={3} />
        <text x={massX} y={massY + 8} fill={PAI_THEME.colors.text}
          fontSize={32} fontWeight={700} textAnchor="middle">m</text>
        {/* Position arrow + readout */}
        <line x1={equilibriumX} y1={massY - 90} x2={massX} y2={massY - 90}
          stroke={PAI_THEME.colors.warning} strokeWidth={3}
          markerEnd="url(#arrowhead)" />
        <defs>
          <marker id="arrowhead" markerWidth={10} markerHeight={10} refX={9} refY={3} orient="auto">
            <polygon points="0 0, 10 3, 0 6" fill={PAI_THEME.colors.warning} />
          </marker>
        </defs>
        <text x={(equilibriumX + massX) / 2} y={massY - 100}
          fill={PAI_THEME.colors.warning} fontSize={22} fontWeight={700} textAnchor="middle">
          x = {x.toFixed(0)} px
        </text>
      </svg>

      {/* Phase plot */}
      <svg width={PW} height={PH} style={{ marginTop: 12 }}>
        <PlotFrame p={plot} title="Displacement vs time" />
        {/* Trace x(t) over [0, t] */}
        <polyline
          points={buildPath(plot, (tt) => A_PX * Math.cos(OMEGA * tt), [0, 20], reveal, 400)}
          fill="none" stroke={PAI_THEME.colors.accent} strokeWidth={4} strokeLinecap="round" />
        {/* Current-time cursor + dot */}
        {t > 0 && t < 20 && (
          <>
            <line x1={xToPx(plot, t)} y1={plot.pad.t}
              x2={xToPx(plot, t)} y2={plot.pad.t + plot.height - plot.pad.t - plot.pad.b}
              stroke={PAI_THEME.colors.warning} strokeWidth={2} strokeDasharray="6 6" />
            <circle cx={xToPx(plot, t)} cy={yToPx(plot, x)} r={9}
              fill={PAI_THEME.colors.warning} stroke={PAI_THEME.colors.text} strokeWidth={2} />
          </>
        )}
      </svg>

      <div style={{
        marginTop: 18, color: PAI_THEME.colors.text, fontSize: 26,
        opacity: captionOp, textAlign: 'center', maxWidth: 1500,
      }}>
        Period T = 4 s — the motion repeats every 4 seconds. Position is fastest through equilibrium and zero at the turning points.
      </div>
    </AbsoluteFill>
  );
};
