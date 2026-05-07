import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PAI_THEME } from '../theme';
import { PlotFrame, buildPath, xToPx, yToPx, type Plot } from '../plot';

// h(t) = 20t - 4.9 t^2; t_peak = 20/9.8 ≈ 2.04, h_peak ≈ 20.4, t_impact ≈ 4.08
const VI = 20;
const G = 9.8;
const T_IMPACT = VI * 2 / G;
const T_PEAK = VI / G;
const H_PEAK = (VI * VI) / (2 * G);

const h = (t: number) => VI * t - 0.5 * G * t * t;
const v = (t: number) => VI - G * t;

export const FreeFallScene: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });

  // Phases: 0-90 title; 90-510 ball animation (14s of motion);
  // 510-660 h(t) trace; 660-810 v(t) trace; 810-840 caption
  const t = interpolate(frame, [90, 510], [0, T_IMPACT], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  // Ball position on a vertical track on the left
  const trackX = 320;
  const trackTop = 200;
  const trackBottom = 880;
  const ballY = trackBottom - ((h(t) / H_PEAK) * (trackBottom - trackTop));

  // Plots — h(t) and v(t)
  const PW = 660, PH = 360;
  const ph: Plot = {
    width: PW, height: PH, pad: { l: 80, r: 30, t: 50, b: 70 },
    xRange: [0, 4.5], yRange: [0, 22], xTicks: [0, 1, 2, 3, 4],
    yTicks: [0, 5, 10, 15, 20], xLabel: 't (s)', yLabel: 'h (m)',
  };
  const pv: Plot = {
    ...ph, yRange: [-22, 22], yTicks: [-20, -10, 0, 10, 20], yLabel: 'v (m/s)',
  };

  const hReveal = interpolate(frame, [510, 660], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const vReveal = interpolate(frame, [660, 810], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      padding: 40, fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      <h1 style={{
        fontSize: 50, color: PAI_THEME.colors.text, margin: '0 0 6px',
        opacity: titleOp, textAlign: 'center',
      }}>
        Free Fall — Object Thrown Upward at 20 m/s
      </h1>
      <p style={{
        fontSize: 22, color: PAI_THEME.colors.accentLight, margin: '0 0 30px',
        opacity: titleOp, fontStyle: 'italic', textAlign: 'center',
      }}>
        h(t) = vᵢ t − ½ g t²    ·    v(t) = vᵢ − g t    ·    g = 9.8 m/s²
      </p>

      {/* Ball track on the left */}
      <div style={{ position: 'absolute', left: 200, top: 150, width: 240, height: 800 }}>
        {/* Track */}
        <svg width="240" height="800">
          <line x1="120" y1="50" x2="120" y2="730" stroke={PAI_THEME.colors.textDark} strokeWidth={2} strokeDasharray="6 6" />
          {/* Ground */}
          <line x1="20" y1="730" x2="220" y2="730" stroke={PAI_THEME.colors.textDark} strokeWidth={2} />
          {/* Height markers */}
          {[0, 5, 10, 15, 20].map((m) => {
            const y = 730 - (m / H_PEAK) * 680;
            return (
              <g key={m}>
                <line x1="110" y1={y} x2="130" y2={y} stroke={PAI_THEME.colors.textDark} strokeWidth={1} />
                <text x="100" y={y + 6} fill={PAI_THEME.colors.textMuted} fontSize={18} textAnchor="end">{m} m</text>
              </g>
            );
          })}
          {/* Ball */}
          <circle cx="120" cy={ballY - 150} r="22" fill={PAI_THEME.colors.error} stroke="white" strokeWidth={4} />
          {/* Live readouts */}
          <text x="160" y={ballY - 150 + 6} fill={PAI_THEME.colors.text} fontSize={22}
            fontFamily={PAI_THEME.typography.fontFamilyMono} fontWeight={600}>
            t = {t.toFixed(2)} s
          </text>
          <text x="160" y={ballY - 150 + 30} fill={PAI_THEME.colors.text} fontSize={22}
            fontFamily={PAI_THEME.typography.fontFamilyMono} fontWeight={600}>
            h = {Math.max(0, h(t)).toFixed(2)} m
          </text>
          <text x="160" y={ballY - 150 + 54} fill={PAI_THEME.colors.text} fontSize={22}
            fontFamily={PAI_THEME.typography.fontFamilyMono} fontWeight={600}>
            v = {v(t).toFixed(2)} m/s
          </text>
        </svg>
      </div>

      {/* Plots on the right */}
      <div style={{ position: 'absolute', right: 60, top: 200, display: 'flex', flexDirection: 'column', gap: 30 }}>
        <svg width={PW} height={PH}>
          <PlotFrame p={ph} title="Height vs Time" />
          <polyline points={buildPath(ph, h, [0, T_IMPACT], hReveal)}
            fill="none" stroke={PAI_THEME.colors.accent} strokeWidth={4} strokeLinecap="round" />
          {/* Live ball position on the curve */}
          {hReveal > 0 && (
            <circle
              cx={xToPx(ph, Math.min(t, T_IMPACT))}
              cy={yToPx(ph, Math.max(0, h(Math.min(t, T_IMPACT))))}
              r={9} fill={PAI_THEME.colors.error} stroke="white" strokeWidth={2}
            />
          )}
        </svg>
        <svg width={PW} height={PH}>
          <PlotFrame p={pv} title="Velocity vs Time" />
          <polyline points={buildPath(pv, v, [0, T_IMPACT], vReveal)}
            fill="none" stroke={PAI_THEME.colors.warning} strokeWidth={4} strokeLinecap="round" />
          {vReveal > 0.4 && (
            <g>
              <line x1={xToPx(pv, T_PEAK)} y1={yToPx(pv, -22)}
                x2={xToPx(pv, T_PEAK)} y2={yToPx(pv, 22)}
                stroke={PAI_THEME.colors.success} strokeWidth={2} strokeDasharray="4 4" />
              <text x={xToPx(pv, T_PEAK) + 10} y={yToPx(pv, 18)}
                fill={PAI_THEME.colors.success} fontSize={20} fontWeight={600}>v = 0 at peak</text>
            </g>
          )}
        </svg>
      </div>
    </AbsoluteFill>
  );
};
