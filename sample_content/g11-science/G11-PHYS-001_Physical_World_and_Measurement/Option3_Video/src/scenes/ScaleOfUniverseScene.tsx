import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

/**
 * "Scale of the Universe" — animated zoom across log-scale.
 *
 * Nine stops along the log axis from 10^-35 m (Planck length) to 10^26 m
 * (observable universe). Each stop pauses for ~2.6 s, then we glide to
 * the next one. The horizontal axis represents log10(size in m); a moving
 * indicator shows where on the scale we are. A central content panel
 * shows the canonical object at that scale plus a one-line description.
 *
 * Total: 32 s @ 30 fps = 960 frames.
 */

type Stop = {
  log10m: number;            // log10(size_in_m)
  name: string;
  size: string;              // human-readable size
  description: string;
  band: 'quantum' | 'classical' | 'cosmological';
};

const STOPS: Stop[] = [
  { log10m: -35,  name: 'Planck length',           size: '1.6 × 10⁻³⁵ m',
    description: 'the smallest length where current physics still applies',
    band: 'quantum' },
  { log10m: -15,  name: 'Proton',                  size: '1 × 10⁻¹⁵ m',
    description: 'the nucleus of a hydrogen atom — a quark trio bound by the strong force',
    band: 'quantum' },
  { log10m: -10,  name: 'Atom',                    size: '1 × 10⁻¹⁰ m',
    description: 'electron cloud around a tiny nucleus — the building block of chemistry',
    band: 'quantum' },
  { log10m: -7,   name: 'Virus',                   size: '1 × 10⁻⁷ m',
    description: 'about a thousand atoms wide — at the edge of what light microscopes can see',
    band: 'quantum' },
  { log10m: 0,    name: 'Human',                   size: '1 m',
    description: 'our familiar scale — Newtonian mechanics governs everything we touch',
    band: 'classical' },
  { log10m: 6.8,  name: 'Earth',                   size: '6.4 × 10⁶ m',
    description: 'planetary radius — gravity, atmospheres, and weather',
    band: 'classical' },
  { log10m: 8.85, name: 'Sun',                     size: '7 × 10⁸ m',
    description: 'a main-sequence star — fusion at 1.5 × 10⁷ K powers the solar system',
    band: 'classical' },
  { log10m: 21,   name: 'Milky Way',               size: '1 × 10²¹ m',
    description: 'our galaxy — about 100 billion stars rotating around a central black hole',
    band: 'cosmological' },
  { log10m: 26.94, name: 'Observable universe',    size: '8.8 × 10²⁶ m',
    description: 'everything light has had time to reach us from in 13.8 billion years',
    band: 'cosmological' },
];

// Layout
const W = 1920;
const H = 1080;

// Axis: horizontal, drawn from x=140 to x=1780, log10m range [-36, 28] (slightly wider than data).
const AX_LEFT = 140;
const AX_RIGHT = 1780;
const AX_Y = 880;
const LOG_MIN = -36;
const LOG_MAX = 28;
const logToX = (log10m: number) =>
  AX_LEFT + ((log10m - LOG_MIN) / (LOG_MAX - LOG_MIN)) * (AX_RIGHT - AX_LEFT);

const bandColor = (b: Stop['band']) => {
  switch (b) {
    case 'quantum':       return PAI_THEME.colors.info;       // blue
    case 'classical':     return PAI_THEME.colors.warning;    // amber
    case 'cosmological':  return PAI_THEME.colors.accent;     // purple
  }
};
const bandLabel = (b: Stop['band']) => {
  switch (b) {
    case 'quantum':       return 'quantum domain';
    case 'classical':     return 'classical domain';
    case 'cosmological':  return 'cosmological domain';
  }
};

