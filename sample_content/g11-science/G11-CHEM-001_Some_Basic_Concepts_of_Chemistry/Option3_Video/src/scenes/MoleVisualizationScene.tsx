/**
 * MoleVisualizationScene — visualises 1 mole of carbon-12.
 *
 * Story arc:
 *   1. A spoonful of charcoal (12 g of ¹²C) sits centre-stage.
 *   2. Zoom in: an expanding grid of dots floods the frame, suggesting the
 *      6.022 × 10²³ atoms inside.
 *   3. The number 6.022 × 10²³ writes itself out in giant type.
 *   4. Three scale comparisons fly in one at a time:
 *      - "Marbles, Earth knee-deep"
 *      - "Seconds, ~1 million × age of universe"
 *      - "Drops of water — a 0.6-billion-cubic-km ocean"
 *   5. Closing tag: "1 mole = a counting unit. The bridge between mass and
 *      atoms."
 *
 * Frames @ 30 fps (28 s total = 840 frames):
 *   0–60     title fades in
 *   60–150   spoon + 12 g of carbon appears
 *   150–270  dots flood in, suggesting atoms
 *   270–390  big number writes out: 6.022 × 10²³
 *   390–510  comparison 1 — marbles + Earth
 *   510–630  comparison 2 — clock + universe age
 *   630–750  comparison 3 — water drops + ocean
 *   750–840  closing tag
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Frame anchors ───────────────────────────────────────────────────────────
const F_TITLE_END = 60;
const F_SPOON_IN = 60;
const F_SPOON_END = 150;
const F_DOTS_IN = 150;
const F_DOTS_END = 270;
const F_BIGNUM_IN = 270;
const F_BIGNUM_END = 390;
const F_C1_IN = 390;
const F_C1_END = 510;
const F_C2_IN = 510;
const F_C2_END = 630;
const F_C3_IN = 630;
const F_C3_END = 750;
const F_TAG_IN = 750;

// ── Layout constants ────────────────────────────────────────────────────────
const STAGE_CX = 960;
const STAGE_CY = 540;

// Dot-flood grid: 30 cols × 20 rows = 600 dots, suggestive of ~10²³
const DOT_COLS = 30;
const DOT_ROWS = 20;
const DOT_GAP_X = 50;
const DOT_GAP_Y = 50;
const DOT_GRID_W = (DOT_COLS - 1) * DOT_GAP_X;
const DOT_GRID_H = (DOT_ROWS - 1) * DOT_GAP_Y;
const DOT_ORIGIN_X = STAGE_CX - DOT_GRID_W / 2;
const DOT_ORIGIN_Y = STAGE_CY - DOT_GRID_H / 2;

export const MoleVisualizationScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Title (0–60) ────────────────────────────────────────────────────────
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  // Title gracefully recedes when the spoon arrives
  const titlePersist = interpolate(frame, [F_DOTS_IN, F_DOTS_IN + 20], [1, 0.3], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // ── Stage 1: spoon + 12 g of carbon (60–150) ────────────────────────────
  const spoonOp = interpolate(frame, [F_SPOON_IN, F_SPOON_IN + 25], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  // Spoon shrinks/fades when dots take over
  const spoonShrink = interpolate(frame, [F_DOTS_IN, F_DOTS_IN + 30], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // ── Stage 2: dot flood (150–270) ────────────────────────────────────────
  // Dots fade in cascade — each row's threshold staggered by frame index.
  // dotProgress maps 0..1 across F_DOTS_IN → F_DOTS_IN + 90 (3 s flood).
  const dotProgress = interpolate(frame, [F_DOTS_IN, F_DOTS_IN + 90], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  // After flood, dots persist but dim when big number arrives.
  const dotPersist = interpolate(frame, [F_BIGNUM_IN, F_BIGNUM_IN + 30], [1, 0.2], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // ── Stage 3: big number writeout (270–390) ──────────────────────────────
  const bignumOp = interpolate(frame, [F_BIGNUM_IN, F_BIGNUM_IN + 30], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const bignumScale = spring({
    frame: frame - F_BIGNUM_IN,
    fps,
    config: PAI_THEME.animation.springDefault,
  });
  const bignumPersist = interpolate(frame, [F_C1_IN, F_C1_IN + 25], [1, 0.45], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // ── Stage 4–6: three comparisons ─────────────────────────────────────────
  const comparisons = [
    {
      inFrame: F_C1_IN,
      outFrame: F_C1_END,
      x: 380,
      label: 'A mole of marbles',
      detail: 'would cover Earth ~80 km deep',
      kind: 'marbles' as const,
    },
    {
      inFrame: F_C2_IN,
      outFrame: F_C2_END,
      x: 960,
      label: 'A mole of seconds',
      detail: '≈ 1.9 × 10¹⁶ years — a million ages of the universe',
      kind: 'clock' as const,
    },
    {
      inFrame: F_C3_IN,
      outFrame: F_C3_END,
      x: 1540,
      label: 'A mole of water drops',
      detail: 'fills the volume of all of Earth\'s oceans, and then some',
      kind: 'drops' as const,
    },
  ];

  // ── Closing tag (750–840) ────────────────────────────────────────────────
  const tagOp = interpolate(frame, [F_TAG_IN, F_TAG_IN + 30], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Helper: per-comparison opacity based on a fade-in/fade-out band
  const cmpOp = (inF: number, outF: number) => {
    const fadeIn = interpolate(frame, [inF, inF + 20], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
    // After comparison's outFrame, dim slightly but keep visible until tag
    const sustain = interpolate(frame, [outF, outF + 20], [1, 0.55], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
    return fadeIn * sustain;
  };

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
        fontFamily: PAI_THEME.typography.fontFamily,
      }}
    >
      {/* ── Title ─────────────────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 36,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: titleOp * titlePersist,
        }}
      >
        <h1
          style={{
            fontSize: 60,
            color: PAI_THEME.colors.text,
            margin: 0,
            transform: `scale(${titleScale})`,
          }}
        >
          From Matter to the Mole
        </h1>
        <p
          style={{
            fontSize: 28,
            color: PAI_THEME.colors.accentLight,
            marginTop: 6,
            fontStyle: 'italic',
            opacity: subOp,
          }}
        >
          How big is 6.022 × 10²³?  ·  A counting unit for a world of atoms.
        </p>
      </div>

      {/* ── Stage 1: spoon of 12 g carbon ───────────────────────────────── */}
      <svg
        width={1920}
        height={1080}
        viewBox="0 0 1920 1080"
        style={{
          position: 'absolute',
          inset: 0,
          opacity: spoonOp * spoonShrink,
        }}
      >
        {/* Spoon bowl */}
        <ellipse
          cx={STAGE_CX}
          cy={STAGE_CY}
          rx={220}
          ry={88}
          fill={PAI_THEME.colors.paperGround}
          stroke={PAI_THEME.colors.text}
          strokeWidth={4}
        />
        {/* Spoon handle */}
        <rect
          x={STAGE_CX + 200}
          y={STAGE_CY - 18}
          width={260}
          height={26}
          rx={10}
          fill={PAI_THEME.colors.paperGround}
          stroke={PAI_THEME.colors.text}
          strokeWidth={4}
        />

        {/* Charcoal heap (carbon) */}
        <ellipse
          cx={STAGE_CX}
          cy={STAGE_CY - 8}
          rx={180}
          ry={56}
          fill={PAI_THEME.colors.carbon}
        />
        {/* Specks */}
        {Array.from({ length: 22 }).map((_, i) => {
          const angle = (i / 22) * Math.PI * 2;
          const r = 30 + 110 * ((i * 17) % 7) / 7;
          const cx = STAGE_CX + r * Math.cos(angle);
          const cy = STAGE_CY - 14 + 26 * Math.sin(angle);
          return (
            <circle
              key={i}
              cx={cx}
              cy={cy}
              r={3 + (i % 4)}
              fill="#000000"
              opacity={0.7}
            />
          );
        })}

        {/* Mass label */}
        <rect
          x={STAGE_CX - 130}
          y={STAGE_CY + 130}
          width={260}
          height={56}
          rx={28}
          fill={PAI_THEME.colors.warning}
          opacity={0.92}
        />
        <text
          x={STAGE_CX}
          y={STAGE_CY + 168}
          fontSize={36}
          fontWeight={700}
          fill={PAI_THEME.colors.background}
          textAnchor="middle"
        >
          12 g of ¹²C
        </text>

        {/* Caption */}
        <text
          x={STAGE_CX}
          y={STAGE_CY - 130}
          fontSize={28}
          fontWeight={600}
          fill={PAI_THEME.colors.textMuted}
          textAnchor="middle"
        >
          a teaspoon of charcoal — fits in your hand
        </text>
      </svg>

      {/* ── Stage 2: dot flood ──────────────────────────────────────────── */}
      <svg
        width={1920}
        height={1080}
        viewBox="0 0 1920 1080"
        style={{
          position: 'absolute',
          inset: 0,
          opacity: dotPersist,
        }}
      >
        {Array.from({ length: DOT_ROWS }).map((_, row) =>
          Array.from({ length: DOT_COLS }).map((_, col) => {
            const idx = row * DOT_COLS + col;
            // Stagger by index — each dot's appearance threshold is offset.
            const threshold = idx / (DOT_COLS * DOT_ROWS);
            const visible = dotProgress > threshold;
            if (!visible) return null;

            // Per-dot fade-in over a small window past its threshold.
            const localProgress = Math.min(
              1,
              (dotProgress - threshold) / 0.05,
            );
            const opacity = localProgress * 0.85;
            const radius = 4 + 1.5 * localProgress;

            const cx = DOT_ORIGIN_X + col * DOT_GAP_X;
            const cy = DOT_ORIGIN_Y + row * DOT_GAP_Y;

            // Mix of two atom colours (carbon-charcoal vs straw) for variety
            const fill =
              (row + col) % 3 === 0
                ? PAI_THEME.colors.warning
                : PAI_THEME.colors.accentLight;

            return (
              <circle
                key={`${row}-${col}`}
                cx={cx}
                cy={cy}
                r={radius}
                fill={fill}
                opacity={opacity}
              />
            );
          }),
        )}
      </svg>

      {/* ── Stage 3: big number ─────────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 380,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: bignumOp * bignumPersist,
          transform: `scale(${bignumScale})`,
        }}
      >
        <div
          style={{
            fontSize: 28,
            color: PAI_THEME.colors.textMuted,
            letterSpacing: 6,
            textTransform: 'uppercase',
            marginBottom: 12,
          }}
        >
          Avogadro's number
        </div>
        <div
          style={{
            fontSize: 200,
            fontWeight: 700,
            color: PAI_THEME.colors.warning,
            lineHeight: 1,
            textShadow: `0 0 40px ${PAI_THEME.colors.warning}55`,
          }}
        >
          6.022 × 10
          <span style={{ fontSize: 130, verticalAlign: 'super' }}>23</span>
        </div>
        <div
          style={{
            fontSize: 32,
            color: PAI_THEME.colors.text,
            marginTop: 16,
          }}
        >
          atoms in 12 g of ¹²C  ·  also: 1 mole of anything
        </div>
      </div>

      {/* ── Stages 4–6: three comparison cards ──────────────────────────── */}
      <svg
        width={1920}
        height={1080}
        viewBox="0 0 1920 1080"
        style={{ position: 'absolute', inset: 0 }}
      >
        {comparisons.map((c, i) => {
          const op = cmpOp(c.inFrame, c.outFrame);
          if (op <= 0.001) return null;

          const cardX = c.x - 230;
          const cardY = 800;
          const cardW = 460;
          const cardH = 230;

          return (
            <g key={i} opacity={op}>
              {/* Card background */}
              <rect
                x={cardX}
                y={cardY}
                width={cardW}
                height={cardH}
                rx={20}
                fill={PAI_THEME.colors.backgroundAlt}
                stroke={PAI_THEME.colors.accent}
                strokeWidth={3}
              />

              {/* Icon area */}
              <g transform={`translate(${c.x}, ${cardY + 70})`}>
                {c.kind === 'marbles' && (
                  <>
                    {/* Earth */}
                    <circle r={42} fill="#bfdbfe" stroke="#1e3a8a" strokeWidth={2.5} />
                    <path
                      d="M -28 -16 Q -10 -22 8 -14 Q 24 -22 32 -8"
                      fill="#15803d"
                      opacity={0.8}
                    />
                    <path
                      d="M -30 8 Q -12 4 14 14 Q 24 12 30 6"
                      fill="#15803d"
                      opacity={0.8}
                    />
                    {/* Marble layer ring */}
                    <circle
                      r={56}
                      fill="none"
                      stroke={PAI_THEME.colors.warning}
                      strokeWidth={6}
                      strokeDasharray="3 4"
                    />
                  </>
                )}
                {c.kind === 'clock' && (
                  <>
                    <circle r={42} fill={PAI_THEME.colors.background} stroke={PAI_THEME.colors.accentLight} strokeWidth={3} />
                    <line x1={0} y1={0} x2={0} y2={-28} stroke={PAI_THEME.colors.accentLight} strokeWidth={3} />
                    <line x1={0} y1={0} x2={22} y2={12} stroke={PAI_THEME.colors.accentLight} strokeWidth={3} />
                    <circle r={3} fill={PAI_THEME.colors.accentLight} />
                  </>
                )}
                {c.kind === 'drops' && (
                  <>
                    {/* three water-drop shapes */}
                    <path
                      d="M -20 -10 Q -36 12 -20 24 Q -4 12 -20 -10 Z"
                      fill={PAI_THEME.colors.info}
                      stroke={PAI_THEME.colors.text}
                      strokeWidth={1.5}
                    />
                    <path
                      d="M 6 -22 Q -10 0 6 12 Q 22 0 6 -22 Z"
                      fill={PAI_THEME.colors.info}
                      stroke={PAI_THEME.colors.text}
                      strokeWidth={1.5}
                    />
                    <path
                      d="M 32 -8 Q 16 14 32 26 Q 48 14 32 -8 Z"
                      fill={PAI_THEME.colors.info}
                      stroke={PAI_THEME.colors.text}
                      strokeWidth={1.5}
                    />
                  </>
                )}
              </g>

              {/* Label */}
              <text
                x={c.x}
                y={cardY + 168}
                fontSize={26}
                fontWeight={700}
                fill={PAI_THEME.colors.text}
                textAnchor="middle"
              >
                {c.label}
              </text>
              <text
                x={c.x}
                y={cardY + 200}
                fontSize={18}
                fill={PAI_THEME.colors.textMuted}
                textAnchor="middle"
              >
                {c.detail}
              </text>
            </g>
          );
        })}
      </svg>

      {/* ── Closing tag ─────────────────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 80,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: tagOp,
        }}
      >
        <div
          style={{
            display: 'inline-block',
            padding: '24px 48px',
            borderRadius: 20,
            background: PAI_THEME.colors.warmWash,
            border: `3px solid ${PAI_THEME.colors.warning}`,
          }}
        >
          <div
            style={{
              fontSize: 44,
              fontWeight: 700,
              color: PAI_THEME.colors.text,
            }}
          >
            1 mole = the bridge between mass and atoms.
          </div>
          <div
            style={{
              fontSize: 26,
              color: PAI_THEME.colors.textMuted,
              marginTop: 10,
            }}
          >
            grams on the balance  ↔  atoms in the world
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
