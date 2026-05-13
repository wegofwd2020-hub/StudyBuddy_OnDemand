/**
 * MaxwellBoltzmannScene — animated Maxwell-Boltzmann speed distribution.
 *
 * The probability density of molecular speeds for an ideal gas of particles
 * with mass m at temperature T is:
 *
 *   f(v; T) = 4·π·n_dens · (m / (2π k_B T))^(3/2) · v² · exp(−m v² / (2 k_B T))
 *
 * As T increases the curve:
 *   • peak (most-probable speed v_p = √(2 k_B T / m)) shifts to higher speed
 *   • peak height drops (∝ 1/v_p, since the integral is normalised to 1)
 *   • the long high-speed tail grows
 *
 * Animation phases @ 30 fps (28 s = 840 frames):
 *
 *   0–60       Title fades in
 *   60–120     Subtitle + axes fade in
 *   120–240    Static curve at T = 200 K — narrow, tall, blue
 *   240–360    T smoothly grows 200 → 600 K — peak slides right, drops
 *   360–480    Static curve at T = 600 K — labelled (orange)
 *   480–600    T smoothly grows 600 → 1200 K — peak again moves right
 *   600–720    Three "ghost" curves overlay (200 K, 600 K, 1200 K) for comparison
 *   720–840    Caption + recap fade
 *
 * The chosen molecule is nitrogen (M = 0.028 kg/mol) so v_p ranges roughly
 * 350 m/s (cold) → 850 m/s (hot). Speed axis fixed at 0–2000 m/s.
 */
import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from 'remotion';
import { PAI_THEME } from '../theme';

// ── Plot geometry (px), drawn into a 1700×620 SVG ─────────────────────────
const SVG_W = 1700;
const SVG_H = 620;
const PAD_L = 140;
const PAD_R = 80;
const PAD_T = 60;
const PAD_B = 100;

const PLOT_X0 = PAD_L;
const PLOT_X1 = SVG_W - PAD_R;
const PLOT_Y0 = PAD_T;
const PLOT_Y1 = SVG_H - PAD_B;

const V_MAX = 2000; // m/s
const V_MIN = 0;

// f(v) is rendered against a fixed amplitude axis. The peak of the cold curve
// reaches near the top; hotter curves are shorter on the same axis.
//
// Reference scale: pick the peak of the COLDEST temperature (T_REF) to map
// to a fraction REF_PEAK_FRAC of the plot height.
const T_REF = 200; // K — coldest curve, used to set the y-axis scale
const REF_PEAK_FRAC = 0.85;

// Universal constants (SI)
const KB = 1.380649e-23;       // Boltzmann constant J/K
const NA = 6.02214076e23;      // Avogadro's number
const M_N2 = 0.028 / NA;        // mass of one N2 molecule, kg

// Most-probable speed v_p = sqrt(2 kB T / m)
function vMostProbable(T: number): number {
  return Math.sqrt((2 * KB * T) / M_N2);
}

// Maxwell-Boltzmann probability density (in 1/(m/s))
function fMB(v: number, T: number): number {
  if (v <= 0) return 0;
  const a = M_N2 / (2 * Math.PI * KB * T);
  const pref = 4 * Math.PI * Math.pow(a, 1.5);
  return pref * v * v * Math.exp(-(M_N2 * v * v) / (2 * KB * T));
}

// Peak value of f(v) at v = v_p, for any T — used for scaling.
function fMBPeak(T: number): number {
  return fMB(vMostProbable(T), T);
}

// Reference peak (cold curve) — sets the y-axis maximum.
const F_REF_PEAK = fMBPeak(T_REF);
const F_AXIS_MAX = F_REF_PEAK / REF_PEAK_FRAC;

// Map (v, f) → (x, y) on the SVG canvas.
function vToX(v: number): number {
  return PLOT_X0 + ((v - V_MIN) / (V_MAX - V_MIN)) * (PLOT_X1 - PLOT_X0);
}
function fToY(f: number): number {
  // 0 maps to PLOT_Y1 (bottom); F_AXIS_MAX maps to PLOT_Y0 (top).
  return PLOT_Y1 - (f / F_AXIS_MAX) * (PLOT_Y1 - PLOT_Y0);
}

