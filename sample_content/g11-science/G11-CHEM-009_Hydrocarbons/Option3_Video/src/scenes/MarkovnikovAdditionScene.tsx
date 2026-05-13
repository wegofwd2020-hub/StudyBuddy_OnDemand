/**
 * MarkovnikovAdditionScene — animated electrophilic addition of HBr to propene.
 *
 * Reaction:
 *     CH₃-CH=CH₂  +  H-Br   →   CH₃-CHBr-CH₃   (2-bromopropane, Markovnikov product)
 *
 * Three phases over 28 s @ 30 fps (840 frames):
 *
 *   Phase 1  (0–8s, frames 0–240)
 *     Show propene with the C=C drawn explicitly. HBr enters from above.
 *     Highlight the π-bond electron pair on the alkene.
 *
 *   Phase 2  (8–18s, frames 240–540)
 *     Reveal the secondary-carbocation intermediate. H⁺ has added to the
 *     terminal CH₂ carbon, leaving a positive charge on the middle (more
 *     substituted) carbon. Display the rule. Show — in a faded/dashed
 *     panel — the rejected alternative pathway (H to internal C, + on
 *     terminal C) that would give a less-stable primary carbocation.
 *
 *   Phase 3  (18–28s, frames 540–840)
 *     Br⁻ attacks the secondary carbocation. Final product 2-bromopropane
 *     (CH₃-CHBr-CH₃) is drawn. Caption: "Markov-knee → the rich (in H)
 *     get richer."
 *
 * IMPORTANT (Remotion): `interpolate(value, [a, b], ...)` requires a strictly
 * INCREASING input range. To make a value DECREASE over time, flip the
 * OUTPUT range (e.g. [1, 0]), not the input.
 */
import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { PAI_THEME } from '../theme';

// ── Constants ───────────────────────────────────────────────────────────────
const FPS = 30;
const SEC = (s: number) => Math.round(s * FPS);

// Phase boundaries (frames)
const F_TITLE_END    = SEC(1.5);
const F_PROPENE_IN   = SEC(2);     // propene appears
const F_HBR_IN       = SEC(3.5);   // HBr glides in from above
const F_PI_HIGHLIGHT = SEC(5);     // π-bond highlight bloom
const F_PHASE1_END   = SEC(8);

const F_PHASE2_START = SEC(8);
const F_CATION_REVEAL = SEC(9.5);  // carbocation intermediate fades in
const F_RULE_IN      = SEC(11.5);  // rule banner
const F_REJECT_IN    = SEC(14);    // rejected alternative
const F_PHASE2_END   = SEC(18);

const F_PHASE3_START = SEC(18);
const F_BR_ATTACK    = SEC(19);    // Br⁻ approach
const F_PRODUCT_IN   = SEC(22);    // final product crystallises
const F_FINAL_CAP    = SEC(24.5);  // closing caption fades in

// Canvas geometry
const STAGE_W = 1920;
const STAGE_H = 1080;
const CX = 960;
const CY = 600;
const C_R = 38;
const ATOM_R = 30;
const SMALL_R = 22;

// ── Helpers ─────────────────────────────────────────────────────────────────
type Element = 'C' | 'H' | 'Br';

function atomColor(el: Element): string {
  switch (el) {
    case 'C': return PAI_THEME.colors.carbon;
    case 'H': return PAI_THEME.colors.hydrogen;
    case 'Br': return PAI_THEME.colors.bromine;
  }
}

function atomLabelColor(el: Element): string {
  return el === 'H' ? '#1a202c' : '#fff';
}

// Render a generic atom with its label, optionally with a coloured halo.
function Atom(props: {
  x: number;
  y: number;
  el: Element;
  r?: number;
  highlight?: boolean;
  opacity?: number;
}) {
  const { x, y, el, r = el === 'C' ? C_R : ATOM_R, highlight, opacity = 1 } = props;
  const stroke = highlight ? PAI_THEME.colors.fgHighlight : PAI_THEME.colors.text;
  const strokeWidth = highlight ? 5 : 3;
  return (
    <g opacity={opacity}>
      <circle cx={x} cy={y} r={r}
        fill={atomColor(el)} stroke={stroke} strokeWidth={strokeWidth} />
      <text x={x} y={y + (el === 'C' ? 13 : 10)}
        fontSize={el === 'C' ? 34 : 26} fontWeight={700}
        fill={atomLabelColor(el)} textAnchor="middle"
        fontFamily={PAI_THEME.typography.fontFamily}>
        {el}
      </text>
    </g>
  );
}

