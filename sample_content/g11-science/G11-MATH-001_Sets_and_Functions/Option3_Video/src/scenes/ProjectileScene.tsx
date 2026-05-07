import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PAI_THEME } from '../theme';

// h(t) = -4.9 t² + 14 t + 2
// Ground impact ≈ 2.706 s, Peak height 12 m at t = 10/7 ≈ 1.43 s
const T_MAX = 2.706;
const T_PEAK = 10 / 7;
const H_AXIS_MAX = 14;
const H_PEAK = 12;

const h = (t: number) => -4.9 * t * t + 14 * t + 2;

export const ProjectileScene: React.FC = () => {
  const frame = useCurrentFrame();
  const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });

  // Animation timeline:
  //   30 → 60   draw axes
  //   60 → 360  ball travels  (300 frames = 10s)
  //   360 → 410 highlight peak
  //   410 → 450 ground impact note
  const axesReveal = interpolate(frame, [25, 55], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const t = interpolate(frame, [60, 360], [0, T_MAX], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const peakOpacity = interpolate(frame, [360, 400], [0, 1], { extrapolateRight: 'clamp' });
  const impactOpacity = interpolate(frame, [410, 440], [0, 1], { extrapolateRight: 'clamp' });

  // Plot bounds — t on x in [0, 3], h on y in [0, 14]
  const W = 1300, H = 600;
  const tMin = 0, tMax = 3;
  const hMin = 0, hMax = H_AXIS_MAX;
  const tToPx = (t0: number) => 80 + ((t0 - tMin) / (tMax - tMin)) * (W - 120);
  const hToPx = (y: number) => H - 60 - ((y - hMin) / (hMax - hMin)) * (H - 100);

  // Build the traced parabola up to current t
  const N = 200;
  const tracePts: string[] = [];
  for (let i = 0; i <= N; i++) {
    const ti = (i / N) * t;
    const yi = h(ti);
    tracePts.push(`${tToPx(ti).toFixed(2)},${hToPx(yi).toFixed(2)}`);
  }

  // Faint full guide curve
  const guidePts: string[] = [];
  for (let i = 0; i <= N; i++) {
    const ti = (i / N) * T_MAX;
    const yi = h(ti);
    guidePts.push(`${tToPx(ti).toFixed(2)},${hToPx(yi).toFixed(2)}`);
  }

  const ballX = tToPx(t);
  const ballY = hToPx(h(t));

  return (
    <AbsoluteFill style={{
      backgroundColor: PAI_THEME.colors.background, padding: 40,
      flexDirection: 'column', justifyContent: 'flex-start', alignItems: 'center',
    }}>
      <h2 style={{
        ...PAI_THEME.typography.heading, fontSize: 50,
        color: PAI_THEME.colors.text, margin: '20px 0 6px', opacity: titleOpacity,
      }}>Projectile motion</h2>
      <div style={{ color: PAI_THEME.colors.accentLight, fontSize: 28, margin: '0 0 8px', opacity: titleOpacity }}>
        h(t) = −4.9 t² + 14 t + 2
      </div>
      <div style={{ color: PAI_THEME.colors.textMuted, fontSize: 22, margin: '0 0 12px', opacity: titleOpacity }}>
        A ball thrown up at 14 m/s from a 2 m height.
      </div>

      <div style={{ background: PAI_THEME.colors.backgroundAlt, borderRadius: 16, padding: 20 }}>
        <svg width={W} height={H}>
          {/* grid */}
          {[0, 0.5, 1, 1.5, 2, 2.5, 3].map((g) => (
            <line key={`vg-${g}`} x1={tToPx(g)} y1={hToPx(0)} x2={tToPx(g)} y2={hToPx(hMax)} stroke="#1e293b" strokeWidth={1} opacity={axesReveal} />
          ))}
          {[0, 4, 8, 12].map((g) => (
            <line key={`hg-${g}`} x1={tToPx(0)} y1={hToPx(g)} x2={tToPx(tMax)} y2={hToPx(g)} stroke="#1e293b" strokeWidth={1} opacity={axesReveal} />
          ))}

          {/* axes */}
          <line x1={tToPx(0)} y1={hToPx(0)} x2={tToPx(tMax)} y2={hToPx(0)} stroke={PAI_THEME.colors.textDark} strokeWidth={2} opacity={axesReveal} />
          <line x1={tToPx(0)} y1={hToPx(0)} x2={tToPx(0)} y2={hToPx(hMax)} stroke={PAI_THEME.colors.textDark} strokeWidth={2} opacity={axesReveal} />

          {/* axis labels */}
          {[0, 4, 8, 12].map((g) => (
            <text key={`yl-${g}`} x={tToPx(0) - 20} y={hToPx(g) + 6} textAnchor="end" fontSize={20} fill={PAI_THEME.colors.textMuted} opacity={axesReveal}>{g}</text>
          ))}
          {[0, 1, 2, 3].map((g) => (
            <text key={`xl-${g}`} x={tToPx(g)} y={hToPx(0) + 30} textAnchor="middle" fontSize={20} fill={PAI_THEME.colors.textMuted} opacity={axesReveal}>{g.toFixed(1)} s</text>
          ))}
          <text x={20} y={40} fontSize={22} fill={PAI_THEME.colors.text} opacity={axesReveal}>h (m)</text>
          <text x={W - 70} y={H - 12} fontSize={22} fill={PAI_THEME.colors.text} opacity={axesReveal}>t (s)</text>

          {/* faint full guide */}
          <polyline points={guidePts.join(' ')} fill="none"
            stroke={PAI_THEME.colors.textMuted} strokeWidth={2} strokeDasharray="6 6"
            opacity={interpolate(frame, [40, 60], [0, 0.45], { extrapolateRight: 'clamp' })} />

          {/* live trace */}
          <polyline points={tracePts.join(' ')} fill="none"
            stroke={PAI_THEME.colors.accent} strokeWidth={5} strokeLinecap="round" />

          {/* peak marker */}
          <g opacity={peakOpacity}>
            <line x1={tToPx(T_PEAK)} y1={hToPx(0)} x2={tToPx(T_PEAK)} y2={hToPx(H_PEAK)} stroke={PAI_THEME.colors.warning} strokeWidth={2} strokeDasharray="6 4" />
            <circle cx={tToPx(T_PEAK)} cy={hToPx(H_PEAK)} r={11} fill={PAI_THEME.colors.warning} stroke="white" strokeWidth={2.5} />
            <text x={tToPx(T_PEAK) + 20} y={hToPx(H_PEAK) - 12} fontSize={26} fontWeight={700} fill={PAI_THEME.colors.warning}>
              peak: 12 m at 1.43 s
            </text>
          </g>

          {/* ground impact marker */}
          <g opacity={impactOpacity}>
            <circle cx={tToPx(T_MAX)} cy={hToPx(0)} r={9} fill={PAI_THEME.colors.error} stroke="white" strokeWidth={2.5} />
            <text x={tToPx(T_MAX) - 20} y={hToPx(0) + 60} fontSize={22} fill={PAI_THEME.colors.error} textAnchor="middle">
              ground impact ≈ 2.71 s
            </text>
          </g>

          {/* ball */}
          <circle cx={ballX} cy={ballY} r={14} fill={PAI_THEME.colors.error} stroke="white" strokeWidth={3} />
        </svg>
      </div>

      <div style={{ marginTop: 12, fontSize: 24, color: PAI_THEME.colors.text, fontFamily: PAI_THEME.typography.fontFamilyMono }}>
        t = {t.toFixed(2)} s    h = {Math.max(0, h(t)).toFixed(2)} m
      </div>
    </AbsoluteFill>
  );
};
