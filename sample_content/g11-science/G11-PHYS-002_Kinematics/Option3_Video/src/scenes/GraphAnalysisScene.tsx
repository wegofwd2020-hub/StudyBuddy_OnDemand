import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PAI_THEME } from '../theme';
import { PlotFrame, buildPath, xToPx, yToPx, type Plot } from '../plot';

// x(t) = 2t + t^2;  v(t) = 2 + 2t;  a = 2

export const GraphAnalysisScene: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });

  // Phases: 0-90 title; 90-360 x-t with sweeping tangent → builds v-t;
  // 360-630 v-t with sweeping area → builds back; 630-780 final + caption
  const sweepFrame1 = interpolate(frame, [90, 360], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const sweepFrame2 = interpolate(frame, [360, 630], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const captionOp = interpolate(frame, [630, 720], [0, 1], { extrapolateRight: 'clamp' });

  const PW = 700, PH = 500;
  const px: Plot = {
    width: PW, height: PH, pad: { l: 90, r: 40, t: 80, b: 80 },
    xRange: [0, 5], yRange: [0, 35], xTicks: [0, 1, 2, 3, 4, 5],
    yTicks: [0, 10, 20, 30], xLabel: 't (s)', yLabel: 'x (m)',
  };
  const pv: Plot = { ...px, yRange: [0, 14], yTicks: [0, 4, 8, 12], yLabel: 'v (m/s)' };

  // Sweeping tangent on x(t): tangent at t=t0, slope = 2 + 2*t0
  const t0 = sweepFrame1 * 4; // tangent t goes from 0 to 4

  // Build v-t up to t0
  const vBuiltReveal = sweepFrame1;

  // Sweeping area on v(t): from 0 to t1
  const t1 = sweepFrame2 * 4;

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      padding: 40, fontFamily: PAI_THEME.typography.fontFamily,
      flexDirection: 'column', alignItems: 'center',
    }}>
      <h1 style={{
        fontSize: 56, color: PAI_THEME.colors.text, margin: '0 0 4px',
        opacity: titleOp, textAlign: 'center',
      }}>
        Slope ↔ Area
      </h1>
      <p style={{
        fontSize: 26, color: PAI_THEME.colors.accentLight, margin: '0 0 18px',
        opacity: titleOp, fontStyle: 'italic',
      }}>
        Slope of x → v.   Area under v → x.
      </p>

      <div style={{ display: 'flex', gap: 50 }}>
        {/* Left: x(t) with sweeping tangent */}
        <svg width={PW} height={PH}>
          <PlotFrame p={px} title="Position x(t)" />
          <polyline points={buildPath(px, (t) => 2 * t + t * t, [0, 5], 1)}
            fill="none" stroke={PAI_THEME.colors.accent} strokeWidth={5} strokeLinecap="round" />
          {/* Tangent line at t0 */}
          {sweepFrame1 > 0 && sweepFrame1 < 1.2 && (() => {
            const slope = 2 + 2 * t0;
            const xVal = 2 * t0 + t0 * t0;
            // tangent: y - xVal = slope * (t - t0); at t = t0 - 0.7 and t0 + 0.7
            const t1L = Math.max(0, t0 - 0.7);
            const t1R = Math.min(5, t0 + 0.7);
            const yL = xVal + slope * (t1L - t0);
            const yR = xVal + slope * (t1R - t0);
            return (
              <g>
                <line x1={xToPx(px, t1L)} y1={yToPx(px, yL)}
                  x2={xToPx(px, t1R)} y2={yToPx(px, yR)}
                  stroke={PAI_THEME.colors.warning} strokeWidth={4} />
                <circle cx={xToPx(px, t0)} cy={yToPx(px, xVal)}
                  r={9} fill={PAI_THEME.colors.warning} stroke="white" strokeWidth={2} />
                <text x={xToPx(px, t0) + 12} y={yToPx(px, xVal) - 12}
                  fill={PAI_THEME.colors.warning} fontSize={22} fontWeight={600}>
                  slope = {slope.toFixed(1)}
                </text>
              </g>
            );
          })()}
        </svg>

        {/* Right: v(t) builds, then sweeps area */}
        <svg width={PW} height={PH}>
          <PlotFrame p={pv} title="Velocity v(t)" />
          {/* v(t) line revealed by sweepFrame1 */}
          <polyline points={buildPath(pv, (t) => 2 + 2 * t, [0, 5], vBuiltReveal)}
            fill="none" stroke={PAI_THEME.colors.warning} strokeWidth={5} strokeLinecap="round" />
          {/* Live dot at t0 showing the freshly-computed slope */}
          {sweepFrame1 > 0 && sweepFrame1 < 1.2 && (
            <circle cx={xToPx(pv, t0)} cy={yToPx(pv, 2 + 2 * t0)}
              r={9} fill={PAI_THEME.colors.warning} stroke="white" strokeWidth={2} />
          )}
          {/* Once v is built, sweep area */}
          {sweepFrame2 > 0 && (() => {
            const pts = [`${xToPx(pv, 0)},${yToPx(pv, 0)}`];
            const N = 80;
            for (let i = 0; i <= N; i++) {
              const ti = (i / N) * t1;
              pts.push(`${xToPx(pv, ti)},${yToPx(pv, 2 + 2 * ti)}`);
            }
            pts.push(`${xToPx(pv, t1)},${yToPx(pv, 0)}`);
            return (
              <polygon points={pts.join(' ')}
                fill={PAI_THEME.colors.success} fillOpacity={0.35}
                stroke={PAI_THEME.colors.success} strokeWidth={2} />
            );
          })()}
          {sweepFrame2 > 0.05 && (
            <text x={xToPx(pv, t1 / 2)} y={yToPx(pv, (2 + 2 * t1) / 2 + 1)}
              fill={PAI_THEME.colors.success} fontSize={22} fontWeight={700} textAnchor="middle">
              area = Δx
            </text>
          )}
        </svg>
      </div>

      <div style={{
        marginTop: 30, color: PAI_THEME.colors.text, fontSize: 26,
        opacity: captionOp, textAlign: 'center', maxWidth: 1400,
      }}>
        Slope of position → velocity.   Area under velocity → displacement.   The two operations are inverses.
      </div>
    </AbsoluteFill>
  );
};
