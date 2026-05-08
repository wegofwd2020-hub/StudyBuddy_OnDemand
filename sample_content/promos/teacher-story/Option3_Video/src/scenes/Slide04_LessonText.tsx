import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { TypeInText } from "../components/TypeInText";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 4 — "The lesson assembles — text first"
 *
 * Visual: a lesson page renders inside a "browser" chrome. Overview
 * heading → three learning objectives → first paragraph of Key Concepts.
 * Each block types in sequentially, simulating real-time generation.
 */
export const Slide04_LessonText: React.FC = () => {
  const frame = useCurrentFrame();
  const chromeOpacity = interpolate(frame, [0, 24], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={4}
      totalSlides={12}
      audioFile="slide-04.wav"
      caption="Text first. Overview. Three learning objectives. Key concepts in plain language."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: 1400,
            backgroundColor: PAI_THEME.colors.paperGround,
            borderRadius: 16,
            padding: 60,
            opacity: chromeOpacity,
            boxShadow: "0 30px 60px rgba(0,0,0,0.4)",
          }}
        >
          {/* H1 */}
          <h1
            style={{
              margin: "0 0 24px 0",
              color: PAI_THEME.colors.background,
              fontSize: 52,
              fontWeight: 700,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            <TypeInText text="Newton's Laws of Motion" cps={28} startAt={30} />
          </h1>

          {/* Overview label */}
          <p
            style={{
              margin: "0 0 12px 0",
              color: PAI_THEME.colors.accent,
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: 1.4,
              textTransform: "uppercase",
              fontFamily: PAI_THEME.typography.fontFamilyMono,
              opacity: interpolate(frame, [60, 90], [0, 1], {
                extrapolateRight: "clamp",
              }),
            }}
          >
            Learning objectives
          </p>

          {/* Three learning objectives, typed in sequentially */}
          <ul
            style={{
              margin: "0 0 32px 0",
              padding: "0 0 0 32px",
              color: PAI_THEME.colors.background,
              fontSize: 30,
              lineHeight: 1.6,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            <li>
              <TypeInText
                text="State Newton's three laws in your own words."
                cps={32}
                startAt={100}
                showCaret={false}
              />
            </li>
            <li>
              <TypeInText
                text="Apply F = ma to a real-world deceleration problem."
                cps={32}
                startAt={170}
                showCaret={false}
              />
            </li>
            <li>
              <TypeInText
                text="Identify action-reaction pairs in everyday scenarios."
                cps={32}
                startAt={240}
                showCaret={false}
              />
            </li>
          </ul>

          {/* Key Concepts label */}
          <p
            style={{
              margin: "0 0 12px 0",
              color: PAI_THEME.colors.accent,
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: 1.4,
              textTransform: "uppercase",
              fontFamily: PAI_THEME.typography.fontFamilyMono,
              opacity: interpolate(frame, [310, 340], [0, 1], {
                extrapolateRight: "clamp",
              }),
            }}
          >
            Key concepts
          </p>

          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.background,
              fontSize: 28,
              lineHeight: 1.6,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            <TypeInText
              text='Force equals mass times acceleration. When a body changes its motion, an unbalanced force is acting on it…'
              cps={36}
              startAt={350}
              showCaret={false}
            />
          </p>
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
