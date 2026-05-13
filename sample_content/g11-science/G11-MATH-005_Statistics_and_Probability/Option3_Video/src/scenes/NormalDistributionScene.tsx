import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

/**
 * Animated normal distribution.
 *
 * 5 phases × 150 frames = 750 frames + 30-frame outro caption = 780 frames (26 s @ 30 fps).
 *
 *   Phase 0  introduce the standard normal  N(0, 1)
 *   Phase 1  slide  μ : 0 → 2                       (location)
 *   Phase 2  μ : 2 → 0  and  σ : 1 → 2              (combined)
 *   Phase 3  σ : 2 → 1  then shade  ±1σ  → 68 %     (empirical rule, step 1)
 *   Phase 4  extend shading to  ±2σ → 95 %, then  ±3σ → 99.7 %
 *
 * Layout (1920 × 1080):
 *   Top:    title + phase pills
 *   Middle: density curve plotted over x ∈ [-8, 8]; vertical lines for μ and μ ± kσ;
 *           coloured bands for the 1σ / 2σ / 3σ regions when active.
 *   Right:  parameter readout (μ, σ, peak height) + the formula
 *   Bottom: takeaway caption (fades in over the last second).
 */

const PHASE_FRAMES = 150;

// ---------- Math helpers -----------------------------------------------------

const TWO_PI = 2 * Math.PI;
const SQRT_2PI = Math.sqrt(TWO_PI);

// Standard-normal density φ
const phi = (z: number): number => Math.exp(-(z * z) / 2) / SQRT_2PI;

// General normal density f(x; μ, σ)
const normalPdf = (x: number, mu: number, sigma: number): number =>
  phi((x - mu) / sigma) / sigma;

// Smooth easing (used at start/end of each tween)
const easeInOutCubic = (t: number) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

// ---------- Phase definitions ------------------------------------------------

type Phase = {
  name: string;
  description: string;
  // Target parameters at the END of the phase.  Tween from previous-phase target
  // to this phase's target across the first 60% of the phase.
  mu: number;
  sigma: number;
  // Which empirical-rule bands should be visible AT THE END of this phase.
  band1: boolean;   // ±1σ  → 68 %
  band2: boolean;   // ±2σ  → 95 %
  band3: boolean;   // ±3σ  → 99.7 %
};

const PHASES: Phase[] = [
  {
    name: 'Standard normal',
    description: 'The bell curve  N(μ, σ²)  with μ = 0 and σ = 1 — the standard normal.',
    mu: 0,
    sigma: 1,
    band1: false,
    band2: false,
    band3: false,
  },
  {
    name: 'Shift μ',
    description: 'Increase the mean μ from 0 to 2 — the bell slides RIGHT, but its shape is unchanged.',
    mu: 2,
    sigma: 1,
    band1: false,
    band2: false,
    band3: false,
  },
  {
    name: 'Stretch σ',
    description: 'Bring μ back to 0 and double σ to 2 — the bell flattens and widens; total area still equals 1.',
    mu: 0,
    sigma: 2,
    band1: false,
    band2: false,
    band3: false,
  },
  {
    name: '68 % within ±1σ',
    description: 'Restore σ = 1.  About 68 % of the area lies within ONE standard deviation of the mean.',
    mu: 0,
    sigma: 1,
    band1: true,
    band2: false,
    band3: false,
  },
  {
    name: '95 % and 99.7 %',
    description: '±2σ captures 95 % of the area; ±3σ captures 99.7 % — the empirical (68 – 95 – 99.7) rule.',
    mu: 0,
    sigma: 1,
    band1: true,
    band2: true,
    band3: true,
  },
];

// ---------- Plotting helpers -------------------------------------------------

// World x-domain visible on screen
const X_MIN = -8;
const X_MAX = 8;

// Plot frame in pixels (inside the SVG)
const PLOT = {
  x: 120,
  y: 80,
  width: 1500,
  height: 540,
};

// Density y-axis: maximum displayed density.  φ(0) ≈ 0.4, but with σ=1 we already
// hit 0.4; with σ=2 the peak is only 0.2, so 0.5 leaves headroom.
const Y_MAX = 0.5;

const xToPx = (x: number): number =>
  PLOT.x + ((x - X_MIN) / (X_MAX - X_MIN)) * PLOT.width;

const yToPx = (y: number): number =>
  PLOT.y + PLOT.height - (y / Y_MAX) * PLOT.height;

