import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { TypeInText } from "../components/TypeInText";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 2 — meet the persona.
 *
 * Persona card on the left (initials avatar + name + grade tag) +
 * "tonight's lesson" stub on the right. Mirrors the layout of the
 * student-story Maya intro so the series reads consistent.
 */
export const Slide02_MeetAditi: React.FC = () => {
  const frame = useCurrentFrame();
  const cardFade = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });

  return (
    <SceneFrame
      slideNumber={2}
      totalSlides={12}
      audioFile="slide-02.wav"
      caption="Meet Aditi — Grade 11 Science. Tonight she's working through alkenes on her laptop."
    >
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 80, flexDirection: "row" }}>
        {/* Persona avatar + name */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24, opacity: cardFade }}>
          <div
            style={{
              width: 200,
              height: 200,
              borderRadius: "50%",
              backgroundColor: PAI_THEME.colors.dim4,
              color: PAI_THEME.colors.text,
              fontSize: 86,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: PAI_THEME.typography.fontFamily,
              boxShadow: `0 0 60px ${PAI_THEME.colors.dim4}66`,
            }}
          >
            AK
          </div>
          <div style={{ textAlign: "center" }}>
            <p style={{ margin: 0, color: PAI_THEME.colors.text, fontSize: 40, fontWeight: 700, fontFamily: PAI_THEME.typography.fontFamily }}>
              Aditi K.
            </p>
            <p style={{ margin: "6px 0 0 0", color: PAI_THEME.colors.textMuted, fontSize: 22, fontFamily: PAI_THEME.typography.fontFamily }}>
              Grade 11 · Chemistry stream
            </p>
          </div>
        </div>

        {/* Tonight's lesson stub */}
        <div
          style={{
            width: 700,
            padding: 40,
            backgroundColor: PAI_THEME.colors.backgroundAlt,
            borderRadius: 16,
            border: `2px solid ${PAI_THEME.colors.accentLight}`,
            opacity: cardFade,
          }}
        >
          <p
            style={{
              margin: "0 0 18px 0",
              color: PAI_THEME.colors.textMuted,
              fontSize: 18,
              fontFamily: PAI_THEME.typography.fontFamilyMono,
              letterSpacing: 1,
              textTransform: "uppercase",
            }}
          >
            ▸ Tonight's lesson
          </p>
          <h2 style={{ margin: "0 0 18px 0", color: PAI_THEME.colors.text, fontSize: 44, fontWeight: 700, fontFamily: PAI_THEME.typography.fontFamily }}>
            <TypeInText text="Reactions of Alkenes" cps={28} startAt={50} />
          </h2>
          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.accentLight,
              fontSize: 22,
              fontFamily: PAI_THEME.typography.fontFamily,
              opacity: interpolate(frame, [180, 210], [0, 1], { extrapolateRight: "clamp" }),
            }}
          >
            ⚗️ Lesson · Quiz · Tutorial • ~25 min
          </p>
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
