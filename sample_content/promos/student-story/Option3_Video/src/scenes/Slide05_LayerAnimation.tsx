import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { InsetVideoFrame } from "../components/InsetVideoFrame";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 5 — Layer 3: ANIMATION
 *
 * Visual: the inset video frame appears, with two motion strips
 * playing inside (uniform vs accelerated). This is the "yes — there
 * are videos in the lesson" beat.
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
              isActive ? PAI_THEME.colors.accentLight : PAI_THEME.colors.textDark
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

export const Slide05_LayerAnimation: React.FC = () => {
  const frame = useCurrentFrame();
  const dotProgress = interpolate(frame, [60, 360], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={5}
      totalSlides={12}
      audioFile="slide-05.mp3"
      caption="Layer three — ANIMATION. For motion topics, an embedded clip plays right inside the lesson. No tab to chase."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          gap: 50,
          flexDirection: "row",
          padding: "0 80px",
        }}
      >
        <LayerStackIndicator active={2} />

        <InsetVideoFrame appearAt={20} width={950} height={550}>
          <div
            style={{
              width: "100%",
              height: "100%",
              backgroundColor: PAI_THEME.colors.background,
              padding: "30px 50px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-around",
              gap: 20,
            }}
          >
            <div>
              <p
                style={{
                  margin: "0 0 12px 0",
                  color: PAI_THEME.colors.success,
                  fontSize: 20,
                  fontWeight: 700,
                  fontFamily: PAI_THEME.typography.fontFamily,
                }}
              >
                Uniform — equal gaps every second
              </p>
              <svg width="100%" height="68">
                <line
                  x1="20"
                  y1="34"
                  x2="800"
                  y2="34"
                  stroke={PAI_THEME.colors.textMuted}
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                {[0, 1, 2, 3, 4, 5, 6].map((i) => {
                  const baseX = 30 + i * 130;
                  const offset = dotProgress * 26;
                  return (
                    <circle
                      key={i}
                      cx={baseX + offset}
                      cy={34}
                      r={10}
                      fill={PAI_THEME.colors.success}
                    />
                  );
                })}
              </svg>
            </div>
            <div>
              <p
                style={{
                  margin: "0 0 12px 0",
                  color: PAI_THEME.colors.error,
                  fontSize: 20,
                  fontWeight: 700,
                  fontFamily: PAI_THEME.typography.fontFamily,
                }}
              >
                Accelerated — gaps grow each second
              </p>
              <svg width="100%" height="68">
                <line
                  x1="20"
                  y1="34"
                  x2="800"
                  y2="34"
                  stroke={PAI_THEME.colors.textMuted}
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                {[0, 1, 2, 3, 4, 5, 6].map((i) => {
                  const baseX = 30 + i * i * 22;
                  const offset = dotProgress * 26;
                  return (
                    <circle
                      key={i}
                      cx={baseX + offset}
                      cy={34}
                      r={10}
                      fill={PAI_THEME.colors.error}
                    />
                  );
                })}
              </svg>
            </div>
          </div>
        </InsetVideoFrame>
      </AbsoluteFill>
    </SceneFrame>
  );
};
