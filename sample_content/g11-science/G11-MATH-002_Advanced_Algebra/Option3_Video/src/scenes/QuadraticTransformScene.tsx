import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

/**
 * Animated quadratic transformation:
 *   y = x²   →   y = (x − 3)²   →   y = 2(x − 3)²   →   y = −2(x − 3)²   →   y = −2(x − 3)² + 5
 *
 * 5 steps × 150 frames = 750 frames; 30-frame outro caption brings the comp to 780 frames (26 s @ 30 fps).
 */

const STEP_FRAMES = 150;

const stepFns: ((x: number) => number)[] = [
  (x) => x * x,                      // step 0: base
  (x) => (x - 3) ** 2,               // step 1: shift right by 3
  (x) => 2 * (x - 3) ** 2,           // step 2: vertical stretch ×2
  (x) => -2 * (x - 3) ** 2,          // step 3: reflect across x-axis
  (x) => -2 * (x - 3) ** 2 + 5,      // step 4: shift up by 5  →  vertex (3, 5)
];

const labels = [
  { eq: 'y = x²',                  desc: 'base parabola — vertex at the origin' },
  { eq: 'y = (x − 3)²',            desc: 'shift RIGHT by 3   →   vertex (3, 0)' },
  { eq: 'y = 2(x − 3)²',           desc: 'vertical stretch ×2  →  narrower, opens up' },
  { eq: 'y = −2(x − 3)²',          desc: 'reflect across the x-axis  →  opens DOWN' },
  { eq: 'y = −2(x − 3)² + 5',      desc: 'shift UP by 5   →   vertex (3, 5)' },
];

