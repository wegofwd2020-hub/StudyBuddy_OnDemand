import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PAI_THEME } from '../theme';

const OP_FRAMES = 150; // each operation gets 5 s

type Op = 'union' | 'inter' | 'diff' | 'comp';

const ops: { kind: Op; name: string; expr: string; result: string; explanation: string }[] = [
  { kind: 'union', name: 'Union',         expr: 'A ∪ B', result: '{1, 2, 3, 4, 5, 6}', explanation: 'everything in A or B (or both)' },
  { kind: 'inter', name: 'Intersection',  expr: 'A ∩ B', result: '{3, 4}',              explanation: 'only what is in both' },
  { kind: 'diff',  name: 'Difference',    expr: 'A \\ B', result: '{1, 2}',             explanation: 'in A but not in B' },
  { kind: 'comp',  name: 'Complement',    expr: "A'",    result: '{5, 6, 7, 8}',       explanation: 'everything in 𝕌 outside A' },
];

const Venn: React.FC<{ op: Op; reveal: number }> = ({ op, reveal }) => {
  const W = 700, H = 480;
  const cxA = 280, cxB = 420, cy = 240, r = 160;

  const accent = PAI_THEME.colors.accent;
  const accentLight = PAI_THEME.colors.accentLight;
  const stroke = PAI_THEME.colors.accentLight;
  const textColor = PAI_THEME.colors.text;

  // Universe
  const uniFill = op === 'comp' ? accent : 'transparent';
  const uniOpacity = op === 'comp' ? 0.55 * reveal : 0;
  const aFill = op === 'union' ? accent : op === 'diff' ? accent : op === 'comp' ? PAI_THEME.colors.background : 'transparent';
  const aOpacity = op === 'comp' ? 1 : (op === 'inter' ? 0 : 0.55) * reveal;
  const bFill = op === 'union' ? accent : 'transparent';
  const bOpacity = op === 'union' ? 0.55 * reveal : 0;

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      <defs>
        <clipPath id="clipB"><circle cx={cxB} cy={cy} r={r} /></clipPath>
      </defs>
      {/* Universe rectangle */}
      <rect x={20} y={40} width={W - 40} height={H - 80} rx={12}
        fill={uniFill} fillOpacity={uniOpacity}
        stroke="#888" strokeWidth={1.5} />
      <text x={36} y={70} fill={PAI_THEME.colors.textMuted} fontSize={26}>𝕌</text>

      {/* Set A */}
      <circle cx={cxA} cy={cy} r={r} fill={aFill} fillOpacity={aOpacity}
        stroke={stroke} strokeWidth={2.5} />
      {/* Set B */}
      <circle cx={cxB} cy={cy} r={r} fill={bFill} fillOpacity={bOpacity}
        stroke={stroke} strokeWidth={2.5} />

      {/* Intersection shading (for inter mode) */}
      {op === 'inter' && (
        <circle cx={cxA} cy={cy} r={r} fill={accent} fillOpacity={0.7 * reveal} clipPath="url(#clipB)" />
      )}
      {/* Diff: cut out the intersection from A */}
      {op === 'diff' && (
        <circle cx={cxA} cy={cy} r={r} fill={PAI_THEME.colors.background} clipPath="url(#clipB)" />
      )}

      {/* Labels */}
      <text x={cxA - r + 30} y={cy - r + 30} fill={textColor} fontSize={42} fontWeight={700}>A</text>
      <text x={cxB + r - 50} y={cy - r + 30} fill={textColor} fontSize={42} fontWeight={700}>B</text>

      {/* Element labels */}
      <text x={cxA - 90} y={cy + 8} fill={textColor} fontSize={22} textAnchor="middle">1, 2</text>
      <text x={(cxA + cxB) / 2} y={cy + 8} fill={textColor} fontSize={22} textAnchor="middle">3, 4</text>
      <text x={cxB + 90} y={cy + 8} fill={textColor} fontSize={22} textAnchor="middle">5, 6</text>
      <text x={W - 60} y={H - 60} fill={PAI_THEME.colors.textMuted} fontSize={18} textAnchor="end">7, 8</text>
    </svg>
  );
};

export const VennScene: React.FC = () => {
  const frame = useCurrentFrame();
  const idx = Math.min(ops.length - 1, Math.floor(frame / OP_FRAMES));
  const localFrame = frame - idx * OP_FRAMES;
  const reveal = interpolate(localFrame, [10, 50], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const titleOpacity = interpolate(localFrame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });

  const op = ops[idx];

  const setA = '{1, 2, 3, 4}';
  const setB = '{3, 4, 5, 6}';
  const universe = '{1, 2, 3, 4, 5, 6, 7, 8}';

  return (
    <AbsoluteFill style={{
      backgroundColor: PAI_THEME.colors.background, padding: 80,
      flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: titleOpacity }}>
        <h2 style={{
          ...PAI_THEME.typography.heading, fontSize: 56,
          color: PAI_THEME.colors.text, margin: '0 0 12px',
        }}>{op.name} — {op.expr}</h2>
        <div style={{ color: PAI_THEME.colors.textMuted, fontSize: 24, marginBottom: 24 }}>
          {op.explanation}
        </div>
        <div style={{ display: 'flex', gap: 60, alignItems: 'center', marginBottom: 16, fontSize: 22, color: PAI_THEME.colors.textMuted }}>
          <span>𝕌 = {universe}</span>
          <span>A = {setA}</span>
          <span>B = {setB}</span>
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <Venn op={op.kind} reveal={reveal} />
      </div>

      <div style={{
        marginTop: 12, fontSize: 38, fontWeight: 600,
        color: PAI_THEME.colors.accentLight,
        opacity: interpolate(localFrame, [60, 90], [0, 1], { extrapolateRight: 'clamp' }),
      }}>
        {op.expr} = {op.result}
      </div>

      {/* Progress dots */}
      <div style={{ position: 'absolute', bottom: 50, display: 'flex', gap: 16 }}>
        {ops.map((_, i) => (
          <div key={i} style={{
            width: 14, height: 14, borderRadius: 7,
            background: i === idx ? PAI_THEME.colors.accent : PAI_THEME.colors.textDark,
          }} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
