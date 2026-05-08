/**
 * TangentEmergenceScene — secant pivots into tangent as Δx → 0.
 *
 * Setup: f(x) = 0.4x² on the domain [0, 5]. Anchor point P at x = 2,
 * y = 1.6. Secant connects P to a second point at x = 2 + Δx.
 *
 * Frames @ 30fps (24 s = 720 frames):
 *   0–60     title fade
 *   60–150   curve appears, point P pinned (3 s)
 *   150–240  initial wide secant — Δx = 2.5 (3 s)
 *   240–540  Δx interpolates from 2.5 → 0.05 (10 s) — the magic happens here
 *   540–660  hold tangent + display f'(2) = 1.6 (4 s)
 *   660–720  caption fade in (2 s)
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Plot geometry ───────────────────────────────────────────────────────────
const PLOT_X0 = 320;
const PLOT_Y0 = 160;
const PLOT_W = 1280;
const PLOT_H = 760;
const X_RANGE: [number, number] = [0, 5];
const Y_RANGE: [number, number] = [0, 6];

const xToPx = (x: number) => PLOT_X0 + ((x - X_RANGE[0]) / (X_RANGE[1] - X_RANGE[0])) * PLOT_W;
const yToPx = (y: number) => PLOT_Y0 + PLOT_H - ((y - Y_RANGE[0]) / (Y_RANGE[1] - Y_RANGE[0])) * PLOT_H;

const fn = (x: number) => 0.4 * x * x;
const fnPrime = (x: number) => 0.8 * x;

// Curve as a polyline string
function curvePath(): string {
  const samples = 200;
  const pts: string[] = [];
  for (let i = 0; i <= samples; i++) {
    const x = X_RANGE[0] + (i / samples) * (X_RANGE[1] - X_RANGE[0]);
    const y = fn(x);
    pts.push(`${xToPx(x).toFixed(2)},${yToPx(y).toFixed(2)}`);
  }
  return pts.join(' ');
}

// ── Frame anchors ──────────────────────────────────────────────────────────
const F_TITLE_END = 60;
const F_CURVE_IN = 150;
const F_DELTA_HOLD = 240;
const F_DELTA_SHRINK_END = 540;
const F_TANGENT_HOLD = 660;
const F_END = 720;

const ANCHOR_X = 2;
const ANCHOR_Y = fn(ANCHOR_X);
const TANGENT_SLOPE = fnPrime(ANCHOR_X);

export const TangentEmergenceScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });
  const curveOp = interpolate(frame, [60, F_CURVE_IN], [0, 1], { extrapolateRight: 'clamp' });

  // Δx schedule
  const dxStart = 2.5;
  const dxEnd = 0.05;
  let dx: number;
  if (frame < F_DELTA_HOLD) {
    dx = dxStart;
  } else if (frame < F_DELTA_SHRINK_END) {
    const t = (frame - F_DELTA_HOLD) / (F_DELTA_SHRINK_END - F_DELTA_HOLD);
    dx = dxStart + (dxEnd - dxStart) * t;
  } else {
    dx = dxEnd;
  }

  // Second-point + secant slope
  const x2 = ANCHOR_X + dx;
  const y2 = fn(x2);
  const secantSlope = (y2 - ANCHOR_Y) / dx;

  // Show tangent only after Δx is fully shrunk
  const tangentOp = interpolate(frame, [F_DELTA_SHRINK_END - 30, F_DELTA_SHRINK_END + 30], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const captionOp = interpolate(frame, [F_TANGENT_HOLD, F_TANGENT_HOLD + 60], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  // Secant line: extend the line through (ANCHOR_X, ANCHOR_Y) with slope secantSlope across the visible x range
  const secantYL = ANCHOR_Y + secantSlope * (X_RANGE[0] - ANCHOR_X);
  const secantYR = ANCHOR_Y + secantSlope * (X_RANGE[1] - ANCHOR_X);

  // Tangent line
  const tangentYL = ANCHOR_Y + TANGENT_SLOPE * (X_RANGE[0] - ANCHOR_X);
  const tangentYR = ANCHOR_Y + TANGENT_SLOPE * (X_RANGE[1] - ANCHOR_X);

  // Axis grid
  const xTicks = [0, 1, 2, 3, 4, 5];
  const yTicks = [0, 1, 2, 3, 4, 5, 6];

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      {/* Title */}
      <div style={{ position: 'absolute', top: 30, left: 0, right: 0, textAlign: 'center' }}>
        <h1 style={{
          fontSize: 56, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleScale})`,
        }}>
          Tangent Line as the Limit of Secants
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          Watch Δx shrink toward zero. The secant pivots and locks into the tangent.
        </p>
      </div>

      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: 'absolute', inset: 0, opacity: curveOp }}>
        {/* Plot frame */}
        <rect x={PLOT_X0} y={PLOT_Y0} width={PLOT_W} height={PLOT_H}
          fill={PAI_THEME.colors.backgroundAlt} stroke={PAI_THEME.colors.textMuted} strokeWidth={2} />

        {/* Grid */}
        {xTicks.map((x) => (
          <g key={`x-${x}`}>
            <line x1={xToPx(x)} y1={PLOT_Y0} x2={xToPx(x)} y2={PLOT_Y0 + PLOT_H}
              stroke="#1e293b" strokeWidth={1} />
            <text x={xToPx(x)} y={PLOT_Y0 + PLOT_H + 30}
              fill={PAI_THEME.colors.textMuted} fontSize={20} textAnchor="middle">{x}</text>
          </g>
        ))}
        {yTicks.map((y) => (
          <g key={`y-${y}`}>
            <line x1={PLOT_X0} y1={yToPx(y)} x2={PLOT_X0 + PLOT_W} y2={yToPx(y)}
              stroke="#1e293b" strokeWidth={1} />
            <text x={PLOT_X0 - 14} y={yToPx(y) + 8}
              fill={PAI_THEME.colors.textMuted} fontSize={20} textAnchor="end">{y}</text>
          </g>
        ))}

        {/* Axis labels */}
        <text x={PLOT_X0 + PLOT_W / 2} y={PLOT_Y0 + PLOT_H + 70}
          fill={PAI_THEME.colors.text} fontSize={26} fontWeight={700} textAnchor="middle">x</text>
        <text x={PLOT_X0 - 60} y={PLOT_Y0 + PLOT_H / 2}
          fill={PAI_THEME.colors.text} fontSize={26} fontWeight={700} textAnchor="middle"
          transform={`rotate(-90 ${PLOT_X0 - 60} ${PLOT_Y0 + PLOT_H / 2})`}>f(x)</text>

        {/* Curve f(x) = 0.4x² */}
        <polyline points={curvePath()}
          fill="none" stroke={PAI_THEME.colors.curve} strokeWidth={5} strokeLinecap="round" />
        <text x={xToPx(4.6)} y={yToPx(fn(4.6)) - 18}
          fill={PAI_THEME.colors.curve} fontSize={28} fontWeight={700} textAnchor="middle">f(x) = 0.4x²</text>

        {/* Secant line (visible until tangent takes over) */}
        {frame >= F_CURVE_IN && (
          <g opacity={1 - tangentOp}>
            <line
              x1={xToPx(X_RANGE[0])} y1={yToPx(secantYL)}
              x2={xToPx(X_RANGE[1])} y2={yToPx(secantYR)}
              stroke={PAI_THEME.colors.secant} strokeWidth={4} strokeDasharray="8 6" />
            {/* Second point Q */}
            <circle cx={xToPx(x2)} cy={yToPx(y2)} r={12}
              fill={PAI_THEME.colors.secant} stroke={PAI_THEME.colors.text} strokeWidth={2} />
            <text x={xToPx(x2) + 18} y={yToPx(y2) - 10}
              fill={PAI_THEME.colors.secant} fontSize={26} fontWeight={700}>Q</text>
            {/* Δx bracket beneath the curve */}
            <line x1={xToPx(ANCHOR_X)} y1={yToPx(0) + 10}
              x2={xToPx(x2)} y2={yToPx(0) + 10}
              stroke={PAI_THEME.colors.secant} strokeWidth={3} />
            <line x1={xToPx(ANCHOR_X)} y1={yToPx(0) + 4}
              x2={xToPx(ANCHOR_X)} y2={yToPx(0) + 16}
              stroke={PAI_THEME.colors.secant} strokeWidth={3} />
            <line x1={xToPx(x2)} y1={yToPx(0) + 4}
              x2={xToPx(x2)} y2={yToPx(0) + 16}
              stroke={PAI_THEME.colors.secant} strokeWidth={3} />
            <text x={(xToPx(ANCHOR_X) + xToPx(x2)) / 2} y={yToPx(0) + 38}
              fill={PAI_THEME.colors.secant} fontSize={22} fontWeight={700} textAnchor="middle">
              Δx = {dx.toFixed(2)}
            </text>
          </g>
        )}

        {/* Tangent line (fades in after secant collapse) */}
        {frame > F_DELTA_SHRINK_END - 60 && (
          <line
            x1={xToPx(X_RANGE[0])} y1={yToPx(tangentYL)}
            x2={xToPx(X_RANGE[1])} y2={yToPx(tangentYR)}
            stroke={PAI_THEME.colors.tangent} strokeWidth={5} strokeLinecap="round"
            opacity={tangentOp} />
        )}

        {/* Anchor point P (always visible after curve appears) */}
        {frame >= F_CURVE_IN && (
          <g>
            <circle cx={xToPx(ANCHOR_X)} cy={yToPx(ANCHOR_Y)} r={14}
              fill={PAI_THEME.colors.point} stroke={PAI_THEME.colors.text} strokeWidth={3} />
            <text x={xToPx(ANCHOR_X) - 18} y={yToPx(ANCHOR_Y) + 8}
              fill={PAI_THEME.colors.point} fontSize={28} fontWeight={700} textAnchor="end">P</text>
          </g>
        )}

        {/* Live slope readout (top-right of plot area) */}
        {frame >= F_CURVE_IN && (
          <g>
            <rect x={1500} y={200} width={400} height={180} rx={12}
              fill={PAI_THEME.colors.backgroundAlt} stroke={PAI_THEME.colors.textMuted} strokeWidth={2} />
            <text x={1700} y={234} fill={PAI_THEME.colors.text}
              fontSize={26} fontWeight={700} textAnchor="middle">slope of secant</text>
            <text x={1700} y={272} fill={PAI_THEME.colors.secant}
              fontSize={24} fontFamily={PAI_THEME.typography.fontFamilyMono} textAnchor="middle">
              [f(2+Δx) − f(2)] / Δx
            </text>
            <text x={1700} y={324} fill={PAI_THEME.colors.tangent}
              fontSize={48} fontWeight={700} textAnchor="middle">
              = {secantSlope.toFixed(3)}
            </text>
            <text x={1700} y={362} fill={PAI_THEME.colors.textMuted}
              fontSize={18} textAnchor="middle" fontStyle="italic">
              true tangent slope: f'(2) = {TANGENT_SLOPE.toFixed(2)}
            </text>
          </g>
        )}
      </svg>

      {/* Final caption */}
      <div style={{
        position: 'absolute', top: 990, left: 0, right: 0, textAlign: 'center',
        fontSize: 28, fontWeight: 700, color: PAI_THEME.colors.tangent,
        opacity: captionOp,
      }}>
        f'(2) is the slope of the curve at x = 2 — exactly what a perfect ruler resting on the curve would show.
      </div>
    </AbsoluteFill>
  );
};