export const ScaleOfUniverseScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 32 s = 960 frames. Phases:
  //   0   .. 60   : title fade in (2 s)
  //   60  .. 870  : 9 stops at ~90 frames each (3 s/stop)
  //   870 .. 960  : final caption + zoom-out (3 s)
  const PHASE_INTRO_END = 60;
  const PHASE_STOPS_END = 870;
  const STOPS_TOTAL_FRAMES = PHASE_STOPS_END - PHASE_INTRO_END; // 810
  const FRAMES_PER_STOP = STOPS_TOTAL_FRAMES / STOPS.length;     // 90

  // Title fade
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });

  // Title slides up & shrinks once stops begin
  const titleSlideOut = interpolate(
    frame,
    [PHASE_INTRO_END - 10, PHASE_INTRO_END + 20],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  // Determine current stop & sub-progress
  let stopIndex = 0;
  let subProgress = 0; // 0..1 where 1 means just reached the next stop
  if (frame >= PHASE_INTRO_END && frame < PHASE_STOPS_END) {
    const f = frame - PHASE_INTRO_END;
    stopIndex = Math.min(STOPS.length - 1, Math.floor(f / FRAMES_PER_STOP));
    subProgress = (f - stopIndex * FRAMES_PER_STOP) / FRAMES_PER_STOP;
  } else if (frame >= PHASE_STOPS_END) {
    stopIndex = STOPS.length - 1;
    subProgress = 1;
  }

  const currentStop = STOPS[stopIndex];
  const nextStop = STOPS[Math.min(stopIndex + 1, STOPS.length - 1)];

  // Smooth interpolation between currentStop and nextStop's log10m
  // Use ease-in-out so each stop "settles" before moving on.
  const easeInOut = (t: number) => 0.5 - 0.5 * Math.cos(Math.PI * t);
  // We hold for the first 60% of each stop's window, then glide for the last 40%.
  const HOLD_FRAC = 0.6;
  const glideT =
    subProgress < HOLD_FRAC
      ? 0
      : easeInOut((subProgress - HOLD_FRAC) / (1 - HOLD_FRAC));
  const indicatorLog =
    currentStop.log10m + glideT * (nextStop.log10m - currentStop.log10m);
  const indicatorX = logToX(indicatorLog);

  // Card opacity — fade in when we're holding, fade out at very end before glide
  const cardOpacity = interpolate(
    subProgress,
    [0, 0.1, HOLD_FRAC, HOLD_FRAC + 0.15, 1],
    [0, 1, 1, 0.4, 0.4],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  // Outro
  const outroOpacity = interpolate(frame, [PHASE_STOPS_END, PHASE_STOPS_END + 30], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(180deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
      color: PAI_THEME.colors.text,
    }}>
      {/* Title (top) */}
      <div style={{
        position: 'absolute',
        top: 40 - 30 * titleSlideOut,
        left: 0, right: 0,
        textAlign: 'center',
        opacity: 1 - 0.4 * titleSlideOut,
        transform: `scale(${1 - 0.25 * titleSlideOut})`,
        transformOrigin: 'top center',
      }}>
        <div style={{
          fontSize: 56 * titleScale,
          fontWeight: 700,
          opacity: titleOpacity,
        }}>
          The Scales of the Physical World
        </div>
        <div style={{
          fontSize: 26,
          fontStyle: 'italic',
          color: PAI_THEME.colors.accentLight,
          opacity: titleOpacity,
          marginTop: 8,
        }}>
          from the Planck length (10⁻³⁵ m) to the observable universe (10²⁶ m) — 61 orders of magnitude
        </div>
      </div>

      {/* Central content card — current stop */}
      <div style={{
        position: 'absolute',
        top: 220, left: 0, right: 0,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        opacity: cardOpacity,
      }}>
        {/* Object visual — a circle scaled visually for impact (not literally to scale) */}
        <ObjectGlyph stop={currentStop} />

        <div style={{
          marginTop: 30,
          fontSize: 64,
          fontWeight: 700,
          color: bandColor(currentStop.band),
        }}>
          {currentStop.name}
        </div>
        <div style={{
          marginTop: 8,
          fontSize: 44,
          fontFamily: PAI_THEME.typography.fontFamilyMono,
          fontWeight: 700,
          color: PAI_THEME.colors.text,
        }}>
          {currentStop.size}
        </div>
        <div style={{
          marginTop: 18,
          fontSize: 24,
          color: PAI_THEME.colors.textMuted,
          textAlign: 'center',
          maxWidth: 1200,
        }}>
          {currentStop.description}
        </div>
        <div style={{
          marginTop: 16,
          fontSize: 18,
          color: bandColor(currentStop.band),
          fontStyle: 'italic',
        }}>
          {bandLabel(currentStop.band)}
        </div>
      </div>

      {/* Log axis at the bottom */}
      <svg
        width={W} height={H}
        style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
      >
        {/* Axis bands */}
        {/* Quantum band: log -36 .. log -9 */}
        <rect
          x={logToX(-36)} y={AX_Y - 40}
          width={logToX(-9) - logToX(-36)} height={20}
          fill={PAI_THEME.colors.info} fillOpacity={0.18}
          stroke={PAI_THEME.colors.info} strokeWidth={1}
        />
        <text
          x={(logToX(-36) + logToX(-9)) / 2} y={AX_Y - 50}
          fill={PAI_THEME.colors.info} fontSize={20} fontWeight={700} textAnchor="middle"
        >
          quantum
        </text>
        {/* Classical band: log -9 .. log 7 */}
        <rect
          x={logToX(-9)} y={AX_Y - 40}
          width={logToX(7) - logToX(-9)} height={20}
          fill={PAI_THEME.colors.warning} fillOpacity={0.18}
          stroke={PAI_THEME.colors.warning} strokeWidth={1}
        />
        <text
          x={(logToX(-9) + logToX(7)) / 2} y={AX_Y - 50}
          fill={PAI_THEME.colors.warning} fontSize={20} fontWeight={700} textAnchor="middle"
        >
          classical
        </text>
        {/* Cosmological band: log 7 .. log 28 */}
        <rect
          x={logToX(7)} y={AX_Y - 40}
          width={logToX(28) - logToX(7)} height={20}
          fill={PAI_THEME.colors.accent} fillOpacity={0.18}
          stroke={PAI_THEME.colors.accent} strokeWidth={1}
        />
        <text
          x={(logToX(7) + logToX(28)) / 2} y={AX_Y - 50}
          fill={PAI_THEME.colors.accent} fontSize={20} fontWeight={700} textAnchor="middle"
        >
          cosmological
        </text>

        {/* Main axis line */}
        <line
          x1={AX_LEFT} y1={AX_Y} x2={AX_RIGHT} y2={AX_Y}
          stroke={PAI_THEME.colors.text} strokeWidth={2}
        />

        {/* Tick marks every 5 powers + label */}
        {Array.from({ length: 14 }, (_, i) => -35 + i * 5).map((p) => {
          const x = logToX(p);
          return (
            <g key={`tick-${p}`}>
              <line x1={x} y1={AX_Y - 8} x2={x} y2={AX_Y + 8}
                stroke={PAI_THEME.colors.textMuted} strokeWidth={1.5} />
              <text x={x} y={AX_Y + 32}
                fill={PAI_THEME.colors.textMuted} fontSize={18}
                fontFamily={PAI_THEME.typography.fontFamilyMono}
                textAnchor="middle">
                10{toSuper(p)}
              </text>
            </g>
          );
        })}

        {/* Stop markers */}
        {STOPS.map((stop, i) => {
          const x = logToX(stop.log10m);
          const isActive = i === stopIndex;
          return (
            <g key={`stop-${i}`}>
              <circle
                cx={x} cy={AX_Y}
                r={isActive ? 12 : 7}
                fill={bandColor(stop.band)}
                stroke={PAI_THEME.colors.text}
                strokeWidth={isActive ? 3 : 1.5}
                opacity={isActive ? 1 : 0.55}
              />
              {/* Label only the active stop here, others are visible in the content panel */}
            </g>
          );
        })}

        {/* Moving indicator triangle above the axis */}
        <g transform={`translate(${indicatorX}, ${AX_Y - 16})`} opacity={1 - titleSlideOut < 0 ? 0 : (frame >= PHASE_INTRO_END ? 1 : 0)}>
          <polygon
            points="-12,-18 12,-18 0,0"
            fill={PAI_THEME.colors.text}
            stroke={PAI_THEME.colors.text}
            strokeWidth={1}
          />
          <text
            x={0} y={-26}
            fill={PAI_THEME.colors.text}
            fontSize={20}
            fontFamily={PAI_THEME.typography.fontFamilyMono}
            textAnchor="middle"
            fontWeight={700}
          >
            10{toSuper(Math.round(indicatorLog))} m
          </text>
        </g>

        {/* Axis label */}
        <text
          x={(AX_LEFT + AX_RIGHT) / 2}
          y={AX_Y + 70}
          fill={PAI_THEME.colors.text}
          fontSize={22}
          fontWeight={600}
          textAnchor="middle"
        >
          size in metres (log scale)
        </text>
      </svg>

      {/* Outro caption (overlay, becomes visible after the last stop holds) */}
      <div style={{
        position: 'absolute',
        bottom: 130,
        left: 0, right: 0,
        textAlign: 'center',
        opacity: outroOpacity,
      }}>
        <div style={{
          fontSize: 30,
          fontWeight: 700,
          color: PAI_THEME.colors.text,
        }}>
          One set of physical laws — applied across 61 orders of magnitude.
        </div>
        <div style={{
          marginTop: 8,
          fontSize: 22,
          color: PAI_THEME.colors.accentLight,
          fontStyle: 'italic',
        }}>
          Quantum mechanics on the left · Newtonian / classical in the middle · general relativity on the right.
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* --------------------------- helpers --------------------------- */

const SUPER_DIGITS: Record<string, string> = {
  '-': '⁻', '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
  '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
};
function toSuper(n: number): string {
  return String(n)
    .split('')
    .map((c) => SUPER_DIGITS[c] ?? c)
    .join('');
}

/**
 * A stylised glyph for the current stop. Visual size is fixed for legibility;
 * the literal scale is conveyed by the axis indicator and the size label,
 * not by the glyph itself.
 */
const ObjectGlyph: React.FC<{ stop: Stop }> = ({ stop }) => {
  const color = bandColor(stop.band);
  const SIZE = 220;

  // Stop-specific glyphs
  switch (stop.name) {
    case 'Planck length':
      return (
        <svg width={SIZE} height={SIZE}>
          <circle cx={SIZE / 2} cy={SIZE / 2} r={6} fill={color}>
            <animate attributeName="r" values="4;9;4" dur="1.6s" repeatCount="indefinite" />
          </circle>
          <circle cx={SIZE / 2} cy={SIZE / 2} r={40} fill="none"
            stroke={color} strokeOpacity={0.4} strokeDasharray="3 6" strokeWidth={1.5} />
          <circle cx={SIZE / 2} cy={SIZE / 2} r={80} fill="none"
            stroke={color} strokeOpacity={0.25} strokeDasharray="2 8" strokeWidth={1.2} />
        </svg>
      );

    case 'Proton':
      return (
        <svg width={SIZE} height={SIZE}>
          {/* three quarks */}
          <circle cx={SIZE / 2} cy={SIZE / 2 - 30} r={28} fill={color} fillOpacity={0.7} />
          <circle cx={SIZE / 2 - 32} cy={SIZE / 2 + 22} r={28} fill={color} fillOpacity={0.7} />
          <circle cx={SIZE / 2 + 32} cy={SIZE / 2 + 22} r={28} fill={color} fillOpacity={0.7} />
          <text x={SIZE / 2} y={SIZE / 2 - 22} fill="white" fontSize={20} fontWeight={700} textAnchor="middle">u</text>
          <text x={SIZE / 2 - 32} y={SIZE / 2 + 30} fill="white" fontSize={20} fontWeight={700} textAnchor="middle">u</text>
          <text x={SIZE / 2 + 32} y={SIZE / 2 + 30} fill="white" fontSize={20} fontWeight={700} textAnchor="middle">d</text>
          {/* binding */}
          <line x1={SIZE / 2} y1={SIZE / 2 - 30} x2={SIZE / 2 - 32} y2={SIZE / 2 + 22}
            stroke={color} strokeWidth={2} strokeDasharray="3 4" />
          <line x1={SIZE / 2} y1={SIZE / 2 - 30} x2={SIZE / 2 + 32} y2={SIZE / 2 + 22}
            stroke={color} strokeWidth={2} strokeDasharray="3 4" />
          <line x1={SIZE / 2 - 32} y1={SIZE / 2 + 22} x2={SIZE / 2 + 32} y2={SIZE / 2 + 22}
            stroke={color} strokeWidth={2} strokeDasharray="3 4" />
        </svg>
      );

    case 'Atom':
      return (
        <svg width={SIZE} height={SIZE}>
          {/* nucleus */}
          <circle cx={SIZE / 2} cy={SIZE / 2} r={12} fill={color} />
          {/* three orbits */}
          <ellipse cx={SIZE / 2} cy={SIZE / 2} rx={90} ry={32}
            fill="none" stroke={color} strokeWidth={2} strokeOpacity={0.7} />
          <ellipse cx={SIZE / 2} cy={SIZE / 2} rx={90} ry={32}
            fill="none" stroke={color} strokeWidth={2} strokeOpacity={0.5}
            transform={`rotate(60 ${SIZE / 2} ${SIZE / 2})`} />
          <ellipse cx={SIZE / 2} cy={SIZE / 2} rx={90} ry={32}
            fill="none" stroke={color} strokeWidth={2} strokeOpacity={0.5}
            transform={`rotate(-60 ${SIZE / 2} ${SIZE / 2})`} />
          {/* electrons */}
          <circle cx={SIZE / 2 + 90} cy={SIZE / 2} r={6} fill={PAI_THEME.colors.text} />
          <circle cx={SIZE / 2 - 45} cy={SIZE / 2 + 78} r={6} fill={PAI_THEME.colors.text} />
          <circle cx={SIZE / 2 + 45} cy={SIZE / 2 - 78} r={6} fill={PAI_THEME.colors.text} />
        </svg>
      );

    case 'Virus':
      return (
        <svg width={SIZE} height={SIZE}>
          {/* icosahedral capsid suggested by hexagon */}
          <polygon
            points="110,30 180,70 180,150 110,190 40,150 40,70"
            fill={color} fillOpacity={0.25} stroke={color} strokeWidth={3}
          />
          {/* spike proteins */}
          {Array.from({ length: 12 }).map((_, i) => {
            const a = (i / 12) * 2 * Math.PI;
            const x1 = SIZE / 2 + 80 * Math.cos(a);
            const y1 = SIZE / 2 + 80 * Math.sin(a);
            const x2 = SIZE / 2 + 105 * Math.cos(a);
            const y2 = SIZE / 2 + 105 * Math.sin(a);
            return (
              <g key={i}>
                <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={2} />
                <circle cx={x2} cy={y2} r={5} fill={color} />
              </g>
            );
          })}
        </svg>
      );

    case 'Human':
      return (
        <svg width={SIZE} height={SIZE}>
          {/* Stick-figure proportions */}
          <circle cx={SIZE / 2} cy={45} r={22} fill="none" stroke={color} strokeWidth={4} />
          <line x1={SIZE / 2} y1={67} x2={SIZE / 2} y2={150} stroke={color} strokeWidth={4} />
          <line x1={SIZE / 2} y1={90} x2={SIZE / 2 - 35} y2={120} stroke={color} strokeWidth={4} strokeLinecap="round" />
          <line x1={SIZE / 2} y1={90} x2={SIZE / 2 + 35} y2={120} stroke={color} strokeWidth={4} strokeLinecap="round" />
          <line x1={SIZE / 2} y1={150} x2={SIZE / 2 - 25} y2={200} stroke={color} strokeWidth={4} strokeLinecap="round" />
          <line x1={SIZE / 2} y1={150} x2={SIZE / 2 + 25} y2={200} stroke={color} strokeWidth={4} strokeLinecap="round" />
          {/* ground */}
          <line x1={20} y1={205} x2={SIZE - 20} y2={205} stroke={PAI_THEME.colors.textDark} strokeWidth={2} />
        </svg>
      );

    case 'Earth':
      return (
        <svg width={SIZE} height={SIZE}>
          <defs>
            <radialGradient id="earth-grad" cx="0.4" cy="0.4">
              <stop offset="0%" stopColor="#60a5fa" />
              <stop offset="65%" stopColor="#1e40af" />
              <stop offset="100%" stopColor="#0f172a" />
            </radialGradient>
          </defs>
          <circle cx={SIZE / 2} cy={SIZE / 2} r={90} fill="url(#earth-grad)"
            stroke={color} strokeWidth={2} />
          {/* Stylised continents */}
          <path d="M 90 80 Q 110 70 130 90 Q 145 95 130 115 Q 110 125 95 110 Z"
            fill="#16a34a" fillOpacity={0.85} />
          <path d="M 145 130 Q 165 125 175 140 Q 175 160 155 165 Q 140 158 145 140 Z"
            fill="#16a34a" fillOpacity={0.85} />
          <path d="M 60 130 Q 78 128 85 145 Q 80 160 65 158 Q 50 150 60 130 Z"
            fill="#16a34a" fillOpacity={0.85} />
        </svg>
      );

    case 'Sun':
      return (
        <svg width={SIZE} height={SIZE}>
          <defs>
            <radialGradient id="sun-grad" cx="0.5" cy="0.5">
              <stop offset="0%" stopColor="#fef08a" />
              <stop offset="60%" stopColor="#f59e0b" />
              <stop offset="100%" stopColor="#b45309" />
            </radialGradient>
          </defs>
          {/* corona rays */}
          {Array.from({ length: 12 }).map((_, i) => {
            const a = (i / 12) * 2 * Math.PI;
            const x1 = SIZE / 2 + 90 * Math.cos(a);
            const y1 = SIZE / 2 + 90 * Math.sin(a);
            const x2 = SIZE / 2 + 105 * Math.cos(a);
            const y2 = SIZE / 2 + 105 * Math.sin(a);
            return (
              <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
                stroke="#fbbf24" strokeWidth={4} strokeLinecap="round" />
            );
          })}
          <circle cx={SIZE / 2} cy={SIZE / 2} r={85} fill="url(#sun-grad)" />
        </svg>
      );

    case 'Milky Way':
      return (
        <svg width={SIZE} height={SIZE}>
          {/* Spiral galaxy from polar curve r = a + b*theta */}
          {[0, Math.PI * 2 / 3, Math.PI * 4 / 3].map((rot, idx) => {
            const pts: string[] = [];
            for (let k = 0; k <= 60; k++) {
              const t = (k / 60) * 4 * Math.PI;
              const r = 6 + 2 * t;
              const x = SIZE / 2 + r * Math.cos(t + rot);
              const y = SIZE / 2 + r * Math.sin(t + rot);
              pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
            }
            return (
              <polyline key={idx} points={pts.join(' ')}
                fill="none" stroke={color} strokeOpacity={0.7} strokeWidth={2} />
            );
          })}
          {/* core */}
          <circle cx={SIZE / 2} cy={SIZE / 2} r={14} fill="#fef3c7" />
          <circle cx={SIZE / 2} cy={SIZE / 2} r={22} fill={color} fillOpacity={0.25} />
          {/* a few stars */}
          {[[60,55],[155,72],[170,150],[68,145],[110,40],[40,108],[180,108]].map(([x,y],i) =>
            <circle key={i} cx={x} cy={y} r={1.5} fill="white" />)}
        </svg>
      );

    case 'Observable universe':
      return (
        <svg width={SIZE} height={SIZE}>
          {/* outer sphere */}
          <circle cx={SIZE / 2} cy={SIZE / 2} r={95} fill="none"
            stroke={color} strokeWidth={3} />
          {/* hubble "cosmic web" filaments inside */}
          <g stroke={color} strokeWidth={1.5} strokeOpacity={0.5} fill="none">
            <path d="M 60 70 Q 110 90 160 60" />
            <path d="M 70 130 Q 110 100 150 140" />
            <path d="M 50 150 Q 90 165 140 175" />
            <path d="M 100 50 Q 120 110 90 170" />
            <path d="M 65 100 Q 130 115 175 95" />
          </g>
          {/* clusters */}
          {[[80,75],[140,90],[105,135],[90,160],[150,150],[120,55]].map(([x,y],i) =>
            <circle key={i} cx={x} cy={y} r={3} fill={color} />)}
          <text x={SIZE / 2} y={SIZE - 8} fill={color}
            fontSize={14} fontStyle="italic" textAnchor="middle">cosmic web</text>
        </svg>
      );

    default:
      return (
        <svg width={SIZE} height={SIZE}>
          <circle cx={SIZE / 2} cy={SIZE / 2} r={60} fill={color} fillOpacity={0.5} />
        </svg>
      );
  }
};
