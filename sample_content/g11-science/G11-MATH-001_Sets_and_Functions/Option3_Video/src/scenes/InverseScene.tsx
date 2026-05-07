import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PAI_THEME } from '../theme';

export const InverseScene: React.FC = () => {
  const frame = useCurrentFrame();
  const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });
  const fReveal = interpolate(frame, [30, 110], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const lineReveal = interpolate(frame, [120, 160], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const gReveal = interpolate(frame, [170, 280], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const captionOpacity = interpolate(frame, [290, 330], [0, 1], { extrapolateRight: 'clamp' });

  // Plot bounds — symmetric so y = x is a true 45° line
  const W = 900, H = 700;
  const xMin = -3, xMax = 5;
  const yMin = -3, yMax = 5;
  const xToPx = (x: number) => ((x - xMin) / (xMax - xMin)) * W;
  const yToPx = (y: number) => H - ((y - yMin) / (yMax - yMin)) * H;

  // Build polylines
  const buildPath = (fn: (x: number) => number, range: [number, number], reveal: number, samples = 200) => {
    const pts: string[] = [];
    for (let i = 0; i <= samples; i++) {
      const x = range[0] + (i / samples) * (range[1] - range[0]);
      const y = fn(x);
      if (!Number.isFinite(y) || y < yMin - 5 || y > yMax + 5) continue;
      pts.push(`${xToPx(x).toFixed(2)},${yToPx(y).toFixed(2)}`);
    }
    return pts.slice(0, Math.floor(pts.length * reveal)).join(' ');
  };

  return (
    <AbsoluteFill style={{
      backgroundColor: PAI_THEME.colors.background, padding: 50,
      flexDirection: 'column', justifyContent: 'flex-start', alignItems: 'center',
    }}>
      <h2 style={{
        ...PAI_THEME.typography.heading, fontSize: 52,
        color: PAI_THEME.colors.text, margin: '20px 0 6px', opacity: titleOpacity,
      }}>The inverse is the reflection across y = x</h2>
      <p style={{ color: PAI_THEME.colors.textMuted, fontSize: 22, margin: '0 0 16px', opacity: titleOpacity }}>
        Pick any point on f, swap (x, y) — you land on f⁻¹.
      </p>

      <div style={{ background: PAI_THEME.colors.backgroundAlt, borderRadius: 16, padding: 24 }}>
        <svg width={W} height={H}>
          {/* grid */}
          {[-3, -2, -1, 0, 1, 2, 3, 4, 5].map((g) => (
            <line key={`vg-${g}`} x1={xToPx(g)} y1={0} x2={xToPx(g)} y2={H} stroke="#1e293b" strokeWidth={1} />
          ))}
          {[-3, -2, -1, 0, 1, 2, 3, 4, 5].map((g) => (
            <line key={`hg-${g}`} x1={0} y1={yToPx(g)} x2={W} y2={yToPx(g)} stroke="#1e293b" strokeWidth={1} />
          ))}
          {/* axes */}
          <line x1={0} y1={yToPx(0)} x2={W} y2={yToPx(0)} stroke={PAI_THEME.colors.textDark} strokeWidth={2} />
          <line x1={xToPx(0)} y1={0} x2={xToPx(0)} y2={H} stroke={PAI_THEME.colors.textDark} strokeWidth={2} />

          {/* y = x dashed line */}
          <line
            x1={xToPx(xMin)} y1={yToPx(xMin)}
            x2={xToPx(xMin) + (xToPx(xMax) - xToPx(xMin)) * lineReveal}
            y2={yToPx(xMin) + (yToPx(xMax) - yToPx(xMin)) * lineReveal}
            stroke={PAI_THEME.colors.textMuted} strokeWidth={2.5} strokeDasharray="10 8"
          />

          {/* f(x) = e^x */}
          <polyline
            points={buildPath((x) => Math.exp(x), [xMin, 1.7], fReveal)}
            fill="none" stroke={PAI_THEME.colors.accent} strokeWidth={4.5} strokeLinecap="round"
          />
          {/* f^-1(x) = ln x */}
          <polyline
            points={buildPath((x) => Math.log(x), [0.05, xMax], gReveal)}
            fill="none" stroke={PAI_THEME.colors.warning} strokeWidth={4.5} strokeLinecap="round"
          />
        </svg>
      </div>

      <div style={{ display: 'flex', gap: 50, marginTop: 16 }}>
        <div style={{ color: PAI_THEME.colors.accent, fontSize: 28, fontWeight: 600, opacity: fReveal }}>
          f(x) = eˣ
        </div>
        <div style={{ color: PAI_THEME.colors.textMuted, fontSize: 24, opacity: lineReveal }}>
          y = x
        </div>
        <div style={{ color: PAI_THEME.colors.warning, fontSize: 28, fontWeight: 600, opacity: gReveal }}>
          f⁻¹(x) = ln x
        </div>
      </div>

      <div style={{
        marginTop: 8, color: PAI_THEME.colors.text, fontSize: 22,
        opacity: captionOpacity,
      }}>
        Only bijective functions have an inverse.
      </div>
    </AbsoluteFill>
  );
};