// Sample the density on a fine grid and return an SVG path string for the line.
const buildCurvePath = (mu: number, sigma: number): string => {
  const N = 240;
  const segs: string[] = [];
  for (let i = 0; i <= N; i++) {
    const x = X_MIN + (i / N) * (X_MAX - X_MIN);
    const y = normalPdf(x, mu, sigma);
    const px = xToPx(x).toFixed(2);
    const py = yToPx(y).toFixed(2);
    segs.push(`${i === 0 ? 'M' : 'L'} ${px} ${py}`);
  }
  return segs.join(' ');
};

// Build a closed polygon path for the shaded region between x = a and x = b.
const buildBandPath = (a: number, b: number, mu: number, sigma: number): string => {
  const N = 80;
  const segs: string[] = [];
  // Top boundary: along the curve from a → b
  for (let i = 0; i <= N; i++) {
    const x = a + (i / N) * (b - a);
    const y = normalPdf(x, mu, sigma);
    const px = xToPx(x).toFixed(2);
    const py = yToPx(y).toFixed(2);
    segs.push(`${i === 0 ? 'M' : 'L'} ${px} ${py}`);
  }
  // Bottom: back along the x-axis (y = 0)
  segs.push(`L ${xToPx(b).toFixed(2)} ${yToPx(0).toFixed(2)}`);
  segs.push(`L ${xToPx(a).toFixed(2)} ${yToPx(0).toFixed(2)}`);
  segs.push('Z');
  return segs.join(' ');
};

// ---------- Component --------------------------------------------------------

