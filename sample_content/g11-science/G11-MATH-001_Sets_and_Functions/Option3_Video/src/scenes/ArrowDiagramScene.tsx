import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PAI_THEME } from '../theme';

const PER_FRAMES = 150; // each diagram lives 5s

type Pos = { label: string; y: number };

const diagrams: { name: string; tag: string; explainer: string; a: Pos[]; b: Pos[]; arrows: [string, string][] }[] = [
  {
    name: 'Injective only',
    tag: '1-to-1 — distinct inputs give distinct outputs',
    explainer: 'Some elements of B are unreached.',
    a: [{ label: '1', y: 200 }, { label: '2', y: 320 }, { label: '3', y: 440 }],
    b: [{ label: 'p', y: 160 }, { label: 'q', y: 270 }, { label: 'r', y: 380 }, { label: 's', y: 490 }],
    arrows: [['1', 'p'], ['2', 'q'], ['3', 'r']],
  },
  {
    name: 'Surjective only',
    tag: 'Onto — every B-element is hit',
    explainer: 'Two inputs collide on the same output.',
    a: [{ label: '1', y: 160 }, { label: '2', y: 260 }, { label: '3', y: 360 }, { label: '4', y: 460 }],
    b: [{ label: 'p', y: 200 }, { label: 'q', y: 320 }, { label: 'r', y: 440 }],
    arrows: [['1', 'p'], ['2', 'p'], ['3', 'q'], ['4', 'r']],
  },
  {
    name: 'Bijective',
    tag: 'One-to-one correspondence',
    explainer: 'Both injective and surjective — the only kind with an inverse.',
    a: [{ label: '1', y: 200 }, { label: '2', y: 320 }, { label: '3', y: 440 }],
    b: [{ label: 'p', y: 200 }, { label: 'q', y: 320 }, { label: 'r', y: 440 }],
    arrows: [['1', 'p'], ['2', 'q'], ['3', 'r']],
  },
];

const Diagram: React.FC<{ idx: number; localFrame: number }> = ({ idx, localFrame }) => {
  const W = 900, H = 620;
  const A_X = 280, B_X = 620;
  const dotR = 12;
  const d = diagrams[idx];

  const aPos = Object.fromEntries(d.a.map((p) => [p.label, { x: A_X, y: p.y }]));
  const bPos = Object.fromEntries(d.b.map((p) => [p.label, { x: B_X, y: p.y }]));

  return (
    <svg width={W} height={H} style={{ background: PAI_THEME.colors.backgroundAlt, borderRadius: 16 }}>
      <defs>
        <marker id={`arrow-${idx}`} viewBox="0 0 10 10" refX={9} refY={5} markerWidth={8} markerHeight={8} orient="auto">
          <path d="M 0 0 L 10 5 L 0 10 z" fill={PAI_THEME.colors.accent} />
        </marker>
      </defs>

      {/* Set A oval */}
      <ellipse cx={A_X} cy={H / 2} rx={120} ry={210}
        fill={PAI_THEME.colors.background} stroke={PAI_THEME.colors.accentLight} strokeWidth={2} />
      <text x={A_X} y={70} fill={PAI_THEME.colors.accentLight} fontSize={36} fontWeight={700} textAnchor="middle">A</text>

      {/* Set B oval */}
      <ellipse cx={B_X} cy={H / 2} rx={120} ry={210}
        fill={PAI_THEME.colors.background} stroke={PAI_THEME.colors.warning} strokeWidth={2} />
      <text x={B_X} y={70} fill={PAI_THEME.colors.warning} fontSize={36} fontWeight={700} textAnchor="middle">B</text>

      {/* Dots A */}
      {d.a.map((e) => (
        <g key={`a-${e.label}`}>
          <circle cx={A_X} cy={e.y} r={dotR} fill={PAI_THEME.colors.text} />
          <text x={A_X - 30} y={e.y + 8} fontSize={28} fill={PAI_THEME.colors.text} textAnchor="end">{e.label}</text>
        </g>
      ))}
      {/* Dots B */}
      {d.b.map((e) => (
        <g key={`b-${e.label}`}>
          <circle cx={B_X} cy={e.y} r={dotR} fill={PAI_THEME.colors.text} />
          <text x={B_X + 30} y={e.y + 8} fontSize={28} fill={PAI_THEME.colors.text}>{e.label}</text>
        </g>
      ))}
      {/* Arrows — staggered reveal */}
      {d.arrows.map(([from, to], i) => {
        const start = 30 + i * 18;
        const t = interpolate(localFrame, [start, start + 30], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
        const f = aPos[from], v = bPos[to];
        const dx = v.x - f.x, dy = v.y - f.y;
        const len = Math.hypot(dx, dy);
        const ux = dx / len, uy = dy / len;
        const x1 = f.x + ux * (dotR + 2);
        const y1 = f.y + uy * (dotR + 2);
        const x2t = f.x + ux * ((dotR + 2) + (len - 2 * (dotR + 2)) * t);
        const y2t = f.y + uy * ((dotR + 2) + (len - 2 * (dotR + 2)) * t);
        return (
          <line key={i}
            x1={x1} y1={y1} x2={x2t} y2={y2t}
            stroke={PAI_THEME.colors.accent}
            strokeWidth={3.5}
            markerEnd={t > 0.95 ? `url(#arrow-${idx})` : undefined}
          />
        );
      })}
    </svg>
  );
};

export const ArrowDiagramScene: React.FC = () => {
  const frame = useCurrentFrame();
  const idx = Math.min(diagrams.length - 1, Math.floor(frame / PER_FRAMES));
  const localFrame = frame - idx * PER_FRAMES;
  const titleOpacity = interpolate(localFrame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });

  const d = diagrams[idx];

  return (
    <AbsoluteFill style={{
      backgroundColor: PAI_THEME.colors.background, padding: 60,
      flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
    }}>
      <div style={{ opacity: titleOpacity, textAlign: 'center', marginBottom: 16 }}>
        <h2 style={{ ...PAI_THEME.typography.heading, fontSize: 56, color: PAI_THEME.colors.text, margin: '0 0 8px' }}>
          {d.name}
        </h2>
        <div style={{ color: PAI_THEME.colors.accentLight, fontSize: 26 }}>{d.tag}</div>
        <div style={{ color: PAI_THEME.colors.textMuted, fontSize: 22, marginTop: 6 }}>{d.explainer}</div>
      </div>

      <Diagram idx={idx} localFrame={localFrame} />

      {/* Progress dots */}
      <div style={{ position: 'absolute', bottom: 50, display: 'flex', gap: 16 }}>
        {diagrams.map((_, i) => (
          <div key={i} style={{
            width: 14, height: 14, borderRadius: 7,
            background: i === idx ? PAI_THEME.colors.accent : PAI_THEME.colors.textDark,
          }} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
