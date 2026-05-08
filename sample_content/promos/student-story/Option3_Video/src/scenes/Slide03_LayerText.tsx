import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { TypeInText } from "../components/TypeInText";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 3 — Layer 1: TEXT
 *
 * Visual: a layer-stack indicator on the left ("01 / 05 — TEXT") with
 * the four other layers dimmed below. A lesson-text panel on the right
 * types in: H1, three objectives, and a paragraph of key concepts.
 */
const LAYERS = ["TEXT", "IMAGES", "ANIMATION", "QUIZ", "TUTORIAL"];

const LayerStackIndicator: React.FC<{ active: number }> = ({ active }) => (
  <div
    style={{
      width: 360,
      display: "flex",
      flexDirection: "column",
      gap: 10,
      fontFamily: PAI_THEME.typography.fontFamilyMono,
    }}
  >
    {LAYERS.map((label, i) => {
      const isActive = i === active;
      const isPast = i < active;
      return (
        <div
          key={i}
          style={{
            padding: "16px 22px",
            backgroundColor: isActive
              ? PAI_THEME.colors.accent
              : isPast
              ? PAI_THEME.colors.backgroundAlt
              : "transparent",
            border: `2px solid ${
              isActive
                ? PAI_THEME.colors.accentLight
                : PAI_THEME.colors.textDark
            }`,
            borderRadius: 8,
            color: isActive
              ? PAI_THEME.colors.text
              : isPast
              ? PAI_THEME.colors.textMuted
              : PAI_THEME.colors.textDark,
            fontSize: 22,
            fontWeight: isActive ? 700 : 500,
            display: "flex",
            justifyContent: "space-between",
            opacity: isActive ? 1 : isPast ? 0.7 : 0.4,
          }}
        >
          <span>0{i + 1}</span>
          <span>{label}</span>
        </div>
      );
    })}
  </div>
);

export const Slide03_LayerText: React.FC = () => {
  const frame = useCurrentFrame();
  const panelOpacity = interpolate(frame, [0, 24], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={3}
      totalSlides={12}
      audioFile="slide-03.wav"
      caption="Layer one — TEXT. Plain language, two grades below her own, with the heavy terms defined inline."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          gap: 60,
          flexDirection: "row",
          padding: "0 80px",
        }}
      >
        <LayerStackIndicator active={0} />

        {/* Lesson-text card */}
        <div
          style={{
            flex: 1,
            maxWidth: 1100,
            padding: 50,
            backgroundColor: PAI_THEME.colors.paperGround,
            borderRadius: 16,
            opacity: panelOpacity,
            boxShadow: "0 30px 60px rgba(0,0,0,0.4)",
          }}
        >
          <h1
            style={{
              margin: "0 0 20px 0",
              color: PAI_THEME.colors.background,
              fontSize: 46,
              fontWeight: 700,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            <TypeInText text="Newton's Laws of Motion" cps={28} startAt={30} />
          </h1>
          <p
            style={{
              margin: "0 0 12px 0",
              color: PAI_THEME.colors.accent,
              fontSize: 18,
              fontWeight: 700,
              letterSpacing: 1.4,
              textTransform: "uppercase",
              fontFamily: PAI_THEME.typography.fontFamilyMono,
            }}
          >
            What you'll learn
          </p>
          <ul
            style={{
              margin: "0 0 28px 0",
              padding: "0 0 0 28px",
              color: PAI_THEME.colors.background,
              fontSize: 26,
              lineHeight: 1.7,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            <li>
              <TypeInText
                text="When something speeds up or slows down, a force is acting on it."
                cps={36}
                startAt={90}
                showCaret={false}
              />
            </li>
            <li>
              <TypeInText
                text="The bigger the mass, the harder it is to change its motion."
                cps={36}
                startAt={170}
                showCaret={false}
              />
            </li>
            <li>
              <TypeInText
                text="Every action has an equal and opposite reaction."
                cps={36}
                startAt={250}
                showCaret={false}
              />
            </li>
          </ul>
          <p
            style={{
              margin: 0,
              padding: "16px 20px",
              backgroundColor: `${PAI_THEME.colors.info}22`,
              borderLeft: `5px solid ${PAI_THEME.colors.info}`,
              color: PAI_THEME.colors.background,
              fontSize: 22,
              fontFamily: PAI_THEME.typography.fontFamily,
              opacity: interpolate(frame, [320, 360], [0, 1], {
                extrapolateRight: "clamp",
              }),
            }}
          >
            <strong>"Inertia"</strong> = the tendency of an object to keep
            doing what it's doing. Heavy = lots of inertia.
          </p>
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
