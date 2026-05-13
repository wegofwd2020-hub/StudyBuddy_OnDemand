/**
 * Shared plotting primitives — same shape as the kinematics + laws-of-motion plot helpers.
 * Light wrappers — full plot grid, axes, animated polyline reveal.
 */
import React from 'react';
import { PAI_THEME } from './theme';

export type Plot = {
  width: number;
  height: number;
  pad: { l: number; r: number; t: number; b: number };
  xRange: [number, number];
  yRange: [number, number];
  xTicks: number[];
  yTicks: number[];
  xLabel?: string;
  yLabel?: string;
};

export function xToPx(p: Plot, x: number) {
  const innerW = p.width - p.pad.l - p.pad.r;
  return p.pad.l + ((x - p.xRange[0]) / (p.xRange[1] - p.xRange[0])) * innerW;
}
export function yToPx(p: Plot, y: number) {
  const innerH = p.height - p.pad.t - p.pad.b;
  return p.pad.t + innerH - ((y - p.yRange[0]) / (p.yRange[1] - p.yRange[0])) * innerH;
}

export const PlotFrame: React.FC<{ p: Plot; title?: string }> = ({ p, title }) => {
  const innerW = p.width - p.pad.l - p.pad.r;
  const innerH = p.height - p.pad.t - p.pad.b;
  return (
    <g>
      <rect x={p.pad.l} y={p.pad.t} width={innerW} height={innerH}
        fill={PAI_THEME.colors.backgroundAlt} stroke={PAI_THEME.colors.textDark} strokeWidth={1} />
      {p.xTicks.map((x) => (
        <g key={`x-${x}`}>
          <line x1={xToPx(p, x)} y1={p.pad.t} x2={xToPx(p, x)} y2={p.pad.t + innerH}
            stroke="#1e293b" strokeWidth={1} />
          <text x={xToPx(p, x)} y={p.pad.t + innerH + 28} fill={PAI_THEME.colors.textMuted}
            fontSize={20} textAnchor="middle">{x}</text>
        </g>
      ))}
      {p.yTicks.map((y) => (
        <g key={`y-${y}`}>
          <line x1={p.pad.l} y1={yToPx(p, y)} x2={p.pad.l + innerW} y2={yToPx(p, y)}
            stroke="#1e293b" strokeWidth={1} />
          <text x={p.pad.l - 12} y={yToPx(p, y) + 7} fill={PAI_THEME.colors.textMuted}
            fontSize={20} textAnchor="end">{y}</text>
        </g>
      ))}
      {p.yRange[0] <= 0 && p.yRange[1] >= 0 && (
        <line x1={p.pad.l} y1={yToPx(p, 0)} x2={p.pad.l + innerW} y2={yToPx(p, 0)}
          stroke={PAI_THEME.colors.textDark} strokeWidth={2} />
      )}
      {p.xRange[0] <= 0 && p.xRange[1] >= 0 && (
        <line x1={xToPx(p, 0)} y1={p.pad.t} x2={xToPx(p, 0)} y2={p.pad.t + innerH}
          stroke={PAI_THEME.colors.textDark} strokeWidth={2} />
      )}
      {p.xLabel && (
        <text x={p.pad.l + innerW / 2} y={p.pad.t + innerH + 60} fill={PAI_THEME.colors.text}
          fontSize={22} fontWeight={600} textAnchor="middle">{p.xLabel}</text>
      )}
      {p.yLabel && (
        <text x={p.pad.l - 50} y={p.pad.t + innerH / 2} fill={PAI_THEME.colors.text}
          fontSize={22} fontWeight={600} textAnchor="middle"
          transform={`rotate(-90 ${p.pad.l - 50} ${p.pad.t + innerH / 2})`}>{p.yLabel}</text>
      )}
      {title && (
        <text x={p.pad.l + innerW / 2} y={p.pad.t - 16} fill={PAI_THEME.colors.text}
          fontSize={24} fontWeight={700} textAnchor="middle">{title}</text>
      )}
    </g>
  );
};

export function buildPath(
  p: Plot,
  fn: (x: number) => number,
  range: [number, number],
  reveal: number,
  samples = 200,
): string {
  const pts: string[] = [];
  for (let i = 0; i <= samples; i++) {
    const x = range[0] + (i / samples) * (range[1] - range[0]);
    const y = fn(x);
    if (!Number.isFinite(y)) continue;
    pts.push(`${xToPx(p, x).toFixed(1)},${yToPx(p, y).toFixed(1)}`);
  }
  return pts.slice(0, Math.floor(pts.length * reveal)).join(' ');
}