// Sample a Maxwell-Boltzmann curve at temperature T and return SVG path
// strings: one for the line and one for the filled area below it.
function buildCurvePaths(T: number, samples = 220): { line: string; area: string } {
  const dv = (V_MAX - V_MIN) / samples;
  const linePts: string[] = [];
  for (let i = 0; i <= samples; i++) {
    const v = V_MIN + i * dv;
    const f = fMB(v, T);
    linePts.push(`${vToX(v).toFixed(1)},${fToY(f).toFixed(1)}`);
  }
  const line = linePts.join(' ');
  const area =
    `M ${vToX(V_MIN).toFixed(1)},${PLOT_Y1.toFixed(1)} ` +
    `L ${linePts.join(' L ')} ` +
    `L ${vToX(V_MAX).toFixed(1)},${PLOT_Y1.toFixed(1)} Z`;
  return { line, area };
}

// Smoothstep helper (cubic ease) for in-out animation.
function smoothstep(edge0: number, edge1: number, x: number): number {
  if (x <= edge0) return 0;
  if (x >= edge1) return 1;
  const t = (x - edge0) / (edge1 - edge0);
  return t * t * (3 - 2 * t);
}

export const MaxwellBoltzmannScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Phase opacities ─────────────────────────────────────────────────────
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [30, 90], [0, 1], { extrapolateRight: 'clamp' });

  // Plot frame (axes, grid) fades in first.
  const axesOp = interpolate(frame, [60, 120], [0, 1], { extrapolateRight: 'clamp' });

  // The animated curve appears at f=120 and stays visible for the rest.
  const curveOp = interpolate(frame, [120, 180], [0, 1], { extrapolateRight: 'clamp' });

  // Caption in the last second.
  const captionOp = interpolate(frame, [720, 780], [0, 1], { extrapolateRight: 'clamp' });

  // ── Temperature evolution T(frame) ──────────────────────────────────────
  // 120–240 hold at 200 K
  // 240–360 ramp 200 → 600 K   (smoothstep)
  // 360–480 hold at 600 K
  // 480–600 ramp 600 → 1200 K  (smoothstep)
  // 600+    hold at 1200 K (then static comparison overlay)
  let T_now: number;
  if (frame < 240) {
    T_now = 200;
  } else if (frame < 360) {
    const t = smoothstep(240, 360, frame);
    T_now = 200 + (600 - 200) * t;
  } else if (frame < 480) {
    T_now = 600;
  } else if (frame < 600) {
    const t = smoothstep(480, 600, frame);
    T_now = 600 + (1200 - 600) * t;
  } else {
    T_now = 1200;
  }

  // Curve color tracks temperature: blue (cold) → orange → red (hot).
  // Linear blend between three colour stops at T = 200, 600, 1200 K.
  function lerp(a: number, b: number, t: number): number {
    return a + (b - a) * t;
  }
  function rgb(r: number, g: number, b: number): string {
    return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
  }
  // Three stops: cold blue (#3b82f6 = 59,130,246), warm orange (#f59e0b = 245,158,11),
  // hot red (#ef4444 = 239,68,68).
  let curveColor: string;
  if (T_now <= 600) {
    const t = (T_now - 200) / (600 - 200);
    curveColor = rgb(lerp(59, 245, t), lerp(130, 158, t), lerp(246, 11, t));
  } else {
    const t = (T_now - 600) / (1200 - 600);
    curveColor = rgb(lerp(245, 239, t), lerp(158, 68, t), lerp(11, 68, t));
  }

  // Build the active animated curve.
  const { line: lineNow, area: areaNow } = buildCurvePaths(T_now);
  const vpNow = vMostProbable(T_now);
  const peakNow = fMBPeak(T_now);
  const peakX = vToX(vpNow);
  const peakY = fToY(peakNow);

  // Comparison overlay (frames ≥ 600): three ghost curves at 200, 600, 1200 K.
  const compareOp = interpolate(frame, [600, 720], [0, 1], { extrapolateRight: 'clamp' });
  const cold = buildCurvePaths(200);
  const warm = buildCurvePaths(600);
  const hot = buildCurvePaths(1200);

  // Y-axis ticks (in absolute f units → fraction-per-(m/s)).
  // We'll show fractional ticks at 0, 25%, 50%, 75% of F_AXIS_MAX.
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];

  // X-axis ticks (m/s).
  const xTicks = [0, 500, 1000, 1500, 2000];

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
        flexDirection: 'column',
        alignItems: 'center',
        padding: 30,
        fontFamily: PAI_THEME.typography.fontFamily,
      }}
    >
      <h1
        style={{
          fontSize: 56,
          color: PAI_THEME.colors.text,
          margin: '12px 0 4px',
          opacity: titleOp,
          transform: `scale(${titleScale})`,
          textAlign: 'center',
        }}
      >
        Maxwell–Boltzmann Speed Distribution
      </h1>
      <p
        style={{
          fontSize: 26,
          color: PAI_THEME.colors.accentLight,
          margin: '0 0 8px',
          opacity: subOp,
          fontStyle: 'italic',
        }}
      >
        Heat the gas — the speed peak shifts right, lowers, and the tail stretches out.
      </p>

      <svg width={SVG_W} height={SVG_H} style={{ marginTop: 16 }}>
        <defs>
          <linearGradient id="mb-areagrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={curveColor} stopOpacity="0.55" />
            <stop offset="100%" stopColor={curveColor} stopOpacity="0.05" />
          </linearGradient>
        </defs>

        {/* Plot background */}
        <rect
          x={PLOT_X0}
          y={PLOT_Y0}
          width={PLOT_X1 - PLOT_X0}
          height={PLOT_Y1 - PLOT_Y0}
          fill="rgba(255,255,255,0.04)"
          stroke={PAI_THEME.colors.textMuted}
          strokeWidth={1.2}
          opacity={axesOp}
        />

        {/* Grid lines (horizontal) */}
        <g opacity={axesOp * 0.4}>
          {yTicks.map((t, i) => {
            if (t === 0) return null;
            const y = PLOT_Y1 - t * (PLOT_Y1 - PLOT_Y0);
            return (
              <line
                key={`gy-${i}`}
                x1={PLOT_X0}
                y1={y}
                x2={PLOT_X1}
                y2={y}
                stroke={PAI_THEME.colors.textMuted}
                strokeWidth={0.8}
                strokeDasharray="4 4"
              />
            );
          })}
          {xTicks.map((v, i) => {
            if (v === 0) return null;
            const x = vToX(v);
            return (
              <line
                key={`gx-${i}`}
                x1={x}
                y1={PLOT_Y0}
                x2={x}
                y2={PLOT_Y1}
                stroke={PAI_THEME.colors.textMuted}
                strokeWidth={0.8}
                strokeDasharray="4 4"
              />
            );
          })}
        </g>

        {/* Axes */}
        <g opacity={axesOp}>
          <line
            x1={PLOT_X0}
            y1={PLOT_Y1}
            x2={PLOT_X1}
            y2={PLOT_Y1}
            stroke={PAI_THEME.colors.text}
            strokeWidth={2}
          />
          <line
            x1={PLOT_X0}
            y1={PLOT_Y0}
            x2={PLOT_X0}
            y2={PLOT_Y1}
            stroke={PAI_THEME.colors.text}
            strokeWidth={2}
          />
        </g>

        {/* X-axis tick labels */}
        <g opacity={axesOp}>
          {xTicks.map((v) => (
            <g key={`xt-${v}`}>
              <line
                x1={vToX(v)}
                y1={PLOT_Y1}
                x2={vToX(v)}
                y2={PLOT_Y1 + 8}
                stroke={PAI_THEME.colors.text}
                strokeWidth={1.5}
              />
              <text
                x={vToX(v)}
                y={PLOT_Y1 + 32}
                textAnchor="middle"
                fontSize={22}
                fill={PAI_THEME.colors.text}
              >
                {v}
              </text>
            </g>
          ))}
          <text
            x={(PLOT_X0 + PLOT_X1) / 2}
            y={PLOT_Y1 + 72}
            textAnchor="middle"
            fontSize={26}
            fontWeight={600}
            fill={PAI_THEME.colors.text}
          >
            molecular speed v (m/s)
          </text>
        </g>

        {/* Y-axis label */}
        <g opacity={axesOp}>
          <text
            x={PAD_L - 70}
            y={(PLOT_Y0 + PLOT_Y1) / 2}
            textAnchor="middle"
            fontSize={26}
            fontWeight={600}
            fill={PAI_THEME.colors.text}
            transform={`rotate(-90 ${PAD_L - 70} ${(PLOT_Y0 + PLOT_Y1) / 2})`}
          >
            f(v) — fraction of molecules per (m/s)
          </text>
        </g>

        {/* Comparison overlay (faded ghost curves at fixed temperatures) */}
        {compareOp > 0 && (
          <g opacity={compareOp * 0.55}>
            <polyline
              points={cold.line}
              fill="none"
              stroke="#3b82f6"
              strokeWidth={3}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="0"
            />
            <polyline
              points={warm.line}
              fill="none"
              stroke="#f59e0b"
              strokeWidth={3}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <polyline
              points={hot.line}
              fill="none"
              stroke="#ef4444"
              strokeWidth={3}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {/* Compact legend in plot area */}
            <g transform={`translate(${PLOT_X1 - 360}, ${PLOT_Y0 + 30})`}>
              <rect
                x={-10}
                y={-26}
                width={350}
                height={140}
                rx={10}
                fill="rgba(15,23,42,0.85)"
                stroke="rgba(148,163,184,0.5)"
                strokeWidth={1.4}
              />
              <line x1={10} y1={0} x2={50} y2={0} stroke="#3b82f6" strokeWidth={4} />
              <text x={60} y={6} fontSize={22} fill="#e2e8f0">
                T = 200 K (cold, narrow)
              </text>
              <line x1={10} y1={36} x2={50} y2={36} stroke="#f59e0b" strokeWidth={4} />
              <text x={60} y={42} fontSize={22} fill="#e2e8f0">
                T = 600 K
              </text>
              <line x1={10} y1={72} x2={50} y2={72} stroke="#ef4444" strokeWidth={4} />
              <text x={60} y={78} fontSize={22} fill="#e2e8f0">
                T = 1200 K (hot, broad)
              </text>
            </g>
          </g>
        )}

        {/* Active animated curve — area + line + peak marker */}
        <g opacity={curveOp}>
          <path d={areaNow} fill="url(#mb-areagrad)" />
          <polyline
            points={lineNow}
            fill="none"
            stroke={curveColor}
            strokeWidth={5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Peak vertical guide line */}
          <line
            x1={peakX}
            y1={peakY}
            x2={peakX}
            y2={PLOT_Y1}
            stroke={curveColor}
            strokeWidth={2}
            strokeDasharray="6 6"
            opacity={0.8}
          />

          {/* Peak dot */}
          <circle cx={peakX} cy={peakY} r={9} fill={curveColor} stroke="#0f172a" strokeWidth={2} />

          {/* Peak label */}
          <text
            x={peakX}
            y={peakY - 22}
            textAnchor="middle"
            fontSize={24}
            fontWeight={700}
            fill={curveColor}
          >
            v_p = {Math.round(vpNow)} m/s
          </text>
        </g>

        {/* Live readout: current temperature */}
        <g opacity={curveOp}>
          <rect
            x={PLOT_X0 + 24}
            y={PLOT_Y0 + 24}
            width={300}
            height={70}
            rx={12}
            fill="rgba(15,23,42,0.85)"
            stroke={curveColor}
            strokeWidth={2}
          />
          <text x={PLOT_X0 + 44} y={PLOT_Y0 + 56} fontSize={28} fill="#e2e8f0">
            T =
          </text>
          <text
            x={PLOT_X0 + 92}
            y={PLOT_Y0 + 56}
            fontSize={32}
            fontWeight={700}
            fill={curveColor}
          >
            {Math.round(T_now)} K
          </text>
          <text x={PLOT_X0 + 44} y={PLOT_Y0 + 82} fontSize={18} fill="#94a3b8">
            N₂ (M = 0.028 kg/mol)
          </text>
        </g>
      </svg>

      {/* Lower equation panel */}
      <div
        style={{
          marginTop: 8,
          opacity: subOp,
          color: PAI_THEME.colors.text,
          fontSize: 26,
          textAlign: 'center',
          maxWidth: 1700,
        }}
      >
        <span style={{ color: PAI_THEME.colors.accentLight, fontWeight: 700 }}>
          f(v) = 4π n (m / 2π k_B T)^{'³/₂'} · v² · exp(−m v² / 2 k_B T)
        </span>
        &nbsp;&nbsp;·&nbsp;&nbsp;
        <span style={{ color: '#f59e0b', fontWeight: 700 }}>
          v_p = √(2 k_B T / m)
        </span>
      </div>

      {/* Caption */}
      <div
        style={{
          marginTop: 12,
          color: PAI_THEME.colors.textMuted,
          fontSize: 24,
          opacity: captionOp,
          textAlign: 'center',
          maxWidth: 1600,
          fontStyle: 'italic',
        }}
      >
        Higher temperature doesn't just mean faster molecules — it means a wider spread of speeds.
        The high-energy tail is what drives evaporation and chemical reaction rates.
      </div>
    </AbsoluteFill>
  );
};
