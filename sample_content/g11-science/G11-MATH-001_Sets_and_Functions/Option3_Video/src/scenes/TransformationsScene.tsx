import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PAI_THEME } from '../theme';

// 4 steps × 150 frames = 600 frames total
const STEP_FRAMES = 150;

const stepFns: ((x: number) => number)[] = [
  (x) => x * x,                       // step 0: base
  (x) => (x + 3) ** 2,                // step 1: shift left by 3
  (x) => 2 * (x + 3) ** 2,            // step 2: vertical stretch ×2
  (x) => -2 * (x + 3) ** 2 + 5,       // step 3: reflect + shift up — combined as final state
];

const labels = [
  { eq: 'y = x²', desc: 'base parabola' },
  { eq: 'y = (x + 3)²', desc: 'shift LEFT by 3' },
  { eq: 'y = 2(x + 3)²', desc: 'vertical stretch ×2' },
  { eq: 'y = −2(x + 3)² + 5', desc: 'reflect across x-axis, then shift UP by 5  →  vertex (−3, 5)' },
];

export const TransformationsScene: React.FC = () => {
  const frame = useCurrentFrame();
  const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });

  // Find current step + tween fraction toward NEXT step
  const totalSteps = stepFns.length;
  const stepIdx = Math.min(totalSteps - 1, Math.floor(frame / STEP_FRAMES));
  const localFrame = frame - stepIdx * STEP_FRAMES;
  // tween: full transition over the first 60% of the step's duration, then dwell
  const t = stepIdx === 0
    ? 1 // initial appearance
    : interpolate(localFrame, [0, STEP_FRAMES * 0.55], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  // Easing
  const tt = 1 - Math.pow(1 - t, 3); // ease-out cubic

  const fnPrev = stepFns[Math.max(0, stepIdx - 1)];
  const fnNow = stepFns[stepIdx];
  // For step 3 (combined reflect + shift up), interpolate by mixing y values
  const fnInterp = (x: number) => {
    const a = fnPrev(x);
    const b = fnNow(x);
    return a + (b - a) * tt;
  };

  // Plot bounds
  const W = 1200, H = 720;
  const xMin = -8, xMax = 4;
  const yMin = -15, yMax = 15;
  const xToPx = (x: number) => ((x - xMin) / (xMax - xMin)) * W;
  const yToPx = (y: number) => H - ((y - yMin) / (yMax - yMin)) * H;

  const buildPath = (fn: (x: number) => number) => {
    const pts: string[] = [];
    const N = 200;
    for (let i = 0; i <= N; i++) {
      const x = xMin + (i / N) * (xMax - xMin);
      const y = fn(x);
      if (!Number.isFinite(y) || y < yMin - 30 || y > yMax + 30) continue;
      pts.push(`${xToPx(x).toFixed(2)},${yToPx(y).toFixed(2)}`);
    }
    return pts.join(' ');
  };

  // vertex marker pops in only on the final step
  const vertexOpacity = stepIdx === 3
    ? interpolate(localFrame, [STEP_FRAMES * 0.55, STEP_FRAMES * 0.7], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' })
    : 0;

  return (
    <AbsoluteFill style={{
      backgroundColor: PAI_THEME.colors.background, padding: 40,
      flexDirection: 'column', justifyContent: 'flex-start', alignItems: 'center',
    }}>
      <h2 style={{
        ...PAI_THEME.typography.heading, fontSize: 50,
        color: PAI_THEME.colors.text, margin: '12px 0 4px', opacity: titleOpacity,
      }}>Transforming y = x²</h2>

      <div style={{ display: 'flex', gap: 30, marginBottom: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
        {labels.map((l, i) => {
          const active = i === stepIdx;
          return (
            <div key={i} style={{
              padding: '8px 14px', borderRadius: 8,
              background: active ? PAI_THEME.colors.accent : 'transparent',
              color: active ? 'white' : PAI_THEME.colors.textMuted,
              fontSize: 18, fontWeight: active ? 600 : 400,
              border: `1px solid ${active ? PAI_THEME.colors.accent : PAI_THEME.colors.textDark}`,
            }}>
              Step {i}: {l.eq}
            </div>
          );
        })}
      </div>
      <div style={{ color: PAI_THEME.colors.textMuted, fontSize: 22, marginBottom: 12 }}>
        {labels[stepIdx].desc}
      </div>

      <div style={{ background: PAI_THEME.colors.backgroundAlt, borderRadius: 16, padding: 16 }}>
        <svg width={W} height={H}>
          {/* grid */}
          {Array.from({ length: 13 }, (_, i) => xMin + i).map((g) => (
            <line key={`vg-${g}`} x1={xToPx(g)} y1={0} x2={xToPx(g)} y2={H} stroke="#1e293b" strokeWidth={1} />
          ))}
          {Array.from({ length: 7 }, (_, i) => yMin + i * 5).map((g) => (
            <line key={`hg-${g}`} x1={0} y1={yToPx(g)} x2={W} y2={yToPx(g)} stroke="#1e293b" strokeWidth={1} />
          ))}
          {/* axes */}
          <line x1={0} y1={yToPx(0)} x2={W} y2={yToPx(0)} stroke={PAI_THEME.colors.textDark} strokeWidth={2} />
          <line x1={xToPx(0)} y1={0} x2={xToPx(0)} y2={H} stroke={PAI_THEME.colors.textDark} strokeWidth={2} />

          {/* base reference (faint dotted) */}
          <polyline points={buildPath(stepFns[0])} fill="none" stroke={PAI_THEME.colors.textMuted}
            strokeWidth={2} strokeDasharray="6 6" opacity={0.4} />
          {/* current curve */}
          <polyline points={buildPath(fnInterp)} fill="none" stroke={PAI_THEME.colors.accent} strokeWidth={5} strokeLinecap="round" />

          {/* vertex marker on final step */}
          <g opacity={vertexOpacity}>
            <circle cx={xToPx(-3)} cy={yToPx(5)} r={12} fill={PAI_THEME.colors.warning} stroke="white" strokeWidth={3} />
            <text x={xToPx(-3) + 22} y={yToPx(5) - 14} fill={PAI_THEME.colors.warning} fontSize={28} fontWeight={700}>
              vertex (−3, 5)
            </text>
          </g>
        </svg>
      </div>
    </AbsoluteFill>
  );
};
