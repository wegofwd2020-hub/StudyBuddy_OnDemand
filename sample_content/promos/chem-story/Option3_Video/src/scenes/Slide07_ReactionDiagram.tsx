import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PAI_THEME } from "../theme";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 7 — full-canvas reaction diagram.
 *
 * Mid-scene "zoom in" — break out of the AppFrame chrome and show a
 * blackboard-style reaction diagram for the worked HBr + propene
 * example. SVG-rendered structural formulae (skeletal style) with
 * sequential reveal:
 *   1. Propene (CH₃-CH=CH₂)
 *   2. + HBr arrow
 *   3. Two product candidates (1-bromopropane, 2-bromopropane)
 *   4. Markovnikov tick / cross marks the major product
 */
const REACTION_PALETTE = {
  bg: "#ffffff",
  ink: "#111827",
  accent: PAI_THEME.colors.accent,
  green: "#16a34a",
  red: "#dc2626",
  muted: "#94a3b8",
} as const;

const Atom: React.FC<{ x: number; y: number; label: string; color?: string; fontSize?: number }> = ({
  x,
  y,
  label,
  color = REACTION_PALETTE.ink,
  fontSize = 32,
}) => (
  <text
    x={x}
    y={y}
    fontSize={fontSize}
    fontWeight={700}
    fill={color}
    textAnchor="middle"
    dominantBaseline="middle"
    fontFamily={PAI_THEME.typography.fontFamily}
  >
    {label}
  </text>
);