function SingleBond(props: { x1: number; y1: number; x2: number; y2: number; opacity?: number; color?: string; width?: number }) {
  const { x1, y1, x2, y2, opacity = 1, color = PAI_THEME.colors.bond, width = 6 } = props;
  return (
    <line x1={x1} y1={y1} x2={x2} y2={y2}
      stroke={color} strokeWidth={width} strokeLinecap="round" opacity={opacity} />
  );
}

function DoubleBond(props: { x1: number; y1: number; x2: number; y2: number; opacity?: number; color?: string }) {
  const { x1, y1, x2, y2, opacity = 1, color = PAI_THEME.colors.bond } = props;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const L = Math.sqrt(dx * dx + dy * dy) || 1;
  const px = (-dy / L) * 8;
  const py = (dx / L) * 8;
  return (
    <g opacity={opacity}>
      <line x1={x1 + px} y1={y1 + py} x2={x2 + px} y2={y2 + py}
        stroke={color} strokeWidth={6} strokeLinecap="round" />
      <line x1={x1 - px} y1={y1 - py} x2={x2 - px} y2={y2 - py}
        stroke={color} strokeWidth={6} strokeLinecap="round" />
    </g>
  );
}

// Charge badge — a small circled +/− label that hovers near an atom.
function Charge(props: { x: number; y: number; sign: '+' | '-'; opacity?: number }) {
  const { x, y, sign, opacity = 1 } = props;
  const color = sign === '+' ? PAI_THEME.colors.chargePos : PAI_THEME.colors.chargeNeg;
  return (
    <g opacity={opacity}>
      <circle cx={x} cy={y} r={22} fill={PAI_THEME.colors.background} stroke={color} strokeWidth={3} />
      <text x={x} y={y + 9} fontSize={28} fontWeight={800}
        fill={color} textAnchor="middle">{sign}</text>
    </g>
  );
}

