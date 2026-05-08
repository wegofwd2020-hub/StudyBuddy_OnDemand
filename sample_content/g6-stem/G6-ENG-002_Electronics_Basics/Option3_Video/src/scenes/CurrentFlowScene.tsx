/**
 * CurrentFlowScene — Ohm's law visualised. A simple battery+switch+resistor+LED
 * loop with green charge dots flowing around it. Three regimes:
 *   A: switch open, no current
 *   B: V=5V, R=330Ω, I=15mA (baseline)
 *   C: V doubles to 10V, I doubles to 30mA — dots flow visibly faster
 *   D: R doubles to 660Ω, I halves to 15mA — dots slow to baseline rate
 *
 * Ohm's law (V = I × R) is rendered on the right with live values.
 *
 * Frames @ 30fps (24 s = 720 frames):
 *   0–60     title fade
 *   60–150   circuit appears, switch open (3 s)
 *   150–300  switch closes — Regime B (5 s)
 *   300–450  V doubles — Regime C (5 s)
 *   450–600  R doubles — Regime D (5 s)
 *   600–720  hold final tableau (4 s)
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Frame anchors ───────────────────────────────────────────────────────────
const F_TITLE_END = 60;
const F_CIRCUIT_IN = 150;
const F_REGIME_B = 150;
const F_REGIME_C = 300;
const F_REGIME_D = 450;
const F_REGIME_E = 600;
const F_END = 720;

// ── Circuit geometry (rectangular loop) ─────────────────────────────────────
const LOOP_LEFT = 540;
const LOOP_RIGHT = 1300;
const LOOP_TOP = 280;
const LOOP_BOTTOM = 700;
const LOOP_W = LOOP_RIGHT - LOOP_LEFT;
const LOOP_H = LOOP_BOTTOM - LOOP_TOP;
const PERIM = 2 * (LOOP_W + LOOP_H);

// Phase ∈ [0, 1) maps to a position on the loop, going clockwise from top-left
function loopXY(phase: number): { x: number; y: number } {
  const p = ((phase % 1) + 1) % 1; // normalize
  const dist = p * PERIM;
  if (dist < LOOP_W) {
    return { x: LOOP_LEFT + dist, y: LOOP_TOP };
  }
  if (dist < LOOP_W + LOOP_H) {
    return { x: LOOP_RIGHT, y: LOOP_TOP + (dist - LOOP_W) };
  }
  if (dist < LOOP_W + LOOP_H + LOOP_W) {
    return { x: LOOP_RIGHT - (dist - LOOP_W - LOOP_H), y: LOOP_BOTTOM };
  }
  return { x: LOOP_LEFT, y: LOOP_BOTTOM - (dist - 2 * LOOP_W - LOOP_H) };
}

// ── Cumulative-phase integral ───────────────────────────────────────────────
// Speed (loops per second) by regime: B=0.25 (4s/loop), C=0.50, D=0.25
// Phase per frame = speed / fps
function cumulativePhase(frame: number, fps: number): number {
  let phase = 0;
  let f = frame;

  // No motion before regime B
  if (f <= F_REGIME_B) return 0;

  // Regime B: F_REGIME_B → min(f, F_REGIME_C)
  const bEnd = Math.min(f, F_REGIME_C);
  phase += ((bEnd - F_REGIME_B) / fps) * 0.25;
  if (f <= F_REGIME_C) return phase;

  // Regime C: F_REGIME_C → min(f, F_REGIME_D)
  const cEnd = Math.min(f, F_REGIME_D);
  phase += ((cEnd - F_REGIME_C) / fps) * 0.50;
  if (f <= F_REGIME_D) return phase;

  // Regime D: F_REGIME_D → min(f, F_REGIME_E)
  const dEnd = Math.min(f, F_REGIME_E);
  phase += ((dEnd - F_REGIME_D) / fps) * 0.25;
  if (f <= F_REGIME_E) return phase;

  // Regime E: hold (= regime D speed, optional)
  const eEnd = Math.min(f, F_END);
  phase += ((eEnd - F_REGIME_E) / fps) * 0.25;
  return phase;
}

// ── Regime info (V, I, R, caption) ──────────────────────────────────────────
function getRegime(frame: number) {
  if (frame < F_REGIME_B) {
    return { regime: 'A', V: 0, I_mA: 0, R: 330, caption: 'Switch open — no current.', color: PAI_THEME.colors.textMuted };
  }
  if (frame < F_REGIME_C) {
    return { regime: 'B', V: 5, I_mA: 15.15, R: 330, caption: 'Switch closes — current flows. V = I × R.', color: PAI_THEME.colors.success };
  }
  if (frame < F_REGIME_D) {
    return { regime: 'C', V: 10, I_mA: 30.30, R: 330, caption: 'Double the voltage → double the current.', color: PAI_THEME.colors.warning };
  }
  if (frame < F_REGIME_E) {
    return { regime: 'D', V: 10, I_mA: 15.15, R: 660, caption: 'Double the resistance → current halves back.', color: PAI_THEME.colors.error };
  }
  return { regime: 'E', V: 10, I_mA: 15.15, R: 660, caption: 'Ohm’s law in action: I = V / R.', color: PAI_THEME.colors.info };
}

// ── Charge-dot configuration ────────────────────────────────────────────────
const N_DOTS = 12;
const DOT_R = 9;

export const CurrentFlowScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });
  const circuitOp = interpolate(frame, [60, F_CIRCUIT_IN], [0, 1], { extrapolateRight: 'clamp' });

  const regime = getRegime(frame);
  const cumPhase = cumulativePhase(frame, fps);

  // Switch state — closed once we're at regime B
  const switchClosed = frame >= F_REGIME_B;
  // LED brightness scales with current
  const ledBrightness = regime.I_mA === 0 ? 0 : Math.min(regime.I_mA / 30, 1);

  // ── Component positions ─────────────────────────────────────────────────
  // Top wire: switch on the left half, resistor on the right half
  const SW_X = LOOP_LEFT + 180, SW_Y = LOOP_TOP;
  const RES_X = LOOP_LEFT + 540, RES_Y = LOOP_TOP;
  // Right wire: LED in the middle
  const LED_X = LOOP_RIGHT, LED_Y = (LOOP_TOP + LOOP_BOTTOM) / 2;
  // Bottom wire: battery in the middle
  const BAT_X = (LOOP_LEFT + LOOP_RIGHT) / 2, BAT_Y = LOOP_BOTTOM;

  // Pre-render charge dots
  const dots = Array.from({ length: N_DOTS }, (_, k) => {
    const phase = (k / N_DOTS + cumPhase) % 1;
    return loopXY(phase);
  });

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      {/* Title */}
      <div style={{ position: 'absolute', top: 30, left: 0, right: 0, textAlign: 'center' }}>
        <h1 style={{
          fontSize: 56, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleScale})`,
        }}>
          Current Flow Under Voltage — Ohm's Law in Motion
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          Watch the green charge dots speed up and slow down as V and R change.
        </p>
      </div>

      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: 'absolute', inset: 0, opacity: circuitOp }}>
        <defs>
          <radialGradient id="led-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={PAI_THEME.colors.ledGlow} stopOpacity={1} />
            <stop offset="60%" stopColor={PAI_THEME.colors.ledGlow} stopOpacity={0.3} />
            <stop offset="100%" stopColor={PAI_THEME.colors.ledGlow} stopOpacity={0} />
          </radialGradient>
        </defs>

        {/* ── Loop wires (skipping segments where components live) ── */}
        {/* Top: split around the switch and resistor */}
        <line x1={LOOP_LEFT} y1={LOOP_TOP} x2={SW_X - 24} y2={LOOP_TOP} stroke={PAI_THEME.colors.wire} strokeWidth={4} />
        <line x1={SW_X + 24} y1={LOOP_TOP} x2={RES_X - 38} y2={LOOP_TOP} stroke={PAI_THEME.colors.wire} strokeWidth={4} />
        <line x1={RES_X + 38} y1={LOOP_TOP} x2={LOOP_RIGHT} y2={LOOP_TOP} stroke={PAI_THEME.colors.wire} strokeWidth={4} />
        {/* Right: split around the LED */}
        <line x1={LOOP_RIGHT} y1={LOOP_TOP} x2={LOOP_RIGHT} y2={LED_Y - 22} stroke={PAI_THEME.colors.wire} strokeWidth={4} />
        <line x1={LOOP_RIGHT} y1={LED_Y + 22} x2={LOOP_RIGHT} y2={LOOP_BOTTOM} stroke={PAI_THEME.colors.wire} strokeWidth={4} />
        {/* Bottom: split around the battery */}
        <line x1={LOOP_RIGHT} y1={LOOP_BOTTOM} x2={BAT_X + 30} y2={LOOP_BOTTOM} stroke={PAI_THEME.colors.wire} strokeWidth={4} />
        <line x1={BAT_X - 30} y1={LOOP_BOTTOM} x2={LOOP_LEFT} y2={LOOP_BOTTOM} stroke={PAI_THEME.colors.wire} strokeWidth={4} />
        {/* Left: full vertical */}
        <line x1={LOOP_LEFT} y1={LOOP_BOTTOM} x2={LOOP_LEFT} y2={LOOP_TOP} stroke={PAI_THEME.colors.wire} strokeWidth={4} />

        {/* ── Charge dots (only when current is flowing) ── */}
        {regime.I_mA > 0 && dots.map((d, i) => (
          <circle key={i} cx={d.x} cy={d.y} r={DOT_R}
            fill={PAI_THEME.colors.currentFlow}
            stroke={PAI_THEME.colors.text} strokeWidth={1.5} />
        ))}

        {/* ── Switch ── */}
        <g>
          <circle cx={SW_X - 24} cy={SW_Y} r={5} fill={PAI_THEME.colors.switchColor} />
          <circle cx={SW_X + 24} cy={SW_Y} r={5} fill={PAI_THEME.colors.switchColor} />
          {switchClosed ? (
            <line x1={SW_X - 24} y1={SW_Y} x2={SW_X + 24} y2={SW_Y}
              stroke={PAI_THEME.colors.switchColor} strokeWidth={4} strokeLinecap="round" />
          ) : (
            <line x1={SW_X - 24} y1={SW_Y} x2={SW_X + 18} y2={SW_Y - 22}
              stroke={PAI_THEME.colors.switchColor} strokeWidth={4} strokeLinecap="round" />
          )}
          <text x={SW_X} y={SW_Y - 36} fill={PAI_THEME.colors.switchColor}
            fontSize={20} fontWeight={700} textAnchor="middle">
            switch ({switchClosed ? 'closed' : 'open'})
          </text>
        </g>

        {/* ── Resistor (zigzag) ── */}
        <g>
          {(() => {
            const halfW = 38;
            const dx = (2 * halfW) / 6;
            let p = `M ${RES_X - halfW},${RES_Y} `;
            for (let i = 0; i < 6; i++) {
              const x = RES_X - halfW + (i + 0.5) * dx;
              const y = RES_Y + (i % 2 === 0 ? -10 : 10);
              p += `L ${x.toFixed(1)},${y} `;
            }
            p += `L ${RES_X + halfW},${RES_Y}`;
            return <path d={p} fill="none" stroke={PAI_THEME.colors.resistor} strokeWidth={4} strokeLinejoin="miter" />;
          })()}
          <text x={RES_X} y={RES_Y - 26} fill={PAI_THEME.colors.resistor}
            fontSize={20} fontWeight={700} textAnchor="middle">
            R = {regime.R} Ω
          </text>
        </g>

        {/* ── LED ── */}
        <g>
          {ledBrightness > 0 && (
            <circle cx={LED_X} cy={LED_Y} r={50}
              fill="url(#led-glow)" opacity={ledBrightness} />
          )}
          <polygon points={`${LED_X - 14},${LED_Y - 16} ${LED_X - 14},${LED_Y + 16} ${LED_X + 12},${LED_Y}`}
            fill={ledBrightness > 0 ? PAI_THEME.colors.led : PAI_THEME.colors.background}
            stroke={PAI_THEME.colors.led} strokeWidth={3} />
          <line x1={LED_X + 12} y1={LED_Y - 16} x2={LED_X + 12} y2={LED_Y + 16}
            stroke={PAI_THEME.colors.led} strokeWidth={3} />
          {/* Light arrows when lit */}
          {ledBrightness > 0 && (
            <g opacity={ledBrightness}>
              <line x1={LED_X + 6} y1={LED_Y - 22} x2={LED_X + 28} y2={LED_Y - 38}
                stroke={PAI_THEME.colors.ledGlow} strokeWidth={3} />
              <polygon points={`${LED_X + 28},${LED_Y - 38} ${LED_X + 22},${LED_Y - 30} ${LED_X + 32},${LED_Y - 28}`}
                fill={PAI_THEME.colors.ledGlow} />
              <line x1={LED_X + 16} y1={LED_Y - 18} x2={LED_X + 38} y2={LED_Y - 28}
                stroke={PAI_THEME.colors.ledGlow} strokeWidth={3} />
              <polygon points={`${LED_X + 38},${LED_Y - 28} ${LED_X + 32},${LED_Y - 22} ${LED_X + 42},${LED_Y - 20}`}
                fill={PAI_THEME.colors.ledGlow} />
            </g>
          )}
          <text x={LED_X + 60} y={LED_Y + 6} fill={PAI_THEME.colors.led}
            fontSize={20} fontWeight={700}>
            LED
          </text>
        </g>

        {/* ── Battery (multi-cell symbol horizontal) ── */}
        <g>
          <line x1={BAT_X - 24} y1={BAT_Y - 18} x2={BAT_X - 24} y2={BAT_Y + 18}
            stroke={PAI_THEME.colors.batteryNeg} strokeWidth={3} />
          <line x1={BAT_X - 8} y1={BAT_Y - 30} x2={BAT_X - 8} y2={BAT_Y + 30}
            stroke={PAI_THEME.colors.batteryPos} strokeWidth={4} />
          <line x1={BAT_X + 8} y1={BAT_Y - 18} x2={BAT_X + 8} y2={BAT_Y + 18}
            stroke={PAI_THEME.colors.batteryNeg} strokeWidth={3} />
          <line x1={BAT_X + 24} y1={BAT_Y - 30} x2={BAT_X + 24} y2={BAT_Y + 30}
            stroke={PAI_THEME.colors.batteryPos} strokeWidth={4} />
          <text x={BAT_X} y={BAT_Y + 60} fill={PAI_THEME.colors.batteryPos}
            fontSize={26} fontWeight={700} textAnchor="middle">
            V = {regime.V} V
          </text>
        </g>

        {/* ── V/I/R readout panel (right side) ── */}
        <g transform="translate(1420, 280)">
          <rect x={0} y={0} width={420} height={420} rx={16}
            fill={PAI_THEME.colors.backgroundAlt} stroke={PAI_THEME.colors.textMuted} strokeWidth={2} />
          <text x={210} y={48} fill={PAI_THEME.colors.text}
            fontSize={32} fontWeight={700} textAnchor="middle">
            Live Values
          </text>

          {/* V */}
          <text x={30} y={120} fill={PAI_THEME.colors.batteryPos} fontSize={28} fontWeight={700}>V (voltage)</text>
          <text x={390} y={120} fill={PAI_THEME.colors.batteryPos}
            fontSize={42} fontWeight={700} textAnchor="end">{regime.V} V</text>

          {/* I */}
          <text x={30} y={210} fill={PAI_THEME.colors.currentFlow} fontSize={28} fontWeight={700}>I (current)</text>
          <text x={390} y={210} fill={PAI_THEME.colors.currentFlow}
            fontSize={42} fontWeight={700} textAnchor="end">
            {regime.I_mA.toFixed(1)} mA
          </text>

          {/* R */}
          <text x={30} y={300} fill={PAI_THEME.colors.resistor} fontSize={28} fontWeight={700}>R (resistance)</text>
          <text x={390} y={300} fill={PAI_THEME.colors.resistor}
            fontSize={42} fontWeight={700} textAnchor="end">{regime.R} Ω</text>

          {/* Ohm's law equation */}
          <line x1={30} y1={340} x2={390} y2={340} stroke={PAI_THEME.colors.textMuted} strokeWidth={1.5} />
          <text x={210} y={384} fill={PAI_THEME.colors.text}
            fontSize={32} fontWeight={700} textAnchor="middle" fontStyle="italic">
            I = V / R
          </text>
        </g>

        {/* Caption */}
        <text x={960} y={830} fill={regime.color}
          fontSize={36} fontWeight={700} textAnchor="middle">
          {regime.caption}
        </text>

        {/* Regime tag (small, top-right of circuit) */}
        <text x={1300} y={250} fill={regime.color}
          fontSize={22} fontWeight={700} textAnchor="end" fontStyle="italic">
          regime {regime.regime}
        </text>
      </svg>

      {/* Bottom strapline */}
      <div style={{
        position: 'absolute', top: 1010, left: 0, right: 0, textAlign: 'center',
        fontSize: 22, color: PAI_THEME.colors.textMuted,
      }}>
        Each green dot is a stand-in for "a tiny packet of charge". More dots-per-second past a point = more current.
      </div>
    </AbsoluteFill>
  );
};
