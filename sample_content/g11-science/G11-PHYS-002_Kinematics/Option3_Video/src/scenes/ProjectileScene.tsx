import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PAI_THEME } from '../theme';
import { PlotFrame, xToPx, yToPx, type Plot } from '../plot';

// Projectile: v = 20 m/s, theta = 60 deg
const V = 20;
const THETA = (60 * Math.PI) / 180;
const G = 9.8;
const VX = V * Math.cos(THETA);
const VY = V * Math.sin(THETA);
const T_FLIGHT = (2 * VY) / G;
const X_RANGE = VX * T_FLIGHT;
const Y_PEAK = (VY * VY) / (2 * G);

const yOf = (x: number) =>
  Math.tan(THETA) * x - (G * x * x) / (2 * V * V * Math.cos(THETA) * Math.cos(THETA));

export const ProjectileScene: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });

  // Phases: 0-90 title, 90-510 flight (14s), 510-660 final + labels
  const t = interpolate(frame, [90, 510], [0, T_FLIGHT], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const x = VX * t;
  const yLive = Math.max(0, VY * t - 0.5 * G * t * t);
  const vyLive = VY - G * t;

  const PW = 1500, PH = 760;
  const p: Plot = {
    width: PW, height: PH, pad: { l: 100, r: 80, t: 60, b: 80 },
    xRange: [0, 40], yRange: [0, 20], xTicks: [0, 10, 20, 30, 40],
    yTicks: [0, 5, 10, 15, 20], xLabel: 'x (m)', yLabel: 'y (m)',
  };

  // Trace points up to current t
  const tracePts: string[] = [];
  const N = 200;
  for (let i = 0; i <= N; i++) {
    const ti = (i / N) * t;
    const xi = VX * ti;
    const yi = VY * ti - 0.5 * G * ti * ti;
    tracePts.push(`${xToPx(p, xi).toFixed(1)},${yToPx(p, yi).toFixed(1)}`);
  }
  // Faint full guide
  const guidePts: string[] = [];
  for (let i = 0; i <= N; i++) {
    const xi = (i / N) * X_RANGE;
    guidePts.push(`${xToPx(p, xi).toFixed(1)},${yToPx(p, yOf(xi)).toFixed(1)}`);
  }

  const labelOp = interpolate(frame, [510, 600], [0, 1], { extrapolateRight: 'clamp' });

  // Ball position
  const ballX = xToPx(p, x);
  const ballY = yToPx(p, yLive);

  // Vector arrow length scaling
  const VEC_SCALE = 6; // px per (m/s)

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      padding: 40, fontFamily: PAI_THEME.typography.fontFamily,
      flexDirection: 'column', alignItems: 'center',
    }}>
      <h1 style={{
        fontSize: 56, color: PAI_THEME.colors.text, margin: '0 0 6px',
        opacity: titleOp, textAlign: 'center',
      }}>
        Projectile Motion — v = 20 m/s, θ = 60°
      </h1>
      <p style={{
        fontSize: 22, color: PAI_THEME.colors.accentLight, margin: '0 0 20px',
        opacity: titleOp, fontStyle: 'italic',
      }}>
        Independent horizontal and vertical motions combine into the parabolic flight path.
      </p>

      <svg width={PW} height={PH}>
        <PlotFrame p={p} />
        {/* Faint full path */}
        <polyline points={guidePts.join(' ')}
          fill="none" stroke={PAI_THEME.colors.textMuted} strokeWidth={2}
          strokeDasharray="6 6" opacity={0.4} />
        {/* Live trace */}
        <polyline points={tracePts.join(' ')}
          fill="none" stroke={PAI_THEME.colors.accent} strokeWidth={5} strokeLinecap="round" />
        {/* Ball */}
        <circle cx={ballX} cy={ballY} r={14} fill={PAI_THEME.colors.error} stroke="white" strokeWidth={3} />
        {/* Velocity vectors */}
        {t > 0.05 && t < T_FLIGHT - 0.05 && (
          <g>
            {/* horizontal vx vector — constant in length */}
            <defs>
              <marker id="ah-vx" viewBox="0 0 10 10" refX={9} refY={5} markerWidth={8} markerHeight={8} orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill={PAI_THEME.colors.warning} />
              </marker>
              <marker id="ah-vy" viewBox="0 0 10 10" refX={9} refY={5} markerWidth={8} markerHeight={8} orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill={PAI_THEME.colors.success} />
              </marker>
            </defs>
            <line x1={ballX} y1={ballY} x2={ballX + VX * VEC_SCALE} y2={ballY}
              stroke={PAI_THEME.colors.warning} strokeWidth={4} markerEnd="url(#ah-vx)" />
            <text x={ballX + VX * VEC_SCALE + 6} y={ballY - 8}
              fill={PAI_THEME.colors.warning} fontSize={20} fontWeight={600}>vₓ</text>
            <line x1={ballX} y1={ballY} x2={ballX} y2={ballY - vyLive * VEC_SCALE}
              stroke={PAI_THEME.colors.success} strokeWidth={4} markerEnd="url(#ah-vy)" />
            <text x={ballX + 8} y={ballY - vyLive * VEC_SCALE - 6}
              fill={PAI_THEME.colors.success} fontSize={20} fontWeight={600}>v_y</text>
          </g>
        )}
        {/* Final labels */}
        <g opacity={labelOp}>
          <line x1={xToPx(p, X_RANGE / 2)} y1={yToPx(p, 0)}
            x2={xToPx(p, X_RANGE / 2)} y2={yToPx(p, Y_PEAK)}
            stroke={PAI_THEME.colors.warning} strokeWidth={2} strokeDasharray="6 4" />
          <circle cx={xToPx(p, X_RANGE / 2)} cy={yToPx(p, Y_PEAK)} r={9}
            fill={PAI_THEME.colors.warning} stroke="white" strokeWidth={2} />
          <text x={xToPx(p, X_RANGE / 2) + 12} y={yToPx(p, Y_PEAK) - 14}
            fill={PAI_THEME.colors.warning} fontSize={26} fontWeight={700}>peak: 15.3 m</text>
          <circle cx={xToPx(p, X_RANGE)} cy={yToPx(p, 0)} r={9}
            fill={PAI_THEME.colors.error} stroke="white" strokeWidth={2} />
          <text x={xToPx(p, X_RANGE) - 10} y={yToPx(p, 0) + 38}
            fill={PAI_THEME.colors.error} fontSize={22} fontWeight={600} textAnchor="middle">
            range ≈ 35.3 m   ·   T ≈ 3.53 s
          </text>
        </g>
      </svg>

      <div style={{
        marginTop: 24, color: PAI_THEME.colors.text,
        fontFamily: PAI_THEME.typography.fontFamilyMono, fontSize: 22,
      }}>
        t = {t.toFixed(2)} s    ·    x = {x.toFixed(1)} m    ·    y = {yLive.toFixed(1)} m
      </div>
    </AbsoluteFill>
  );
};
