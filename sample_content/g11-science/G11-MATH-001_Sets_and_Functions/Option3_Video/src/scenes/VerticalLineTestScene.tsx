import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PAI_THEME } from '../theme';

// Plot bounds and helpers
type Plot = {
  x: [number, number];
  y: [number, number];
  width: number;
  height: number;
};

const xToPx = (p: Plot, x: number) => ((x - p.x[0]) / (p.x[1] - p.x[0])) * p.width;
const yToPx = (p: Plot, y: number) => p.height - ((y - p.y[0]) / (p.y[1] - p.y[0])) * p.height;

const Axes: React.FC<{ plot: Plot; x0?: number; y0?: number }> = ({ plot, x0 = 0, y0 = 0 }) => {
  const stroke = PAI_THEME.colors.textDark;
  return (
    <g>
      <line x1={0} y1={yToPx(plot, y0)} x2={plot.width} y2={yToPx(plot, y0)} stroke={stroke} strokeWidth={1.5} />
      <line x1={xToPx(plot, x0)} y1={0} x2={xToPx(plot, x0)} y2={plot.height} stroke={stroke} strokeWidth={1.5} />
    </g>
  );
};

const FunctionPath: React.FC<{ plot: Plot; fn: (x: number) => number; color: string; xRange: [number, number]; reveal: number }> = ({ plot, fn, color, xRange, reveal }) => {
  const N = 200;
  const points: string[] = [];
  for (let i = 0; i <= N; i++) {
    const x = xRange[0] + (i / N) * (xRange[1] - xRange[0]);
    const y = fn(x);
    if (!Number.isFinite(y)) continue;
    points.push(`${xToPx(plot, x).toFixed(2)},${yToPx(plot, y).toFixed(2)}`);
  }
  // Reveal the curve progressively
  const cut = Math.floor(points.length * reveal);
  return <polyline points={points.slice(0, cut).join(' ')} fill="none" stroke={color} strokeWidth={4} strokeLinecap="round" />;
};

export const VerticalLineTestScene: React.FC = () => {
  const frame = useCurrentFrame();
  const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });
  const reveal = interpolate(frame, [25, 100], [0, 1], { extrapolateRight: 'clamp' });
  // Sweep line moves across both plots from left → right and back
  const sweepT = interpolate(frame, [120, 240], [0, 1], { extrapolateRight: 'clamp' });

  const PW = 700, PH = 500;
  const fnPlot: Plot = { x: [-3, 3], y: [-2, 8], width: PW, height: PH };
  const notFnPlot: Plot = { x: [-1, 6], y: [-3, 3], width: PW, height: PH };

  // Sweep x in plot coordinates
  const sweepXFn = -3 + sweepT * 6;
  const sweepXNot = -1 + sweepT * 7;

  return (
    <AbsoluteFill style={{
      backgroundColor: PAI_THEME.colors.background, padding: 60,
      flexDirection: 'column', justifyContent: 'flex-start', alignItems: 'center',
    }}>
      <h2 style={{
        ...PAI_THEME.typography.heading, fontSize: 52,
        color: PAI_THEME.colors.text, margin: '20px 0 8px', opacity: titleOpacity,
      }}>The Vertical Line Test</h2>
      <p style={{ color: PAI_THEME.colors.textMuted, fontSize: 22, margin: '0 0 24px', opacity: titleOpacity }}>
        A graph is a function iff every vertical line crosses it at most once.
      </p>

      <div style={{ display: 'flex', gap: 60 }}>
        {/* Plot 1: function */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div style={{ color: PAI_THEME.colors.success, fontSize: 26, marginBottom: 8, fontWeight: 600 }}>
            ✓ Function
          </div>
          <div style={{ background: PAI_THEME.colors.backgroundAlt, borderRadius: 12, padding: 20 }}>
            <svg width={PW} height={PH}>
              <Axes plot={fnPlot} />
              <FunctionPath plot={fnPlot} fn={(x) => x * x - 1} color={PAI_THEME.colors.accent} xRange={[-3, 3]} reveal={reveal} />
              {/* sweep line */}
              <line
                x1={xToPx(fnPlot, sweepXFn)} y1={0}
                x2={xToPx(fnPlot, sweepXFn)} y2={PH}
                stroke={PAI_THEME.colors.warning}
                strokeWidth={3} strokeDasharray="8 6"
                opacity={interpolate(frame, [110, 130], [0, 1], { extrapolateRight: 'clamp' })}
              />
              {/* intersect dot */}
              <circle
                cx={xToPx(fnPlot, sweepXFn)}
                cy={yToPx(fnPlot, sweepXFn * sweepXFn - 1)}
                r={8} fill={PAI_THEME.colors.warning}
                opacity={interpolate(frame, [110, 130], [0, 1], { extrapolateRight: 'clamp' })}
              />
            </svg>
          </div>
          <div style={{ color: PAI_THEME.colors.text, fontSize: 28, marginTop: 12 }}>y = x² − 1</div>
        </div>

        {/* Plot 2: not a function */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div style={{ color: PAI_THEME.colors.error, fontSize: 26, marginBottom: 8, fontWeight: 600 }}>
            ✗ Not a function
          </div>
          <div style={{ background: PAI_THEME.colors.backgroundAlt, borderRadius: 12, padding: 20 }}>
            <svg width={PW} height={PH}>
              <Axes plot={notFnPlot} />
              {/* upper branch */}
              <FunctionPath plot={notFnPlot} fn={(x) => Math.sqrt(Math.max(0, x))} color={PAI_THEME.colors.accentLight} xRange={[0, 6]} reveal={reveal} />
              {/* lower branch */}
              <FunctionPath plot={notFnPlot} fn={(x) => -Math.sqrt(Math.max(0, x))} color={PAI_THEME.colors.accentLight} xRange={[0, 6]} reveal={reveal} />
              {/* sweep line */}
              <line
                x1={xToPx(notFnPlot, sweepXNot)} y1={0}
                x2={xToPx(notFnPlot, sweepXNot)} y2={PH}
                stroke={PAI_THEME.colors.warning}
                strokeWidth={3} strokeDasharray="8 6"
                opacity={interpolate(frame, [110, 130], [0, 1], { extrapolateRight: 'clamp' })}
              />
              {/* two intersect dots */}
              {sweepXNot > 0 && (
                <>
                  <circle
                    cx={xToPx(notFnPlot, sweepXNot)}
                    cy={yToPx(notFnPlot, Math.sqrt(sweepXNot))}
                    r={8} fill={PAI_THEME.colors.error}
                    opacity={interpolate(frame, [110, 130], [0, 1], { extrapolateRight: 'clamp' })}
                  />
                  <circle
                    cx={xToPx(notFnPlot, sweepXNot)}
                    cy={yToPx(notFnPlot, -Math.sqrt(sweepXNot))}
                    r={8} fill={PAI_THEME.colors.error}
                    opacity={interpolate(frame, [110, 130], [0, 1], { extrapolateRight: 'clamp' })}
                  />
                </>
              )}
            </svg>
          </div>
          <div style={{ color: PAI_THEME.colors.text, fontSize: 28, marginTop: 12 }}>y² = x  (two y's per positive x)</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
