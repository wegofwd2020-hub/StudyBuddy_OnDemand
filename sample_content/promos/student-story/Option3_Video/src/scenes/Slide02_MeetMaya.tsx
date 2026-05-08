import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { TypeInText } from "../components/TypeInText";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 2 — Meet the student
 *
 * Visual: persona card on the left (initials avatar, name, grade tag).
 * On the right, a "today's lesson" stub types in showing the unit she's
 * starting tonight: Newton's Laws.
 */
export const Slide02_MeetMaya: React.FC = () => {
  const frame = useCurrentFrame();
  const cardFade = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={2}
      totalSlides={12}
      audioFile="slide-02.wav"
      caption="Meet Maya — Grade 11 Science. Tonight she's working through Newton's laws on her phone."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          gap: 80,
          flexDirection: "row",
        }}
      >
        {/* Persona avatar + name */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 24,
            opacity: cardFade,
          }}
        >
          <div
            style={{
              width: 200,
              height: 200,
              borderRadius: "50%",
              backgroundColor: PAI_THEME.colors.dim2,
              color: PAI_THEME.colors.text,
              fontSize: 86,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: PAI_THEME.typography.fontFamily,
              boxShadow: `0 0 60px ${PAI_THEME.colors.dim2}66`,
            }}
          >
            MR
          </div>
          <div style={{ textAlign: "center" }}>
            <p
              style={{
                margin: 0,
                color: PAI_THEME.colors.text,
                fontSize: 40,
                fontWeight: 700,
                fontFamily: PAI_THEME.typography.fontFamily,
              }}
            >
              Maya R.
            </p>
            <p
              style={{
                margin: "6px 0 0 0",
                color: PAI_THEME.colors.textMuted,
                fontSize: 22,
                fontFamily: PAI_THEME.typography.fontFamily,
              }}
            >
              Grade 11 · Science stream
            </p>
          </div>
        </div>

        {/* Today's lesson stub */}
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
          <h2
            style={{
              margin: "0 0 18px 0",
              color: PAI_THEME.colors.text,
              fontSize: 44,
              fontWeight: 700,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            <TypeInText text="Newton's Laws of Motion" cps={28} startAt={50} />
          </h2>
          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.accentLight,
              fontSize: 22,
              fontFamily: PAI_THEME.typography.fontFamily,
              opacity: interpolate(frame, [180, 210], [0, 1], {
                extrapolateRight: "clamp",
              }),
            }}
          >
            ⚡ Five layers • ~25 min
          </p>
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
