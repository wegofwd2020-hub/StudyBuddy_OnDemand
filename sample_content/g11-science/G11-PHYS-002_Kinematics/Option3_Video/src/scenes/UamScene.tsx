import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';
import { PlotFrame, buildPath, type Plot } from '../plot';

export const UamScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Phases (frames at 30fps): 0-90 title, 90-270 x(t), 270-450 v(t),
  // 450-630 a(t), 630-720 final composite + caption.
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [30, 60], [0, 1], { extrapolateRight: 'clamp' });

  // Plot: x(t) = 2t + t^2, v(t) = 2 + 2t, a = 2; t in [0,4]
  const W = 480, H = 360;
  const px: Plot = {
    width: W, height: H, pad: { l: 80, r: 30, t: 60, b: 80 },
    xRange: [0, 4], yRange: [0, 24], xTicks: [0, 1, 2, 3, 4],
    yTicks: [0, 8, 16, 24], xLabel: 't (s)', yLabel: 'x (m)',
  };
  const pv: Plot = { ...px, yRange: [0, 12], yTicks: [0, 4, 8, 12], yLabel: 'v (m/s)' };
  const pa: Plot = { ...px, yRange: [0, 4], yTicks: [0, 1, 2, 3], yLabel: 'a (m/s²)' };

  const xtReveal = interpolate(frame, [90, 270], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const vtReveal = interpolate(frame, [270, 450], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const atReveal = interpolate(frame, [450, 630], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const captionOp = interpolate(frame, [630, 720], [0, 1], { extrapolateRight: 'clamp' });

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
        Uniformly Accelerated Motion
      </h1>
      <p style={{
        fontSize: 26, color: PAI_THEME.colors.accentLight, margin: '0 0 16px',
        opacity: subOp, fontStyle: 'italic',
      }}>
        x = vᵢt + ½at²    ·    v = vᵢ + at    ·    a = constant
      </p>

      <div style={{ display: 'flex', gap: 24, marginTop: 30 }}>
        <svg width={W} height={H}>
          <PlotFrame p={px} title="Position" />
          <polyline points={buildPath(px, (t) => 2 * t + t * t, [0, 4], xtReveal)}
            fill="none" stroke={PAI_THEME.colors.accent} strokeWidth={5} strokeLinecap="round" />
        </svg>
        <svg width={W} height={H}>
          <PlotFrame p={pv} title="Velocity" />
          <polyline points={buildPath(pv, (t) => 2 + 2 * t, [0, 4], vtReveal)}
            fill="none" stroke={PAI_THEME.colors.warning} strokeWidth={5} strokeLinecap="round" />
        </svg>
        <svg width={W} height={H}>
          <PlotFrame p={pa} title="Acceleration" />
          {atReveal > 0 && (
            <line x1={pa.pad.l + 1} y1={(() => {
              const innerH = pa.height - pa.pad.t - pa.pad.b;
              return pa.pad.t + innerH - (2 / 4) * innerH;
            })()}
              x2={pa.pad.l + atReveal * (pa.width - pa.pad.l - pa.pad.r)}
              y2={(() => {
                const innerH = pa.height - pa.pad.t - pa.pad.b;
                return pa.pad.t + innerH - (2 / 4) * innerH;
              })()}
              stroke={PAI_THEME.colors.success} strokeWidth={5} strokeLinecap="round" />
          )}
        </svg>
      </div>

      <div style={{
        marginTop: 36, color: PAI_THEME.colors.text, fontSize: 30,
        opacity: captionOp, textAlign: 'center', maxWidth: 1400,
      }}>
        Slope of x → velocity.    Slope of v → acceleration.
      </div>
    </AbsoluteFill>
  );
};