// ── Component ───────────────────────────────────────────────────────────────
export const MarkovnikovAdditionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Title intro ──────────────────────────────────────────────────────────
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  // After the title settles we fade the subtitle out so it doesn't compete
  // with the rest of the scene. NOTE Remotion gotcha: input range must be
  // strictly increasing; to "fade out" we flip the OUTPUT range to [1, 0].
  const subFadeOut = interpolate(frame, [F_PHASE2_START, F_PHASE2_START + 30], [1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // ── Phase opacities ──────────────────────────────────────────────────────
  // Phase 1 fades in at F_PROPENE_IN, holds, then fades out as Phase 2 starts.
  const phase1In = interpolate(frame, [F_TITLE_END, F_PROPENE_IN], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const phase1Out = interpolate(frame, [F_PHASE1_END - 20, F_PHASE2_START + 10], [1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const phase1Op = phase1In * phase1Out;

  // HBr glide-in from top
  const hbrIn = interpolate(frame, [F_HBR_IN, F_HBR_IN + 30], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const hbrY = interpolate(frame, [F_HBR_IN, F_HBR_IN + 45], [200, 380], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // π-bond highlight — pulsing breathe
  const piHighlight = interpolate(frame, [F_PI_HIGHLIGHT, F_PI_HIGHLIGHT + 25], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const piPulse = 0.65 + 0.35 * Math.sin((frame - F_PI_HIGHLIGHT) * 0.18);

  // Phase 2 opacity envelope
  const phase2In = interpolate(frame, [F_PHASE2_START, F_PHASE2_START + 25], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const phase2Out = interpolate(frame, [F_PHASE2_END - 25, F_PHASE3_START + 10], [1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const phase2Op = phase2In * phase2Out;

  // Carbocation reveal + rule + rejection — staggered
  const cationOp = interpolate(frame, [F_CATION_REVEAL, F_CATION_REVEAL + 25], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const ruleOp = interpolate(frame, [F_RULE_IN, F_RULE_IN + 25], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const rejectOp = interpolate(frame, [F_REJECT_IN, F_REJECT_IN + 30], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // Phase 3
  const phase3In = interpolate(frame, [F_PHASE3_START, F_PHASE3_START + 25], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // Br⁻ approach from the right; pixel-x glides from off-canvas toward C_middle.
  const brX = interpolate(frame, [F_BR_ATTACK, F_BR_ATTACK + 80], [1600, 1010], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const brOp = interpolate(frame, [F_BR_ATTACK, F_BR_ATTACK + 25], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  // Carbocation fades as Br⁻ docks (it becomes neutral 2-bromopropane).
  const cationFadeOut = interpolate(frame, [F_PRODUCT_IN - 20, F_PRODUCT_IN + 5], [1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const productOp = interpolate(frame, [F_PRODUCT_IN, F_PRODUCT_IN + 30], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const finalCapOp = interpolate(frame, [F_FINAL_CAP, F_FINAL_CAP + 30], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // ── Geometry — propene CH₃-CH=CH₂ ─────────────────────────────────────────
  // Backbone laid out left → right.
  //   C1 (CH₃, left)      — terminal methyl
  //   C2 (middle, =CH-)
  //   C3 (CH₂, right)     — terminal =CH₂
  // The C2=C3 double bond is the alkene.
  const C1 = { x: CX - 280, y: CY };
  const C2 = { x: CX - 60,  y: CY };
  const C3 = { x: CX + 160, y: CY };

  // C1 methyl hydrogens (3 H)
  const C1H1 = { x: C1.x - 130, y: C1.y - 70 };
  const C1H2 = { x: C1.x - 130, y: C1.y + 70 };
  const C1H3 = { x: C1.x - 30,  y: C1.y - 140 };

  // C2 has 1 H (it's the =CH-)
  const C2H  = { x: C2.x,        y: C2.y + 140 };

  // C3 has 2 H's (=CH₂ terminal)
  const C3H1 = { x: C3.x + 80,   y: C3.y - 110 };
  const C3H2 = { x: C3.x + 80,   y: C3.y + 110 };

  // HBr — sits above the alkene before reacting
  const HBR_H = { x: CX + 60, y: 380 };
  const HBR_BR = { x: CX + 130, y: 320 };

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      {/* ── Title ────────────────────────────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 30, left: 0, right: 0, textAlign: 'center',
      }}>
        <h1 style={{
          fontSize: 58, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleScale})`,
        }}>
          Markovnikov's Rule — HBr + Propene
        </h1>
        <p style={{
          fontSize: 24, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp * subFadeOut,
        }}>
          Which carbon does the H choose? The one that already has the most.
        </p>
      </div>

      {/* ── PHASE 1: propene + HBr approach ──────────────────────────────── */}
      {phase1Op > 0.01 && (
        <svg width={STAGE_W} height={STAGE_H}
          style={{ position: 'absolute', inset: 0, opacity: phase1Op }}>

          {/* π-bond halo above + below C=C — pulses when highlight is on */}
          {piHighlight > 0.01 && (
            <g opacity={piHighlight * piPulse}>
              <ellipse cx={(C2.x + C3.x) / 2} cy={C2.y - 22}
                rx={140} ry={22}
                fill={PAI_THEME.colors.accentLight} opacity={0.35} />
              <ellipse cx={(C2.x + C3.x) / 2} cy={C2.y + 22}
                rx={140} ry={22}
                fill={PAI_THEME.colors.accentLight} opacity={0.35} />
              <text x={(C2.x + C3.x) / 2} y={C2.y - 80}
                fontSize={26} fontWeight={700} textAnchor="middle"
                fill={PAI_THEME.colors.accentLight}>
                π electron pair
              </text>
            </g>
          )}

          {/* C1-C2 single bond */}
          <SingleBond x1={C1.x} y1={C1.y} x2={C2.x} y2={C2.y} />
          {/* C2=C3 double bond — the alkene */}
          <DoubleBond x1={C2.x} y1={C2.y} x2={C3.x} y2={C3.y}
            color={piHighlight > 0.5 ? PAI_THEME.colors.fgHighlight : PAI_THEME.colors.bond} />
          {/* C1 hydrogens */}
          <SingleBond x1={C1.x} y1={C1.y} x2={C1H1.x} y2={C1H1.y} />
          <SingleBond x1={C1.x} y1={C1.y} x2={C1H2.x} y2={C1H2.y} />
          <SingleBond x1={C1.x} y1={C1.y} x2={C1H3.x} y2={C1H3.y} />
          {/* C2 hydrogen */}
          <SingleBond x1={C2.x} y1={C2.y} x2={C2H.x}  y2={C2H.y}  />
          {/* C3 hydrogens */}
          <SingleBond x1={C3.x} y1={C3.y} x2={C3H1.x} y2={C3H1.y} />
          <SingleBond x1={C3.x} y1={C3.y} x2={C3H2.x} y2={C3H2.y} />

          {/* Carbons */}
          <Atom x={C1.x} y={C1.y} el="C" />
          <Atom x={C2.x} y={C2.y} el="C" />
          <Atom x={C3.x} y={C3.y} el="C" />
          {/* Hydrogens */}
          <Atom x={C1H1.x} y={C1H1.y} el="H" />
          <Atom x={C1H2.x} y={C1H2.y} el="H" />
          <Atom x={C1H3.x} y={C1H3.y} el="H" />
          <Atom x={C2H.x}  y={C2H.y}  el="H" />
          <Atom x={C3H1.x} y={C3H1.y} el="H" />
          <Atom x={C3H2.x} y={C3H2.y} el="H" />

          {/* Propene label */}
          <text x={C1.x - 200} y={CY + 260}
            fontSize={30} fontWeight={700}
            fill={PAI_THEME.colors.text} textAnchor="start">
            propene · CH₃-CH=CH₂
          </text>

          {/* HBr reagent — fade in + glide downward toward the alkene */}
          <g opacity={hbrIn} transform={`translate(0 ${hbrY - 380})`}>
            <SingleBond x1={HBR_H.x} y1={HBR_H.y} x2={HBR_BR.x} y2={HBR_BR.y} />
            <Atom x={HBR_H.x}  y={HBR_H.y}  el="H" r={SMALL_R} />
            <Atom x={HBR_BR.x} y={HBR_BR.y} el="Br" />
            <text x={HBR_BR.x + 80} y={HBR_BR.y + 10}
              fontSize={28} fontWeight={700}
              fill={PAI_THEME.colors.text} textAnchor="start">
              H-Br · electrophile
            </text>
          </g>

          {/* Caption */}
          <text x={STAGE_W / 2} y={STAGE_H - 60}
            fontSize={28} fontWeight={600} textAnchor="middle"
            fill={PAI_THEME.colors.textMuted}>
            The C=C π bond is electron-rich — it offers its pair to the incoming H⁺.
          </text>
        </svg>
      )}

      {/* ── PHASE 2: carbocation intermediate + rule + rejected alternative ── */}
      {phase2Op > 0.01 && (
        <svg width={STAGE_W} height={STAGE_H}
          style={{ position: 'absolute', inset: 0, opacity: phase2Op }}>

          {/* Section heading */}
          <text x={STAGE_W / 2} y={130}
            fontSize={40} fontWeight={700} textAnchor="middle"
            fill={PAI_THEME.colors.text}>
            Step 2: where does the + charge land?
          </text>

          {/* ── Preferred (secondary) carbocation — left half ───────────── */}
          <g opacity={cationOp}>
            {/* Heading badge */}
            <rect x={120} y={210} width={420} height={50} rx={10}
              fill={PAI_THEME.colors.success} opacity={0.85} />
            <text x={330} y={244} fontSize={24} fontWeight={700} textAnchor="middle"
              fill={PAI_THEME.colors.text}>
              preferred — secondary (2°) cation
            </text>

            {/* Geometry: CH₃ - C⁺(H) - CH₃  → H added to terminal C, + on middle C */}
            {/* Carbons */}
            {(() => {
              const aX = 220, mX = 380, bX = 540, yy = 460;
              return (
                <>
                  {/* bonds */}
                  <SingleBond x1={aX} y1={yy} x2={mX} y2={yy} />
                  <SingleBond x1={mX} y1={yy} x2={bX} y2={yy} />
                  {/* CH3 (left) hydrogens — abbreviated */}
                  <SingleBond x1={aX} y1={yy} x2={aX - 80} y2={yy - 60} />
                  <SingleBond x1={aX} y1={yy} x2={aX - 80} y2={yy + 60} />
                  <SingleBond x1={aX} y1={yy} x2={aX - 30} y2={yy + 100} />
                  {/* middle C: one H below */}
                  <SingleBond x1={mX} y1={yy} x2={mX}       y2={yy + 100} />
                  {/* CH3 (right) hydrogens — now CH₃ because new H added here */}
                  <SingleBond x1={bX} y1={yy} x2={bX + 80}  y2={yy - 60} />
                  <SingleBond x1={bX} y1={yy} x2={bX + 80}  y2={yy + 60} />
                  <SingleBond x1={bX} y1={yy} x2={bX + 30}  y2={yy + 100} />

                  <Atom x={aX} y={yy} el="C" />
                  <Atom x={mX} y={yy} el="C" />
                  <Atom x={bX} y={yy} el="C" />

                  <Atom x={aX - 80} y={yy - 60} el="H" r={SMALL_R} />
                  <Atom x={aX - 80} y={yy + 60} el="H" r={SMALL_R} />
                  <Atom x={aX - 30} y={yy + 100} el="H" r={SMALL_R} />
                  <Atom x={mX}      y={yy + 100} el="H" r={SMALL_R} />
                  <Atom x={bX + 80} y={yy - 60} el="H" r={SMALL_R} />
                  <Atom x={bX + 80} y={yy + 60} el="H" r={SMALL_R} />
                  <Atom x={bX + 30} y={yy + 100} el="H" r={SMALL_R} highlight />

                  {/* + charge on middle C */}
                  <Charge x={mX + 50} y={yy - 50} sign="+" />

                  {/* "new H" arrow on the terminal carbon */}
                  <text x={bX + 30} y={yy + 160}
                    fontSize={20} fontWeight={700} textAnchor="middle"
                    fill={PAI_THEME.colors.fgHighlight}>
                    new H added here
                  </text>

                  {/* stability label */}
                  <text x={mX} y={yy - 100}
                    fontSize={22} fontWeight={700} textAnchor="middle"
                    fill={PAI_THEME.colors.success}>
                    2° — flanked by 2 carbons → stable
                  </text>
                </>
              );
            })()}
          </g>

          {/* ── Rule banner (centre) ───────────────────────────────────── */}
          <g opacity={ruleOp}>
            <rect x={STAGE_W / 2 - 380} y={760} width={760} height={120} rx={16}
              fill={PAI_THEME.colors.backgroundAlt}
              stroke={PAI_THEME.colors.fgHighlight} strokeWidth={3} />
            <text x={STAGE_W / 2} y={802}
              fontSize={26} fontWeight={700} textAnchor="middle"
              fill={PAI_THEME.colors.fgHighlight}>
              Markovnikov's Rule
            </text>
            <text x={STAGE_W / 2} y={838}
              fontSize={22} fontWeight={600} textAnchor="middle"
              fill={PAI_THEME.colors.text}>
              H goes to the carbon with more H's already;
            </text>
            <text x={STAGE_W / 2} y={866}
              fontSize={22} fontWeight={600} textAnchor="middle"
              fill={PAI_THEME.colors.text}>
              X goes to the carbon with fewer H's.
            </text>
          </g>

          {/* ── Rejected (primary) alternative — right half ─────────────── */}
          <g opacity={rejectOp}>
            {/* Heading badge */}
            <rect x={STAGE_W - 540} y={210} width={420} height={50} rx={10}
              fill={PAI_THEME.colors.error} opacity={0.85} />
            <text x={STAGE_W - 330} y={244} fontSize={24} fontWeight={700} textAnchor="middle"
              fill={PAI_THEME.colors.text}>
              rejected — primary (1°) cation
            </text>

            {(() => {
              // Same backbone, but H added to MIDDLE C, + on TERMINAL C.
              const aX = STAGE_W - 640, mX = STAGE_W - 480, bX = STAGE_W - 320, yy = 460;
              const dashed = PAI_THEME.colors.dashedReject;
              return (
                <g opacity={0.55}>
                  {/* bonds — drawn dashed */}
                  <line x1={aX} y1={yy} x2={mX} y2={yy} stroke={dashed} strokeWidth={5} strokeDasharray="10 8" strokeLinecap="round" />
                  <line x1={mX} y1={yy} x2={bX} y2={yy} stroke={dashed} strokeWidth={5} strokeDasharray="10 8" strokeLinecap="round" />
                  {/* CH3 (left) — same */}
                  <line x1={aX} y1={yy} x2={aX - 70} y2={yy - 55} stroke={dashed} strokeWidth={4} strokeDasharray="8 6" />
                  <line x1={aX} y1={yy} x2={aX - 70} y2={yy + 55} stroke={dashed} strokeWidth={4} strokeDasharray="8 6" />
                  <line x1={aX} y1={yy} x2={aX - 30} y2={yy + 90} stroke={dashed} strokeWidth={4} strokeDasharray="8 6" />
                  {/* middle C: now has 2 H's (one original + one new) */}
                  <line x1={mX} y1={yy} x2={mX - 40} y2={yy + 95} stroke={dashed} strokeWidth={4} strokeDasharray="8 6" />
                  <line x1={mX} y1={yy} x2={mX + 40} y2={yy + 95} stroke={dashed} strokeWidth={4} strokeDasharray="8 6" />
                  {/* terminal C: now =CH₂ → after H lost to middle stays as 2 H's, +charge */}
                  <line x1={bX} y1={yy} x2={bX + 70} y2={yy - 55} stroke={dashed} strokeWidth={4} strokeDasharray="8 6" />
                  <line x1={bX} y1={yy} x2={bX + 70} y2={yy + 55} stroke={dashed} strokeWidth={4} strokeDasharray="8 6" />

                  {/* Atoms — drawn muted */}
                  <Atom x={aX} y={yy} el="C" opacity={0.65} />
                  <Atom x={mX} y={yy} el="C" opacity={0.65} />
                  <Atom x={bX} y={yy} el="C" opacity={0.65} />
                  <Atom x={aX - 70} y={yy - 55} el="H" r={SMALL_R} opacity={0.55} />
                  <Atom x={aX - 70} y={yy + 55} el="H" r={SMALL_R} opacity={0.55} />
                  <Atom x={aX - 30} y={yy + 90} el="H" r={SMALL_R} opacity={0.55} />
                  <Atom x={mX - 40} y={yy + 95} el="H" r={SMALL_R} opacity={0.55} highlight />
                  <Atom x={mX + 40} y={yy + 95} el="H" r={SMALL_R} opacity={0.55} />
                  <Atom x={bX + 70} y={yy - 55} el="H" r={SMALL_R} opacity={0.55} />
                  <Atom x={bX + 70} y={yy + 55} el="H" r={SMALL_R} opacity={0.55} />

                  {/* + on terminal C */}
                  <Charge x={bX + 50} y={yy - 50} sign="+" opacity={0.75} />

                  {/* "would-have-been" label */}
                  <text x={mX - 40} y={yy + 155}
                    fontSize={20} fontWeight={700} textAnchor="middle"
                    fill={PAI_THEME.colors.fgHighlight}>
                    H goes to internal C (wrong)
                  </text>

                  {/* Stability label */}
                  <text x={mX} y={yy - 100}
                    fontSize={22} fontWeight={700} textAnchor="middle"
                    fill={PAI_THEME.colors.error}>
                    1° — flanked by only 1 carbon → unstable
                  </text>

                  {/* Big red ✕ over the whole thing */}
                  <line x1={aX - 90} y1={yy - 130} x2={bX + 90} y2={yy + 180}
                    stroke={PAI_THEME.colors.error} strokeWidth={6} opacity={0.7} strokeLinecap="round" />
                  <line x1={aX - 90} y1={yy + 180} x2={bX + 90} y2={yy - 130}
                    stroke={PAI_THEME.colors.error} strokeWidth={6} opacity={0.7} strokeLinecap="round" />
                </g>
              );
            })()}
          </g>

          {/* Lower-third caption */}
          <text x={STAGE_W / 2} y={STAGE_H - 40}
            fontSize={22} fontWeight={500} textAnchor="middle"
            fill={PAI_THEME.colors.textMuted}>
            The more-substituted carbocation is more stable — that's the pathway nature picks.
          </text>
        </svg>
      )}

      {/* ── PHASE 3: Br⁻ attack + final 2-bromopropane ─────────────────── */}
      {phase3In > 0.01 && (
        <svg width={STAGE_W} height={STAGE_H}
          style={{ position: 'absolute', inset: 0, opacity: phase3In }}>

          {/* Section heading */}
          <text x={STAGE_W / 2} y={130}
            fontSize={40} fontWeight={700} textAnchor="middle"
            fill={PAI_THEME.colors.text}>
            Step 3: Br⁻ grabs the positive carbon
          </text>

          {/* Carbocation (fades out as Br⁻ docks) overlaid on product backbone */}
          {/* Use a single shared backbone with reposition based on cationFadeOut. */}

          {(() => {
            const aX = CX - 300, mX = CX, bX = CX + 300, yy = CY;

            // Hydrogen positions per carbon
            // C_a (CH₃ — left): 3 H
            const aH1 = { x: aX - 120, y: yy - 90 };
            const aH2 = { x: aX - 120, y: yy + 90 };
            const aH3 = { x: aX - 40,  y: yy + 140 };

            // C_m (middle): 1 H (CHBr)
            const mH  = { x: mX - 30,  y: yy + 140 };

            // C_b (CH₃ — right): 3 H
            const bH1 = { x: bX + 120, y: yy - 90 };
            const bH2 = { x: bX + 120, y: yy + 90 };
            const bH3 = { x: bX + 40,  y: yy + 140 };

            // Br on middle C — comes in from right, docks above
            const brTarget = { x: mX, y: yy - 160 };

            return (
              <>
                {/* === Carbocation (fading) === */}
                <g opacity={cationFadeOut}>
                  <SingleBond x1={aX} y1={yy} x2={mX} y2={yy} />
                  <SingleBond x1={mX} y1={yy} x2={bX} y2={yy} />
                  <SingleBond x1={aX} y1={yy} x2={aH1.x} y2={aH1.y} />
                  <SingleBond x1={aX} y1={yy} x2={aH2.x} y2={aH2.y} />
                  <SingleBond x1={aX} y1={yy} x2={aH3.x} y2={aH3.y} />
                  <SingleBond x1={mX} y1={yy} x2={mH.x}  y2={mH.y}  />
                  <SingleBond x1={bX} y1={yy} x2={bH1.x} y2={bH1.y} />
                  <SingleBond x1={bX} y1={yy} x2={bH2.x} y2={bH2.y} />
                  <SingleBond x1={bX} y1={yy} x2={bH3.x} y2={bH3.y} />

                  <Atom x={aX} y={yy} el="C" />
                  <Atom x={mX} y={yy} el="C" />
                  <Atom x={bX} y={yy} el="C" />

                  <Atom x={aH1.x} y={aH1.y} el="H" r={SMALL_R} />
                  <Atom x={aH2.x} y={aH2.y} el="H" r={SMALL_R} />
                  <Atom x={aH3.x} y={aH3.y} el="H" r={SMALL_R} />
                  <Atom x={mH.x}  y={mH.y}  el="H" r={SMALL_R} />
                  <Atom x={bH1.x} y={bH1.y} el="H" r={SMALL_R} />
                  <Atom x={bH2.x} y={bH2.y} el="H" r={SMALL_R} />
                  <Atom x={bH3.x} y={bH3.y} el="H" r={SMALL_R} />

                  {/* +charge on middle */}
                  <Charge x={mX + 50} y={yy - 50} sign="+" />
                </g>

                {/* === Br⁻ approaching === */}
                <g opacity={brOp * cationFadeOut}>
                  <Atom x={brX} y={yy - 160} el="Br" />
                  <Charge x={brX + 38} y={yy - 200} sign="-" />
                  {/* Curly arrow from Br⁻ toward C+ */}
                  <path
                    d={`M ${brX - 30} ${yy - 140} Q ${(brX + mX) / 2} ${yy - 240} ${mX + 30} ${yy - 30}`}
                    stroke={PAI_THEME.colors.arrow} strokeWidth={4} fill="none"
                    strokeLinecap="round" markerEnd="url(#arrowhead)" />
                  <defs>
                    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
                      <polygon points="0 0, 10 3, 0 6" fill={PAI_THEME.colors.arrow} />
                    </marker>
                  </defs>
                </g>

                {/* === Final product 2-bromopropane === */}
                <g opacity={productOp}>
                  <SingleBond x1={aX} y1={yy} x2={mX} y2={yy} />
                  <SingleBond x1={mX} y1={yy} x2={bX} y2={yy} />
                  <SingleBond x1={mX} y1={yy} x2={brTarget.x} y2={brTarget.y} />
                  <SingleBond x1={aX} y1={yy} x2={aH1.x} y2={aH1.y} />
                  <SingleBond x1={aX} y1={yy} x2={aH2.x} y2={aH2.y} />
                  <SingleBond x1={aX} y1={yy} x2={aH3.x} y2={aH3.y} />
                  <SingleBond x1={mX} y1={yy} x2={mH.x}  y2={mH.y}  />
                  <SingleBond x1={bX} y1={yy} x2={bH1.x} y2={bH1.y} />
                  <SingleBond x1={bX} y1={yy} x2={bH2.x} y2={bH2.y} />
                  <SingleBond x1={bX} y1={yy} x2={bH3.x} y2={bH3.y} />

                  <Atom x={aX} y={yy} el="C" />
                  <Atom x={mX} y={yy} el="C" highlight />
                  <Atom x={bX} y={yy} el="C" />
                  <Atom x={brTarget.x} y={brTarget.y} el="Br" highlight />

                  <Atom x={aH1.x} y={aH1.y} el="H" r={SMALL_R} />
                  <Atom x={aH2.x} y={aH2.y} el="H" r={SMALL_R} />
                  <Atom x={aH3.x} y={aH3.y} el="H" r={SMALL_R} />
                  <Atom x={mH.x}  y={mH.y}  el="H" r={SMALL_R} />
                  <Atom x={bH1.x} y={bH1.y} el="H" r={SMALL_R} />
                  <Atom x={bH2.x} y={bH2.y} el="H" r={SMALL_R} />
                  <Atom x={bH3.x} y={bH3.y} el="H" r={SMALL_R} />

                  {/* Product label */}
                  <text x={STAGE_W / 2} y={yy + 240}
                    fontSize={36} fontWeight={700} textAnchor="middle"
                    fill={PAI_THEME.colors.fgHighlight}>
                    2-bromopropane · CH₃-CHBr-CH₃
                  </text>
                  <text x={STAGE_W / 2} y={yy + 280}
                    fontSize={22} fontWeight={500} textAnchor="middle"
                    fill={PAI_THEME.colors.textMuted}>
                    Br on the middle (2°) carbon — NOT the terminal one. That's Markovnikov.
                  </text>
                </g>
              </>
            );
          })()}

          {/* Closing caption banner */}
          <g opacity={finalCapOp}>
            <rect x={STAGE_W / 2 - 460} y={STAGE_H - 130} width={920} height={90} rx={16}
              fill={PAI_THEME.colors.backgroundAlt}
              stroke={PAI_THEME.colors.fgHighlight} strokeWidth={3} />
            <text x={STAGE_W / 2} y={STAGE_H - 85}
              fontSize={28} fontWeight={700} textAnchor="middle"
              fill={PAI_THEME.colors.text}>
              Markovnikov:  Markov-knee → the rich (in H) get richer.
            </text>
            <text x={STAGE_W / 2} y={STAGE_H - 55}
              fontSize={20} fontWeight={500} textAnchor="middle"
              fill={PAI_THEME.colors.textMuted}>
              Pathway picks the more-stable (more-substituted) carbocation.
            </text>
          </g>
        </svg>
      )}
    </AbsoluteFill>
  );
};
