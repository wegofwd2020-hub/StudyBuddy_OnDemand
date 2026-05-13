/**
 * ReactionCoordinateScene — animated reaction-coordinate diagram.
 *
 * Story arc (30 fps, 26 s = 780 frames):
 *   0–60       title + subtitle fade in
 *   60–150     axes draw + reactant/product baselines appear; reactant + product
 *              labels mounted on their respective levels
 *   150–360    bell-curve traces from left baseline up over the activation-energy
 *              peak and down to the product baseline (stroke-dashoffset technique)
 *   180–540    a "tracer" particle (the reaction's progress dot) walks along the
 *              curve. Two reactant molecules (A, B) approach from the left,
 *              collide near the peak; transition-state ‡ flash; products (C, D)
 *              emerge and slide to the product level.
 *   360–540    Ea bracket draws + label appears
 *   540–660    ΔH bracket draws + label appears; product level pulses green
 *   660–780    closing tag — "ΔG decides IF, Ea decides HOW FAST."
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Geometry (1920 × 1080 stage) ─────────────────────────────────────────────
const PLOT_X0 = 220;
const PLOT_Y0 = 880;     // baseline of the energy axis
const PLOT_X1 = 1700;
const PLOT_Y1 = 240;     // top of the energy axis

const REACTANT_X = 360;
const PRODUCT_X = 1560;
const PEAK_X = 960;
const REACTANT_Y = 600;   // mid-height — reactant level
const PRODUCT_Y = 800;    // lower — product level (exothermic)
const PEAK_Y = 320;       // high — activation-energy peak

// ── Curve sampler — produces the same Bezier path used by the SVG stroke ────
// Path: M reactantX,reactantY  Q (bx1,by1) peakX,peakY  Q (bx2,by2) productX,productY
// We'll use two quadratics joined at the peak for a smooth bell shape.
const BX1 = 600;
const BY1 = REACTANT_Y;     // flat then climb
const BX2 = 1320;
const BY2 = PRODUCT_Y;      // settle to product line

// Quadratic Bezier helper: returns {x, y} at parametric t∈[0,1] on a quadratic.
const quadratic = (
  t: number,
  p0x: number, p0y: number,
  p1x: number, p1y: number,
  p2x: number, p2y: number,
) => {
  const u = 1 - t;
  return {
    x: u * u * p0x + 2 * u * t * p1x + t * t * p2x,
    y: u * u * p0y + 2 * u * t * p1y + t * t * p2y,
  };
};

// Walk a tracer along the full path (two halves of the curve glued at the peak).
// progress in [0, 1]; 0 → reactant, 0.5 → peak, 1 → product
const tracerPos = (progress: number) => {
  if (progress <= 0.5) {
    const t = progress / 0.5;
    return quadratic(t, REACTANT_X, REACTANT_Y, BX1, BY1, PEAK_X, PEAK_Y);
  }
  const t = (progress - 0.5) / 0.5;
  return quadratic(t, PEAK_X, PEAK_Y, BX2, BY2, PRODUCT_X, PRODUCT_Y);
};

// ── Frame anchors ────────────────────────────────────────────────────────────
const F_TITLE_END = 60;
const F_AXES_IN = 60;
const F_AXES_END = 150;
const F_CURVE_IN = 150;
const F_CURVE_END = 360;
const F_PARTICLES_IN = 180;
const F_COLLISION = 360;
const F_PARTICLES_END = 540;
const F_EA_IN = 360;
const F_EA_END = 480;
const F_DH_IN = 540;
const F_DH_END = 660;
const F_TAG_IN = 660;

// Approximate path length for stroke-dashoffset trick — generous bound.
const CURVE_LENGTH = 2400;

export const ReactionCoordinateScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Title (0 → 60) ────────────────────────────────────────────────────────
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, F_TITLE_END], [0, 1], { extrapolateRight: 'clamp' });

  // Title persists through tag — does not vanish.
  const titlePersist = interpolate(frame, [F_TAG_IN, F_TAG_IN + 30], [1, 0.4], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // ── Axes & baselines (60 → 150) ───────────────────────────────────────────
  const axesOp = interpolate(frame, [F_AXES_IN, F_AXES_END], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // ── Curve trace (150 → 360) ───────────────────────────────────────────────
  const curveProgress = interpolate(frame, [F_CURVE_IN, F_CURVE_END], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const dashOffset = CURVE_LENGTH * (1 - curveProgress);

  // ── Tracer / molecule animation (180 → 540) ───────────────────────────────
  const tracerProgress = interpolate(frame, [F_PARTICLES_IN, F_PARTICLES_END], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const tracer = tracerPos(tracerProgress);

  // Reactants (A, B) approach from below the curve up to the tracer until peak.
  // Before F_PARTICLES_IN they sit at staging positions; during 180→360 they
  // walk along the curve up to the peak; at the peak they merge into the
  // transition-state flash; from 360→540 the products emerge and slide down.
  const beforeCollision = frame < F_COLLISION;
  const collisionFlash = interpolate(
    frame, [F_COLLISION - 8, F_COLLISION, F_COLLISION + 12, F_COLLISION + 30],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  // Slight wiggle for atom positions
  const wiggle = (idx: number) => Math.sin((frame + idx * 7) * 0.18) * 4;

  // Pre-collision reactant positions: slightly offset from the tracer
  const aOffsetX = -34;
  const bOffsetX = +34;
  const aPre = { x: tracer.x + aOffsetX, y: tracer.y + wiggle(0) };
  const bPre = { x: tracer.x + bOffsetX, y: tracer.y + wiggle(1) };

  // Post-collision: products (C = single atom, D = single atom) slide ALONG the
  // descending curve out to the product level.
  const post = tracerPos(tracerProgress);
  const cOffsetX = -28;
  const dOffsetX = +28;
  const cPost = { x: post.x + cOffsetX, y: post.y + wiggle(2) };
  const dPost = { x: post.x + dOffsetX, y: post.y + wiggle(3) };

  // Visibility of pre / post particle pairs
  const preOp = interpolate(frame, [F_PARTICLES_IN - 10, F_PARTICLES_IN, F_COLLISION - 10, F_COLLISION + 5], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const postOp = interpolate(frame, [F_COLLISION + 5, F_COLLISION + 25, F_PARTICLES_END, F_PARTICLES_END + 30], [0, 1, 1, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // ── Ea bracket (360 → 480) ────────────────────────────────────────────────
  const eaOp = interpolate(frame, [F_EA_IN, F_EA_END], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // ── ΔH bracket (540 → 660) ────────────────────────────────────────────────
  const dhOp = interpolate(frame, [F_DH_IN, F_DH_END], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const productGlow = interpolate(
    frame, [F_DH_END - 30, F_DH_END, F_DH_END + 60],
    [0, 18, 6],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  // ── Closing tag ───────────────────────────────────────────────────────────
  const tagOp = interpolate(frame, [F_TAG_IN, F_TAG_IN + 30], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
        fontFamily: PAI_THEME.typography.fontFamily,
      }}
    >
      {/* ── Title ───────────────────────────────────────────────── */}
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
            fontSize: 56,
            color: PAI_THEME.colors.text,
            margin: 0,
            transform: `scale(${titleScale})`,
          }}
        >
          Reaction Coordinate — Climbing the Activation-Energy Hill
        </h1>
        <p
          style={{
            fontSize: 26,
            color: PAI_THEME.colors.accentLight,
            marginTop: 6,
            fontStyle: 'italic',
            opacity: subOp,
          }}
        >
          A + B  →  C + D     · exothermic ·     E_a, ‡, ΔH
        </p>
      </div>

      {/* ── Plot ───────────────────────────────────────────────── */}
      <svg
        width={1920}
        height={1080}
        viewBox="0 0 1920 1080"
        style={{ position: 'absolute', inset: 0 }}
      >
        <defs>
          <radialGradient id="rc-flash" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={PAI_THEME.colors.transitionState} stopOpacity={1} />
            <stop offset="60%" stopColor={PAI_THEME.colors.transitionState} stopOpacity={0.5} />
            <stop offset="100%" stopColor={PAI_THEME.colors.transitionState} stopOpacity={0} />
          </radialGradient>
          <marker id="rc-down-arrow" viewBox="0 0 10 10" refX={5} refY={10} markerWidth={8} markerHeight={8} orient="auto">
            <path d="M 0 0 L 5 10 L 10 0 z" fill={PAI_THEME.colors.error} />
          </marker>
          <marker id="rc-up-arrow" viewBox="0 0 10 10" refX={5} refY={0} markerWidth={8} markerHeight={8} orient="auto">
            <path d="M 0 10 L 5 0 L 10 10 z" fill={PAI_THEME.colors.warning} />
          </marker>
        </defs>

        {/* Axes */}
        <g opacity={axesOp}>
          <line
            x1={PLOT_X0}
            y1={PLOT_Y0}
            x2={PLOT_X0}
            y2={PLOT_Y1}
            stroke={PAI_THEME.colors.text}
            strokeWidth={3}
          />
          <line
            x1={PLOT_X0}
            y1={PLOT_Y0}
            x2={PLOT_X1}
            y2={PLOT_Y0}
            stroke={PAI_THEME.colors.text}
            strokeWidth={3}
          />
          <text
            x={PLOT_X0 - 30}
            y={(PLOT_Y0 + PLOT_Y1) / 2}
            transform={`rotate(-90 ${PLOT_X0 - 30} ${(PLOT_Y0 + PLOT_Y1) / 2})`}
            fill={PAI_THEME.colors.text}
            fontSize={28}
            fontWeight={700}
            textAnchor="middle"
          >
            Energy
          </text>
          <text
            x={(PLOT_X0 + PLOT_X1) / 2}
            y={PLOT_Y0 + 50}
            fill={PAI_THEME.colors.text}
            fontSize={28}
            fontWeight={700}
            textAnchor="middle"
          >
            Reaction coordinate (progress) →
          </text>

          {/* Reactant + product reference dashed lines */}
          <line
            x1={PLOT_X0}
            y1={REACTANT_Y}
            x2={PLOT_X1}
            y2={REACTANT_Y}
            stroke={PAI_THEME.colors.textDark}
            strokeWidth={1.2}
            strokeDasharray="6 6"
            opacity={0.5}
          />
          <line
            x1={PLOT_X0}
            y1={PRODUCT_Y}
            x2={PLOT_X1}
            y2={PRODUCT_Y}
            stroke={PAI_THEME.colors.textDark}
            strokeWidth={1.2}
            strokeDasharray="6 6"
            opacity={0.5}
          />
        </g>

        {/* Reactant level marker + label */}
        <g opacity={axesOp}>
          <circle cx={REACTANT_X} cy={REACTANT_Y} r={10} fill={PAI_THEME.colors.reactant} stroke={PAI_THEME.colors.text} strokeWidth={2} />
          <text
            x={REACTANT_X}
            y={REACTANT_Y - 24}
            fill={PAI_THEME.colors.text}
            fontSize={26}
            fontWeight={700}
            textAnchor="middle"
          >
            reactants
          </text>
          <text
            x={REACTANT_X}
            y={REACTANT_Y - 50}
            fill={PAI_THEME.colors.textMuted}
            fontSize={22}
            textAnchor="middle"
          >
            A + B
          </text>
        </g>

        {/* Product level marker + label */}
        <g opacity={axesOp}>
          <circle
            cx={PRODUCT_X}
            cy={PRODUCT_Y}
            r={10}
            fill={PAI_THEME.colors.product}
            stroke={PAI_THEME.colors.text}
            strokeWidth={2}
            style={{ filter: productGlow > 4 ? `drop-shadow(0 0 ${productGlow}px ${PAI_THEME.colors.product})` : undefined }}
          />
          <text
            x={PRODUCT_X}
            y={PRODUCT_Y + 38}
            fill={PAI_THEME.colors.text}
            fontSize={26}
            fontWeight={700}
            textAnchor="middle"
          >
            products
          </text>
          <text
            x={PRODUCT_X}
            y={PRODUCT_Y + 64}
            fill={PAI_THEME.colors.textMuted}
            fontSize={22}
            textAnchor="middle"
          >
            C + D
          </text>
        </g>

        {/* Energy bell curve — drawn with stroke-dashoffset trick */}
        <path
          d={`M ${REACTANT_X} ${REACTANT_Y} Q ${BX1} ${BY1} ${PEAK_X} ${PEAK_Y} Q ${BX2} ${BY2} ${PRODUCT_X} ${PRODUCT_Y}`}
          fill="none"
          stroke={PAI_THEME.colors.energyCurve}
          strokeWidth={6}
          strokeLinecap="round"
          strokeDasharray={CURVE_LENGTH}
          strokeDashoffset={dashOffset}
        />

        {/* Transition-state marker at the peak */}
        {curveProgress >= 1 && (
          <g>
            <circle cx={PEAK_X} cy={PEAK_Y} r={9} fill={PAI_THEME.colors.transitionState} stroke={PAI_THEME.colors.text} strokeWidth={2} />
            <text x={PEAK_X} y={PEAK_Y - 28} fill={PAI_THEME.colors.transitionState} fontSize={26} fontWeight={700} textAnchor="middle">
              transition state ‡
            </text>
          </g>
        )}

        {/* Collision flash at the peak */}
        {collisionFlash > 0 && (
          <circle cx={PEAK_X} cy={PEAK_Y} r={70 + 30 * collisionFlash} fill="url(#rc-flash)" opacity={collisionFlash} />
        )}

        {/* Reactant molecules (pre-collision) — A and B walking up the curve */}
        {beforeCollision && preOp > 0 && (
          <g opacity={preOp}>
            <circle cx={aPre.x} cy={aPre.y} r={28} fill={PAI_THEME.colors.reactant} stroke={PAI_THEME.colors.text} strokeWidth={2.5} />
            <text x={aPre.x} y={aPre.y + 8} fontSize={24} fontWeight={700} fill={PAI_THEME.colors.text} textAnchor="middle">A</text>

            <circle cx={bPre.x} cy={bPre.y} r={28} fill={PAI_THEME.colors.reactant} stroke={PAI_THEME.colors.text} strokeWidth={2.5} />
            <text x={bPre.x} y={bPre.y + 8} fontSize={24} fontWeight={700} fill={PAI_THEME.colors.text} textAnchor="middle">B</text>
          </g>
        )}

        {/* Product molecules (post-collision) — C and D sliding to product level */}
        {!beforeCollision && postOp > 0 && (
          <g opacity={postOp}>
            <circle cx={cPost.x} cy={cPost.y} r={26} fill={PAI_THEME.colors.product} stroke={PAI_THEME.colors.text} strokeWidth={2.5} />
            <text x={cPost.x} y={cPost.y + 8} fontSize={22} fontWeight={700} fill={PAI_THEME.colors.background} textAnchor="middle">C</text>

            <circle cx={dPost.x} cy={dPost.y} r={26} fill={PAI_THEME.colors.product} stroke={PAI_THEME.colors.text} strokeWidth={2.5} />
            <text x={dPost.x} y={dPost.y + 8} fontSize={22} fontWeight={700} fill={PAI_THEME.colors.background} textAnchor="middle">D</text>
          </g>
        )}

        {/* ── Ea bracket (vertical, from reactant level up to peak) ── */}
        <g opacity={eaOp}>
          <line
            x1={PEAK_X - 200}
            y1={REACTANT_Y}
            x2={PEAK_X - 200}
            y2={PEAK_Y}
            stroke={PAI_THEME.colors.warning}
            strokeWidth={4}
            markerEnd="url(#rc-up-arrow)"
          />
          <line x1={PEAK_X - 215} y1={REACTANT_Y} x2={PEAK_X - 185} y2={REACTANT_Y} stroke={PAI_THEME.colors.warning} strokeWidth={3} />
          <line x1={PEAK_X - 215} y1={PEAK_Y} x2={PEAK_X - 185} y2={PEAK_Y} stroke={PAI_THEME.colors.warning} strokeWidth={3} />
          <rect
            x={PEAK_X - 320}
            y={(REACTANT_Y + PEAK_Y) / 2 - 28}
            width={104}
            height={56}
            rx={8}
            fill={PAI_THEME.colors.backgroundAlt}
            stroke={PAI_THEME.colors.warning}
            strokeWidth={2}
          />
          <text
            x={PEAK_X - 268}
            y={(REACTANT_Y + PEAK_Y) / 2 + 10}
            fontSize={36}
            fontWeight={700}
            fill={PAI_THEME.colors.warning}
            textAnchor="middle"
          >
            E_a
          </text>
        </g>

        {/* ── ΔH bracket (vertical, from reactant level down to product level) ── */}
        <g opacity={dhOp}>
          <line
            x1={PRODUCT_X + 90}
            y1={REACTANT_Y}
            x2={PRODUCT_X + 90}
            y2={PRODUCT_Y}
            stroke={PAI_THEME.colors.error}
            strokeWidth={4}
            markerEnd="url(#rc-down-arrow)"
          />
          <line x1={PRODUCT_X + 75} y1={REACTANT_Y} x2={PRODUCT_X + 105} y2={REACTANT_Y} stroke={PAI_THEME.colors.error} strokeWidth={3} />
          <line x1={PRODUCT_X + 75} y1={PRODUCT_Y} x2={PRODUCT_X + 105} y2={PRODUCT_Y} stroke={PAI_THEME.colors.error} strokeWidth={3} />
          <rect
            x={PRODUCT_X + 116}
            y={(REACTANT_Y + PRODUCT_Y) / 2 - 28}
            width={134}
            height={56}
            rx={8}
            fill={PAI_THEME.colors.backgroundAlt}
            stroke={PAI_THEME.colors.error}
            strokeWidth={2}
          />
          <text
            x={PRODUCT_X + 183}
            y={(REACTANT_Y + PRODUCT_Y) / 2 + 10}
            fontSize={32}
            fontWeight={700}
            fill={PAI_THEME.colors.error}
            textAnchor="middle"
          >
            ΔH &lt; 0
          </text>
        </g>
      </svg>

      {/* ── Closing tag ───────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 940,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: tagOp,
        }}
      >
        <div
          style={{
            display: 'inline-block',
            padding: '20px 44px',
            borderRadius: 18,
            background: PAI_THEME.colors.warmWash,
            border: `3px solid ${PAI_THEME.colors.warning}`,
          }}
        >
          <div style={{ fontSize: 38, fontWeight: 700, color: PAI_THEME.colors.text }}>
            ΔG decides <span style={{ color: PAI_THEME.colors.success }}>IF</span>.   E_a decides <span style={{ color: PAI_THEME.colors.warning }}>HOW FAST</span>.
          </div>
          <div style={{ fontSize: 22, color: PAI_THEME.colors.textMuted, marginTop: 8 }}>
            A catalyst lowers E_a — start and end energies stay put.
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