export const NormalDistributionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const totalPhases = PHASES.length;
  const phaseIdx = Math.min(totalPhases - 1, Math.floor(frame / PHASE_FRAMES));
  const localFrame = frame - phaseIdx * PHASE_FRAMES;

  // Tween over the first 65% of each phase
  const t = interpolate(localFrame, [0, PHASE_FRAMES * 0.65], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const tween = easeInOutCubic(t);

  const prev = PHASES[Math.max(0, phaseIdx - 1)];
  const curr = PHASES[phaseIdx];

  // Interpolated parameters
  const mu = lerp(prev.mu, curr.mu, tween);
  const sigma = lerp(prev.sigma, curr.sigma, tween);

  // Band visibility — fade IN bands that turn ON in this phase, keep ON bands that were already ON
  const bandOpacity = (prevOn: boolean, currOn: boolean): number => {
    if (currOn && prevOn) return 1;
    if (currOn && !prevOn) return tween;
    if (!currOn && prevOn) return 1 - tween;
    return 0;
  };
  const op1 = bandOpacity(prev.band1, curr.band1);
  // Band 2 should appear in the FIRST half of the last phase, band 3 in the SECOND half.
  // Override the simple lerp on the final phase to stagger their reveal.
  let op2 = bandOpacity(prev.band2, curr.band2);
  let op3 = bandOpacity(prev.band3, curr.band3);
  if (phaseIdx === 4) {
    // Stagger:  band2 fades 0 → 1 over t ∈ [0, 0.5];  band3 over t ∈ [0.5, 1.0]
    op2 = interpolate(t, [0, 0.5], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
    op3 = interpolate(t, [0.5, 1.0], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }

  // Curve path
  const curvePath = buildCurvePath(mu, sigma);

  // Band paths
  const band1Path = buildBandPath(mu - sigma, mu + sigma, mu, sigma);
  const band2InnerPath = buildBandPath(mu - 2 * sigma, mu - sigma, mu, sigma);
  const band2OuterPath = buildBandPath(mu + sigma, mu + 2 * sigma, mu, sigma);
  const band3InnerPath = buildBandPath(mu - 3 * sigma, mu - 2 * sigma, mu, sigma);
  const band3OuterPath = buildBandPath(mu + 2 * sigma, mu + 3 * sigma, mu, sigma);

  // Sigma-line positions
  const sigmaLines = [
    { x: mu - 3 * sigma, label: 'μ − 3σ', visible: op3 > 0.05 },
    { x: mu - 2 * sigma, label: 'μ − 2σ', visible: op2 > 0.05 || op3 > 0.05 },
    { x: mu - sigma,     label: 'μ − σ',  visible: op1 > 0.05 },
    { x: mu,             label: 'μ',      visible: true },
    { x: mu + sigma,     label: 'μ + σ',  visible: op1 > 0.05 },
    { x: mu + 2 * sigma, label: 'μ + 2σ', visible: op2 > 0.05 || op3 > 0.05 },
    { x: mu + 3 * sigma, label: 'μ + 3σ', visible: op3 > 0.05 },
  ];

  // Title pop-in
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });

  // Outro caption (last 30 frames)
  const captionOp = interpolate(frame, [750, 780], [0, 1], { extrapolateRight: 'clamp' });

  // Area-under-curve readout — only matters in the final phase
  const totalShaded =
    0.6827 * op1 + 0.2718 * op2 + 0.0428 * op3; // 1σ + (2σ−1σ outer) + (3σ−2σ outer)

  // y-axis grid (density 0.0, 0.1, 0.2, 0.3, 0.4)
  const yTicks = [0, 0.1, 0.2, 0.3, 0.4];
  // x-axis grid (every 1 unit from -8 to 8)
  const xTicks: number[] = [];
  for (let x = X_MIN; x <= X_MAX; x++) xTicks.push(x);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: PAI_THEME.colors.background,
        padding: 40,
        flexDirection: 'column',
        justifyContent: 'flex-start',
        alignItems: 'center',
        fontFamily: PAI_THEME.typography.fontFamily,
      }}
    >
      <h1
        style={{
          fontSize: 56,
          color: PAI_THEME.colors.text,
          margin: '12px 0 4px',
          opacity: titleOpacity,
          transform: `scale(${titleScale})`,
          textAlign: 'center',
        }}
      >
        The Normal Distribution
      </h1>
      <p
        style={{
          fontSize: 26,
          color: PAI_THEME.colors.accentLight,
          margin: '0 0 18px',
          fontStyle: 'italic',
        }}
      >
        Vary μ and σ — then meet the 68 – 95 – 99.7 rule
      </p>

      {/* Phase pills */}
      <div
        style={{
          display: 'flex',
          gap: 14,
          marginBottom: 6,
          flexWrap: 'wrap',
          justifyContent: 'center',
        }}
      >
        {PHASES.map((p, i) => {
          const active = i === phaseIdx;
          const past = i < phaseIdx;
          return (
            <div
              key={i}
              style={{
                padding: '8px 14px',
                borderRadius: 8,
                background: active ? PAI_THEME.colors.accent : 'transparent',
                color: active
                  ? 'white'
                  : past
                  ? PAI_THEME.colors.accentLight
                  : PAI_THEME.colors.textMuted,
                fontSize: 18,
                fontWeight: active ? 600 : 400,
                border: `1px solid ${active ? PAI_THEME.colors.accent : PAI_THEME.colors.textDark}`,
              }}
            >
              {i}: {p.name}
            </div>
          );
        })}
      </div>

      {/* Description row */}
      <div
        style={{
          display: 'flex',
          gap: 32,
          marginBottom: 8,
          height: 56,
          alignItems: 'center',
          justifyContent: 'center',
          maxWidth: 1700,
          textAlign: 'center',
        }}
      >
        <div
          style={{
            color: PAI_THEME.colors.textMuted,
            fontSize: 22,
            flex: '1 1 auto',
            maxWidth: 1300,
          }}
        >
          {curr.description}
        </div>
      </div>

      {/* Plot SVG */}
      <div
        style={{
          background: PAI_THEME.colors.backgroundAlt,
          borderRadius: 16,
          padding: 12,
          marginTop: 4,
        }}
      >
        <svg width={1760} height={680}>
          {/* Plot frame */}
          <rect
            x={PLOT.x}
            y={PLOT.y}
            width={PLOT.width}
            height={PLOT.height}
            fill={PAI_THEME.colors.background}
            stroke={PAI_THEME.colors.textDark}
            strokeWidth={2}
            rx={12}
          />

          {/* Horizontal grid (density ticks) */}
          {yTicks.map((y) => (
            <line
              key={`yt-${y}`}
              x1={PLOT.x}
              y1={yToPx(y)}
              x2={PLOT.x + PLOT.width}
              y2={yToPx(y)}
              stroke={PAI_THEME.colors.textDark}
              strokeWidth={0.6}
              opacity={0.4}
            />
          ))}
          {yTicks.map((y) => (
            <text
              key={`ytl-${y}`}
              x={PLOT.x - 14}
              y={yToPx(y) + 6}
              fill={PAI_THEME.colors.textMuted}
              fontSize={20}
              textAnchor="end"
            >
              {y.toFixed(1)}
            </text>
          ))}
          <text
            x={PLOT.x - 14}
            y={PLOT.y - 14}
            fill={PAI_THEME.colors.textMuted}
            fontSize={20}
            textAnchor="end"
          >
            f(x)
          </text>

          {/* Vertical grid (every unit on x) */}
          {xTicks.map((x) => (
            <line
              key={`xt-${x}`}
              x1={xToPx(x)}
              y1={PLOT.y}
              x2={xToPx(x)}
              y2={PLOT.y + PLOT.height}
              stroke={PAI_THEME.colors.textDark}
              strokeWidth={0.6}
              opacity={x === 0 ? 0 : 0.25}
            />
          ))}

          {/* x-axis tick labels */}
          {xTicks.map((x) => (
            <text
              key={`xl-${x}`}
              x={xToPx(x)}
              y={PLOT.y + PLOT.height + 26}
              fill={PAI_THEME.colors.textMuted}
              fontSize={20}
              textAnchor="middle"
            >
              {x}
            </text>
          ))}
          <text
            x={PLOT.x + PLOT.width + 8}
            y={PLOT.y + PLOT.height + 26}
            fill={PAI_THEME.colors.textMuted}
            fontSize={20}
          >
            x
          </text>

          {/* x-axis line */}
          <line
            x1={PLOT.x}
            y1={yToPx(0)}
            x2={PLOT.x + PLOT.width}
            y2={yToPx(0)}
            stroke={PAI_THEME.colors.textMuted}
            strokeWidth={1.6}
          />

          {/* ===== Empirical-rule bands (drawn back-to-front: 3σ outermost first) ===== */}

          {/* 3σ wings */}
          {op3 > 0.01 && (
            <g opacity={op3}>
              <path d={band3InnerPath} fill={PAI_THEME.colors.accent} fillOpacity={0.18} />
              <path d={band3OuterPath} fill={PAI_THEME.colors.accent} fillOpacity={0.18} />
            </g>
          )}

          {/* 2σ wings */}
          {op2 > 0.01 && (
            <g opacity={op2}>
              <path d={band2InnerPath} fill={PAI_THEME.colors.accent} fillOpacity={0.36} />
              <path d={band2OuterPath} fill={PAI_THEME.colors.accent} fillOpacity={0.36} />
            </g>
          )}

          {/* 1σ central band */}
          {op1 > 0.01 && (
            <g opacity={op1}>
              <path d={band1Path} fill={PAI_THEME.colors.accent} fillOpacity={0.6} />
            </g>
          )}

          {/* ===== Sigma vertical lines ===== */}
          {sigmaLines.map((s, idx) => {
            if (!s.visible) return null;
            const isMean = idx === 3;
            const stroke = isMean ? PAI_THEME.colors.warning : PAI_THEME.colors.accentLight;
            const dash = isMean ? '' : '8 6';
            const opacity = isMean ? 1 : Math.max(op1, idx === 1 || idx === 5 ? op2 : 0, idx === 0 || idx === 6 ? op3 : 0);
            // Skip drawing if completely outside the visible domain
            if (s.x < X_MIN || s.x > X_MAX) return null;
            return (
              <g key={`sl-${idx}`} opacity={opacity}>
                <line
                  x1={xToPx(s.x)}
                  y1={PLOT.y + 16}
                  x2={xToPx(s.x)}
                  y2={yToPx(0)}
                  stroke={stroke}
                  strokeWidth={isMean ? 2.6 : 1.6}
                  strokeDasharray={dash}
                />
                <text
                  x={xToPx(s.x)}
                  y={PLOT.y + 12}
                  fill={stroke}
                  fontSize={isMean ? 24 : 18}
                  fontWeight={isMean ? 700 : 600}
                  textAnchor="middle"
                >
                  {s.label}
                </text>
              </g>
            );
          })}

          {/* ===== Density curve ===== */}
          <path
            d={curvePath}
            fill="none"
            stroke={PAI_THEME.colors.accentLight}
            strokeWidth={4}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* ===== Empirical-rule percentage callouts ===== */}
          {op1 > 0.05 && (
            <g opacity={op1}>
              <text
                x={xToPx(mu)}
                y={yToPx(normalPdf(mu, mu, sigma) * 0.45)}
                fill="white"
                fontSize={42}
                fontWeight={800}
                textAnchor="middle"
              >
                68 %
              </text>
            </g>
          )}
          {op2 > 0.05 && (
            <g opacity={op2}>
              <text
                x={xToPx(mu - 1.5 * sigma)}
                y={yToPx(0.04)}
                fill={PAI_THEME.colors.text}
                fontSize={26}
                fontWeight={700}
                textAnchor="middle"
              >
                13.5 %
              </text>
              <text
                x={xToPx(mu + 1.5 * sigma)}
                y={yToPx(0.04)}
                fill={PAI_THEME.colors.text}
                fontSize={26}
                fontWeight={700}
                textAnchor="middle"
              >
                13.5 %
              </text>
            </g>
          )}
          {op3 > 0.05 && (
            <g opacity={op3}>
              <text
                x={xToPx(mu - 2.5 * sigma)}
                y={yToPx(0.018)}
                fill={PAI_THEME.colors.text}
                fontSize={20}
                fontWeight={700}
                textAnchor="middle"
              >
                2.35 %
              </text>
              <text
                x={xToPx(mu + 2.5 * sigma)}
                y={yToPx(0.018)}
                fill={PAI_THEME.colors.text}
                fontSize={20}
                fontWeight={700}
                textAnchor="middle"
              >
                2.35 %
              </text>
            </g>
          )}

          {/* ===== Right-side parameter readout ===== */}
          <g transform={`translate(${PLOT.x + PLOT.width + 32}, ${PLOT.y + 30})`}>
            <rect
              x={0}
              y={0}
              width={92}
              height={420}
              rx={14}
              fill={PAI_THEME.colors.background}
              stroke={PAI_THEME.colors.accent}
              strokeWidth={2}
            />
            <text x={46} y={32} fill={PAI_THEME.colors.text} fontSize={20} fontWeight={700} textAnchor="middle">
              parameters
            </text>
            <text x={14} y={70} fill={PAI_THEME.colors.textMuted} fontSize={18}>
              μ
            </text>
            <text x={78} y={70} fill={PAI_THEME.colors.warning} fontSize={22} fontWeight={700} textAnchor="end">
              {mu.toFixed(2)}
            </text>
            <text x={14} y={104} fill={PAI_THEME.colors.textMuted} fontSize={18}>
              σ
            </text>
            <text x={78} y={104} fill={PAI_THEME.colors.accentLight} fontSize={22} fontWeight={700} textAnchor="end">
              {sigma.toFixed(2)}
            </text>
            <line x1={10} y1={124} x2={82} y2={124} stroke={PAI_THEME.colors.textDark} strokeWidth={1} />
            <text x={14} y={150} fill={PAI_THEME.colors.textMuted} fontSize={14}>
              peak
            </text>
            <text x={78} y={170} fill={PAI_THEME.colors.text} fontSize={18} fontWeight={700} textAnchor="end">
              {(1 / (sigma * SQRT_2PI)).toFixed(3)}
            </text>
            <line x1={10} y1={188} x2={82} y2={188} stroke={PAI_THEME.colors.textDark} strokeWidth={1} />
            <text x={14} y={214} fill={PAI_THEME.colors.textMuted} fontSize={14}>
              shaded
            </text>
            <text x={78} y={234} fill={PAI_THEME.colors.success} fontSize={18} fontWeight={700} textAnchor="end">
              {(totalShaded * 100).toFixed(1)} %
            </text>

            <line x1={10} y1={252} x2={82} y2={252} stroke={PAI_THEME.colors.textDark} strokeWidth={1} />

            {/* Formula card */}
            <text x={46} y={278} fill={PAI_THEME.colors.text} fontSize={14} fontWeight={700} textAnchor="middle">
              density
            </text>
            <text x={46} y={304} fill={PAI_THEME.colors.text} fontSize={14} textAnchor="middle" fontStyle="italic">
              f(x) =
            </text>
            <text x={46} y={328} fill={PAI_THEME.colors.text} fontSize={14} textAnchor="middle" fontStyle="italic">
              1 / (σ √2π)
            </text>
            <text x={46} y={352} fill={PAI_THEME.colors.text} fontSize={14} textAnchor="middle" fontStyle="italic">
              · exp(−
            </text>
            <text x={46} y={376} fill={PAI_THEME.colors.text} fontSize={14} textAnchor="middle" fontStyle="italic">
              (x−μ)² / 2σ²
            </text>
            <text x={46} y={400} fill={PAI_THEME.colors.text} fontSize={14} textAnchor="middle" fontStyle="italic">
              )
            </text>
          </g>
        </svg>
      </div>

      {/* Outro caption */}
      <div
        style={{
          marginTop: 14,
          color: PAI_THEME.colors.text,
          fontSize: 26,
          opacity: captionOp,
          textAlign: 'center',
          maxWidth: 1700,
        }}
      >
        Two parameters, one shape —
        &nbsp;<span style={{ color: PAI_THEME.colors.warning }}>μ</span> moves the bell,
        &nbsp;<span style={{ color: PAI_THEME.colors.accentLight }}>σ</span> sets its width,
        &nbsp;and the area within  ±1σ, ±2σ, ±3σ  is always
        &nbsp;<span style={{ color: PAI_THEME.colors.success, fontWeight: 700 }}>68 %, 95 %, 99.7 %</span>.
      </div>
    </AbsoluteFill>
  );
};