export const Slide07_ReactionDiagram: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgFade = interpolate(frame, [0, 24], [0, 1], { extrapolateRight: "clamp" });
  const propeneOpacity = interpolate(frame, [30, 60], [0, 1], { extrapolateRight: "clamp" });
  const arrowOpacity = interpolate(frame, [120, 150], [0, 1], { extrapolateRight: "clamp" });
  const productsOpacity = interpolate(frame, [180, 240], [0, 1], { extrapolateRight: "clamp" });
  const verdictOpacity = interpolate(frame, [320, 360], [0, 1], { extrapolateRight: "clamp" });
  const scaleSpring = spring({ frame, fps, config: PAI_THEME.animation.springDefault });

  return (
    <SceneFrame
      slideNumber={7}
      totalSlides={12}
      audioFile="slide-07.wav"
      caption="Worked example. Propene plus HBr — two possible products. Markovnikov's rule picks the winner."
    >
      <AbsoluteFill style={{ backgroundColor: REACTION_PALETTE.bg, opacity: bgFade }}>
        <div
          style={{
            transform: `scale(${interpolate(scaleSpring, [0, 1], [0.95, 1])})`,
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 30,
          }}
        >
          <h2
            style={{
              margin: 0,
              fontSize: 36,
              fontWeight: 700,
              color: REACTION_PALETTE.ink,
              fontFamily: PAI_THEME.typography.fontFamily,
              opacity: propeneOpacity,
            }}
          >
            Propene + HBr → ?
          </h2>

          {/* Reactants row */}
          <svg width={1500} height={200}>
            {/* Propene structural formula: CH3—CH=CH2 */}
            <g opacity={propeneOpacity}>
              <Atom x={120} y={100} label="CH₃" />
              <line x1={185} y1={100} x2={290} y2={100} stroke={REACTION_PALETTE.ink} strokeWidth={3} />
              <Atom x={355} y={100} label="CH" />
              {/* Double bond */}
              <line x1={420} y1={92} x2={530} y2={92} stroke={REACTION_PALETTE.ink} strokeWidth={3} />
              <line x1={420} y1={108} x2={530} y2={108} stroke={REACTION_PALETTE.ink} strokeWidth={3} />
              <Atom x={595} y={100} label="CH₂" />
            </g>

            {/* + HBr */}
            <g opacity={arrowOpacity}>
              <Atom x={750} y={100} label="+" fontSize={42} color={REACTION_PALETTE.muted} />
              <Atom x={870} y={100} label="H—Br" fontSize={36} color={REACTION_PALETTE.accent} />
            </g>

            {/* Reaction arrow */}
            <g opacity={arrowOpacity}>
              <line x1={1010} y1={100} x2={1180} y2={100} stroke={REACTION_PALETTE.ink} strokeWidth={3} />
              <polygon points="1180,90 1200,100 1180,110" fill={REACTION_PALETTE.ink} />
              <text x={1095} y={75} fontSize={18} fill={REACTION_PALETTE.muted} textAnchor="middle">
                addition
              </text>
            </g>
          </svg>

          {/* Two product candidates */}
          <div
            style={{
              display: "flex",
              gap: 80,
              opacity: productsOpacity,
              alignItems: "flex-start",
            }}
          >
            {/* Anti-Markovnikov */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
              <p
                style={{
                  margin: 0,
                  fontSize: 18,
                  color: REACTION_PALETTE.muted,
                  fontFamily: PAI_THEME.typography.fontFamilyMono,
                  letterSpacing: 1.2,
                  textTransform: "uppercase",
                }}
              >
                Option A
              </p>
              <div
                style={{
                  border: `2px solid ${
                    verdictOpacity > 0.5 ? REACTION_PALETTE.red : "#cbd5e1"
                  }`,
                  borderRadius: 10,
                  padding: "20px 28px",
                  fontSize: 30,
                  color: REACTION_PALETTE.ink,
                  fontFamily: PAI_THEME.typography.fontFamily,
                  fontWeight: 700,
                  position: "relative",
                  backgroundColor: verdictOpacity > 0.5 ? "#fef2f2" : "#fff",
                }}
              >
                CH₃—CH₂—CH₂—Br
                <p style={{ margin: "6px 0 0 0", fontSize: 16, color: REACTION_PALETTE.muted }}>
                  1-bromopropane
                </p>
                {verdictOpacity > 0.5 && (
                  <span
                    style={{
                      position: "absolute",
                      top: -16,
                      right: -16,
                      fontSize: 36,
                      color: REACTION_PALETTE.red,
                      opacity: verdictOpacity,
                    }}
                  >
                    ✕
                  </span>
                )}
              </div>
            </div>

            {/* Markovnikov */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
              <p
                style={{
                  margin: 0,
                  fontSize: 18,
                  color: REACTION_PALETTE.muted,
                  fontFamily: PAI_THEME.typography.fontFamilyMono,
                  letterSpacing: 1.2,
                  textTransform: "uppercase",
                }}
              >
                Option B
              </p>
              <div
                style={{
                  border: `2px solid ${
                    verdictOpacity > 0.5 ? REACTION_PALETTE.green : "#cbd5e1"
                  }`,
                  borderRadius: 10,
                  padding: "20px 28px",
                  fontSize: 30,
                  color: REACTION_PALETTE.ink,
                  fontFamily: PAI_THEME.typography.fontFamily,
                  fontWeight: 700,
                  position: "relative",
                  backgroundColor: verdictOpacity > 0.5 ? "#f0fdf4" : "#fff",
                }}
              >
                CH₃—CHBr—CH₃
                <p style={{ margin: "6px 0 0 0", fontSize: 16, color: REACTION_PALETTE.muted }}>
                  2-bromopropane
                </p>
                {verdictOpacity > 0.5 && (
                  <span
                    style={{
                      position: "absolute",
                      top: -16,
                      right: -16,
                      fontSize: 36,
                      color: REACTION_PALETTE.green,
                      opacity: verdictOpacity,
                    }}
                  >
                    ✓
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Markovnikov verdict caption */}
          <p
            style={{
              margin: 0,
              fontSize: 22,
              color: REACTION_PALETTE.green,
              fontFamily: PAI_THEME.typography.fontFamily,
              fontWeight: 600,
              opacity: verdictOpacity,
              backgroundColor: "#dcfce7",
              padding: "10px 22px",
              borderRadius: 999,
            }}
          >
            ▸ Markovnikov: H goes to the carbon with more H's already.
          </p>
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
