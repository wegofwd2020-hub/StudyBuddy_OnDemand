import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { TypeInText } from "../components/TypeInText";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 2 — "Linda asks for a lesson"
 *
 * Visual: stylised card representing Linda's voice prompt entering the
 * system. The query types in over a glowing input panel, simulating the
 * scoping query being authored. The persona avatar (initials) sits to
 * the left.
 */
export const Slide02_LindaAsks: React.FC = () => {
  const frame = useCurrentFrame();
  const cardFade = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={2}
      totalSlides={12}
      audioFile="slide-02.wav"
      caption="Linda teaches Grade 11 Science. She wants Newton's laws — for her class, anchored to this week's news."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          gap: 60,
          flexDirection: "column",
        }}
      >
        {/* Persona avatar + name */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 24,
            opacity: cardFade,
          }}
        >
          <div
            style={{
              width: 92,
              height: 92,
              borderRadius: "50%",
              backgroundColor: PAI_THEME.colors.accent,
              color: PAI_THEME.colors.text,
              fontSize: 38,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            LR
          </div>
          <div>
            <p
              style={{
                margin: 0,
                color: PAI_THEME.colors.text,
                fontSize: 36,
                fontWeight: 600,
                fontFamily: PAI_THEME.typography.fontFamily,
              }}
            >
              Linda Ronstad
            </p>
            <p
              style={{
                margin: 0,
                color: PAI_THEME.colors.textMuted,
                fontSize: 22,
                fontFamily: PAI_THEME.typography.fontFamily,
              }}
            >
              G11/G12 Science · MilfordWaterford
            </p>
          </div>
        </div>

        {/* Query input panel */}
        <div
          style={{
            width: 1200,
            padding: 40,
            backgroundColor: PAI_THEME.colors.backgroundAlt,
            borderRadius: 16,
            border: `2px solid ${PAI_THEME.colors.accentLight}`,
            boxShadow: `0 0 60px ${PAI_THEME.colors.accent}55`,
            opacity: cardFade,
          }}
        >
          <p
            style={{
              margin: "0 0 18px 0",
              color: PAI_THEME.colors.textMuted,
              fontSize: 20,
              fontFamily: PAI_THEME.typography.fontFamilyMono,
              letterSpacing: 1,
              textTransform: "uppercase",
            }}
          >
            ▸ Lesson request
          </p>
          <div
            style={{
              color: PAI_THEME.colors.text,
              fontSize: 36,
              lineHeight: 1.4,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            <TypeInText
              text={`"Newton's laws of motion, Grade 11 Science, with a real-world example from this week."`}
              cps={24}
              startAt={60}
            />
          </div>
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
