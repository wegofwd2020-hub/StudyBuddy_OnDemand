import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PAI_THEME } from '../theme';

type Step = { kind: 'input' | 'fn' | 'output'; label: string; sub?: string };

const Pipeline: React.FC<{ steps: Step[]; localFrame: number; offset: number; accent: string }> = ({ steps, localFrame, offset, accent }) => {
  const W = 1200, H = 200;
  const positions = steps.map((_, i) => 100 + i * ((W - 200) / (steps.length - 1)));

  return (
    <svg width={W} height={H}>
      <defs>
        <marker id={`comp-arrow-${offset}`} viewBox="0 0 10 10" refX={9} refY={5} markerWidth={8} markerHeight={8} orient="auto">
          <path d="M 0 0 L 10 5 L 0 10 z" fill={accent} />
        </marker>
      </defs>
      {/* arrows between boxes — staggered reveal */}
      {positions.slice(0, -1).map((px, i) => {
        const start = offset + i * 22;
        const t = interpolate(localFrame, [start, start + 25], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
        const x1 = px + 70;
        const xMax = positions[i + 1] - 70;
        const x2 = x1 + (xMax - x1) * t;
        return (
          <line key={i} x1={x1} y1={H / 2} x2={x2} y2={H / 2}
            stroke={accent} strokeWidth={4}
            markerEnd={t > 0.95 ? `url(#comp-arrow-${offset})` : undefined} />
        );
      })}
      {/* boxes */}
      {steps.map((s, i) => {
        const px = positions[i];
        const start = offset + i * 22;
        const op = interpolate(localFrame, [start, start + 18], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
        const scale = interpolate(localFrame, [start, start + 18], [0.8, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
        if (s.kind === 'fn') {
          return (
            <g key={i} opacity={op} transform={`translate(${px}, ${H / 2}) scale(${scale}) translate(${-px}, ${-H / 2})`}>
              <rect x={px - 80} y={H / 2 - 40} width={160} height={80} rx={10}
                fill={PAI_THEME.colors.backgroundAlt} stroke={accent} strokeWidth={2} />
              <text x={px} y={H / 2 - 4} textAnchor="middle" fontSize={26} fill={PAI_THEME.colors.text} fontWeight={600}>
                {s.label}
              </text>
              {s.sub && (
                <text x={px} y={H / 2 + 26} textAnchor="middle" fontSize={20} fill={PAI_THEME.colors.textMuted}>
                  {s.sub}
                </text>
              )}
            </g>
          );
        }
        return (
          <g key={i} opacity={op} transform={`translate(${px}, ${H / 2}) scale(${scale}) translate(${-px}, ${-H / 2})`}>
            <circle cx={px} cy={H / 2} r={50} fill={PAI_THEME.colors.background} stroke={accent} strokeWidth={2.5} />
            <text x={px} y={H / 2 + 8} textAnchor="middle" fontSize={28} fill={PAI_THEME.colors.text} fontWeight={700}>
              {s.label}
            </text>
            {s.sub && (
              <text x={px} y={H / 2 + 80} textAnchor="middle" fontSize={18} fill={PAI_THEME.colors.textMuted}>
                {s.sub}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
};

export const CompositionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });
  const conclusionOpacity = interpolate(frame, [320, 360], [0, 1], { extrapolateRight: 'clamp' });

  const top: Step[] = [
    { kind: 'input', label: '2', sub: 'input' },
    { kind: 'fn', label: 'f(x) = 2x + 3' },
    { kind: 'input', label: '7', sub: 'f(2)' },
    { kind: 'fn', label: 'g(y) = y² − 1' },
    { kind: 'input', label: '48', sub: 'g(f(2))' },
  ];

  const bottom: Step[] = [
    { kind: 'input', label: '2', sub: 'input' },
    { kind: 'fn', label: 'g(x) = x² − 1' },
    { kind: 'input', label: '3', sub: 'g(2)' },
    { kind: 'fn', label: 'f(y) = 2y + 3' },
    { kind: 'input', label: '9', sub: 'f(g(2))' },
  ];

  return (
    <AbsoluteFill style={{
      backgroundColor: PAI_THEME.colors.background, padding: 60,
      flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
    }}>
      <h2 style={{
        ...PAI_THEME.typography.heading, fontSize: 56,
        color: PAI_THEME.colors.text, margin: '0 0 4px', opacity: titleOpacity,
      }}>Composition is not commutative</h2>
      <p style={{ color: PAI_THEME.colors.textMuted, fontSize: 24, margin: '0 0 30px', opacity: titleOpacity }}>
        Read right-to-left: the rightmost function acts first.
      </p>

      <div style={{ marginBottom: 6 }}>
        <div style={{ color: PAI_THEME.colors.accentLight, fontSize: 32, marginBottom: 4, fontWeight: 600 }}>
          (g ∘ f)(2)
        </div>
        <Pipeline steps={top} localFrame={frame} offset={20} accent={PAI_THEME.colors.accent} />
      </div>

      <div style={{ marginTop: 30 }}>
        <div style={{ color: PAI_THEME.colors.warning, fontSize: 32, marginBottom: 4, fontWeight: 600 }}>
          (f ∘ g)(2)
        </div>
        <Pipeline steps={bottom} localFrame={frame} offset={160} accent={PAI_THEME.colors.warning} />
      </div>

      <div style={{
        marginTop: 24, fontSize: 36, fontWeight: 600,
        color: PAI_THEME.colors.text,
        opacity: conclusionOpacity,
      }}>
        48 ≠ 9 — order matters
      </div>
    </AbsoluteFill>
  );
};