export const QuadraticTransformScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title pop-in
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });

  const totalSteps = stepFns.length;
  const stepIdx = Math.min(totalSteps - 1, Math.floor(frame / STEP_FRAMES));
  const localFrame = frame - stepIdx * STEP_FRAMES;

  // Tween over the first 55% of the step, then dwell on the result
  const t = stepIdx === 0
    ? 1
    : interpolate(localFrame, [0, STEP_FRAMES * 0.55], [0, 1], {
        extrapolateRight: 'clamp', extrapolateLeft: 'clamp',
      });
  const tt = 1 - Math.pow(1 - t, 3); // ease-out cubic

  const fnPrev = stepFns[Math.max(0, stepIdx - 1)];
  const fnNow  = stepFns[stepIdx];
  const fnInterp = (x: number) => {
    const a = fnPrev(x);
    const b = fnNow(x);
    return a + (b - a) * tt;
  };

  // Plot bounds chosen so y = x² (up to y ≈ 8 at x = ±√8 ≈ ±2.83) and final vertex (3, 5) both fit
  const W = 1200;
  const H = 720;
  const xMin = -4, xMax = 8;
  const yMin = -12, yMax = 8;
  const xToPx = (x: number) => ((x - xMin) / (xMax - xMin)) * W;
  const yToPx = (y: number) => H - ((y - yMin) / (yMax - yMin)) * H;

  const buildPath = (fn: (x: number) => number) => {
    const pts: string[] = [];
    const N = 240;
    for (let i = 0; i <= N; i++) {
      const x = xMin + (i / N) * (xMax - xMin);
      const y = fn(x);
      if (!Number.isFinite(y) || y < yMin - 30 || y > yMax + 30) continue;
      pts.push(`${xToPx(x).toFixed(2)},${yToPx(y).toFixed(2)}`);
    }
    return pts.join(' ');
  };

  // Vertex marker: animate to current step's vertex once tween settles
  const vertexX = stepIdx === 0 ? 0 : 3;
  const vertexY =
    stepIdx === 0 ? 0 :
    stepIdx === 1 ? 0 :
    stepIdx === 2 ? 0 :
    stepIdx === 3 ? 0 :
                    5;
  const vertexOpacity = interpolate(localFrame, [STEP_FRAMES * 0.6, STEP_FRAMES * 0.75], [0, 1], {
    extrapolateRight: 'clamp', extrapolateLeft: 'clamp',
  });
  const vertexLabel = stepIdx === 4 ? 'vertex (3, 5)' :
                       stepIdx === 0 ? 'vertex (0, 0)' :
                       `vertex (${vertexX}, ${vertexY})`;

  // Outro caption appears after step 4 finishes
  const captionOp = interpolate(frame, [750, 780], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{
      backgroundColor: PAI_THEME.colors.background,
      padding: 40,
      flexDirection: 'column',
      justifyContent: 'flex-start',
      alignItems: 'center',
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      <h1 style={{
        fontSize: 56,
        color: PAI_THEME.colors.text,
        margin: '12px 0 4px',
        opacity: titleOpacity,
        transform: `scale(${titleScale})`,
        textAlign: 'center',
      }}>
        Quadratic Transformations
      </h1>
      <p style={{
        fontSize: 26,
        color: PAI_THEME.colors.accentLight,
        margin: '0 0 18px',
        fontStyle: 'italic',
      }}>
        From  y = x²  to  y = −2(x − 3)² + 5
      </p>

      {/* Step pills */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
        {labels.map((l, i) => {
          const active = i === stepIdx;
          const past = i < stepIdx;
          return (
            <div key={i} style={{
              padding: '8px 14px',
              borderRadius: 8,
              background: active ? PAI_THEME.colors.accent : 'transparent',
              color: active ? 'white' : (past ? PAI_THEME.colors.accentLight : PAI_THEME.colors.textMuted),
              fontSize: 18,
              fontWeight: active ? 600 : 400,
              border: `1px solid ${active ? PAI_THEME.colors.accent : PAI_THEME.colors.textDark}`,
            }}>
              Step {i}: {l.eq}
            </div>
          );
        })}
      </div>
      <div style={{
        color: PAI_THEME.colors.textMuted,
        fontSize: 24,
        marginBottom: 14,
        height: 32,
      }}>
        {labels[stepIdx].desc}
      </div>

      <div style={{ background: PAI_THEME.colors.backgroundAlt, borderRadius: 16, padding: 16 }}>
        <svg width={W} height={H}>
          {/* unit grid */}
          {Array.from({ length: 13 }, (_, i) => xMin + i).map((g) => (
            <line key={`vg-${g}`}
              x1={xToPx(g)} y1={0} x2={xToPx(g)} y2={H}
              stroke="#1e293b" strokeWidth={1} />
          ))}
          {Array.from({ length: 11 }, (_, i) => yMin + i * 2).map((g) => (
            <line key={`hg-${g}`}
              x1={0} y1={yToPx(g)} x2={W} y2={yToPx(g)}
              stroke="#1e293b" strokeWidth={1} />
          ))}

          {/* main axes */}
          <line x1={0} y1={yToPx(0)} x2={W} y2={yToPx(0)} stroke={PAI_THEME.colors.textDark} strokeWidth={2} />
          <line x1={xToPx(0)} y1={0} x2={xToPx(0)} y2={H} stroke={PAI_THEME.colors.textDark} strokeWidth={2} />

          {/* axis ticks */}
          {[-4, -2, 2, 4, 6, 8].map((x) => (
            <text key={`xt-${x}`} x={xToPx(x)} y={yToPx(0) + 24} fontSize={20}
              fill={PAI_THEME.colors.textMuted} textAnchor="middle">{x}</text>
          ))}
          {[-10, -8, -6, -4, -2, 2, 4, 6, 8].map((y) => (
            <text key={`yt-${y}`} x={xToPx(0) - 12} y={yToPx(y) + 6} fontSize={20}
              fill={PAI_THEME.colors.textMuted} textAnchor="end">{y}</text>
          ))}

          {/* faint dotted reference: base parabola y = x² */}
          <polyline points={buildPath(stepFns[0])}
            fill="none" stroke={PAI_THEME.colors.textMuted}
            strokeWidth={2} strokeDasharray="6 6" opacity={0.4} />

          {/* current curve (interpolated between previous and current step) */}
          <polyline points={buildPath(fnInterp)}
            fill="none" stroke={PAI_THEME.colors.accent}
            strokeWidth={5} strokeLinecap="round" />

          {/* vertex marker */}
          <g opacity={vertexOpacity}>
            <circle cx={xToPx(vertexX)} cy={yToPx(vertexY)} r={12}
              fill={PAI_THEME.colors.warning} stroke="white" strokeWidth={3} />
            <text x={xToPx(vertexX) + 22} y={yToPx(vertexY) - 14}
              fill={PAI_THEME.colors.warning} fontSize={28} fontWeight={700}>
              {vertexLabel}
            </text>
          </g>

          {/* axis-of-symmetry hint on final step */}
          {stepIdx === 4 && (
            <line x1={xToPx(3)} y1={0} x2={xToPx(3)} y2={H}
              stroke={PAI_THEME.colors.accentLight}
              strokeWidth={1.5}
              strokeDasharray="5 6"
              opacity={vertexOpacity * 0.7} />
          )}
        </svg>
      </div>

      {/* Outro takeaway */}
      <div style={{
        marginTop: 20,
        color: PAI_THEME.colors.text,
        fontSize: 28,
        opacity: captionOp,
        textAlign: 'center',
        maxWidth: 1400,
      }}>
        Vertex form  <em>y = a(x − h)² + k</em>  encodes every transformation:
        &nbsp;<span style={{ color: PAI_THEME.colors.accentLight }}>(h, k)</span> is the vertex,
        &nbsp;<span style={{ color: PAI_THEME.colors.accentLight }}>|a|</span> stretches,
        &nbsp;sign of <span style={{ color: PAI_THEME.colors.accentLight }}>a</span> reflects.
      </div>
    </AbsoluteFill>
  );
};
