/**
 * WaveSuperpositionScene — two travelling sine waves combining into their sum.
 *
 * Physics:
 *   y1(x, t) = A sin(k x - ω t)
 *   y2(x, t) = A sin(k x - ω t + φ(t))     where φ sweeps 0 → 2π over 24 s
 *   y_sum    = y1 + y2
 *
 * The phase-difference sweep is the whole point: at φ=0 the sum is fully
 * constructive (amplitude 2A); at φ=π fully destructive (amplitude 0); at
 * φ=2π back to constructive. One continuous clip, three lessons in sequence.
 *
 * Frames @ 30fps (26s total = 780 frames):
 *   0–60   title + equations fade in
 *   60–780 animation (24 s sweep)
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';
import { PlotFrame, type Plot, fullPath } from '../plot';

const SWEEP_S = 24;
const OMEGA = 1.0;     // rad/s — speed of travelling wave
const K = 1.0;         // wavenumber
const A = 1.0;         // amplitude per wave (sum reaches 2A)
const X_MAX = 4 * Math.PI;

export const WaveSuperpositionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  // Active animation time (clamped to [0, SWEEP_S] for the math)
  const animFrame = Math.max(0, Math.min(frame - 60, SWEEP_S * fps));
  const t = animFrame / fps;
  const phi = (2 * Math.PI * t) / SWEEP_S; // 0 → 2π

  // Three stacked plots — same x range, ±2 y range so sum fits when constructive.
  const PW = 1600, PH = 240;
  const makePlot = (yLabel: string, yRange: [number, number]): Plot => ({
    width: PW, height: PH,
    pad: { l: 90, r: 40, t: 38, b: 56 },
    xRange: [0, X_MAX],
    yRange,
    xTicks: [0, Math.PI, 2 * Math.PI, 3 * Math.PI, 4 * Math.PI],
    yTicks: yRange[1] === 2 ? [-2, -1, 0, 1, 2] : [-1, 0, 1],
    xLabel: 'x',
    yLabel,
  });
  const p1 = makePlot('y₁', [-1.2, 1.2]);
  const p2 = makePlot('y₂', [-1.2, 1.2]);
  const pSum = makePlot('y₁ + y₂', [-2.2, 2.2]);

  const y1Fn = (x: number) => A * Math.sin(K * x - OMEGA * t);
  const y2Fn = (x: number) => A * Math.sin(K * x - OMEGA * t + phi);
  const ySum = (x: number) => y1Fn(x) + y2Fn(x);

  // Phase-state caption
  const phiDeg = ((phi * 180) / Math.PI) % 360;
  let regime = '';
  let regimeColor = PAI_THEME.colors.textMuted;
  const wrap = (phi % (2 * Math.PI));
  if (wrap < Math.PI / 4 || wrap > 2 * Math.PI - Math.PI / 4) {
    regime = 'CONSTRUCTIVE — waves in phase, sum amplitude ≈ 2A';
    regimeColor = PAI_THEME.colors.success;
  } else if (Math.abs(wrap - Math.PI) < Math.PI / 4) {
    regime = 'DESTRUCTIVE — waves out of phase by π, sum ≈ 0';
    regimeColor = PAI_THEME.colors.error;
  } else {
    regime = 'PARTIAL — sum amplitude between 0 and 2A';
    regimeColor = PAI_THEME.colors.warning;
  }

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      flexDirection: 'column', alignItems: 'center', padding: 30,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      <h1 style={{
        fontSize: 52, color: PAI_THEME.colors.text, margin: '8px 0 4px',
        opacity: titleOp, transform: `scale(${titleScale})`, textAlign: 'center',
      }}>
        Wave Superposition
      </h1>
      <p style={{
        fontSize: 26, color: PAI_THEME.colors.accentLight, margin: '0 0 6px',
        opacity: subOp, fontStyle: 'italic',
      }}>
        y₁ = A sin(kx − ωt)    ·    y₂ = A sin(kx − ωt + φ)    ·    y = y₁ + y₂
      </p>

      <svg width={PW} height={PH}>
        <PlotFrame p={p1} title="Wave 1" />
        <polyline points={fullPath(p1, y1Fn, [0, X_MAX], 400)}
          fill="none" stroke={PAI_THEME.colors.accent} strokeWidth={4} strokeLinecap="round" />
      </svg>

      <svg width={PW} height={PH}>
        <PlotFrame p={p2} title={`Wave 2  (φ = ${phiDeg.toFixed(0)}°)`} />
        <polyline points={fullPath(p2, y2Fn, [0, X_MAX], 400)}
          fill="none" stroke={PAI_THEME.colors.warning} strokeWidth={4} strokeLinecap="round" />
      </svg>

      <svg width={PW} height={PH}>
        <PlotFrame p={pSum} title="Sum" />
        {/* Faded individual waves for reference */}
        <polyline points={fullPath(pSum, y1Fn, [0, X_MAX], 400)}
          fill="none" stroke={PAI_THEME.colors.accent} strokeWidth={2} opacity={0.25} />
        <polyline points={fullPath(pSum, y2Fn, [0, X_MAX], 400)}
          fill="none" stroke={PAI_THEME.colors.warning} strokeWidth={2} opacity={0.25} />
        <polyline points={fullPath(pSum, ySum, [0, X_MAX], 400)}
          fill="none" stroke={PAI_THEME.colors.success} strokeWidth={5} strokeLinecap="round" />
      </svg>

      <div style={{
        marginTop: 8, color: regimeColor, fontSize: 28, fontWeight: 700,
        textAlign: 'center', maxWidth: 1500, letterSpacing: '0.5px',
      }}>
        {regime}
      </div>
    </AbsoluteFill>
  );
};
