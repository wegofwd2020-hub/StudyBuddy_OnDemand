import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { InsetVideoFrame } from "../components/InsetVideoFrame";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 6 — "Then a video"
 *
 * Visual: the lesson page reveals an inset video frame — a chrome-bordered
 * container suggesting an embedded animation playing inside the lesson.
 * For the v2 first-cut we render a stylised motion-strip diagram inside
 * the inset frame as a still representation; production swaps it for the
 * actual G9-Kinematics MotionAlongStrip clip from the visual library.
 */
export const Slide06_LessonVideo: React.FC = () => {
  const frame = useCurrentFrame();

  // Animate two strobe-dot trails inside the inset frame to suggest motion
  const dotProgress = interpolate(frame, [60, 360], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={6}
      totalSlides={12}
      audioFile="slide-06.mp3"
      caption="For motion topics, the lesson embeds a short animation. The animation lives in the lesson — no link to chase."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <InsetVideoFrame appearAt={20} width={1100} height={620}>
          {/* Two motion strips inside the frame */}
          <div
            style={{
              width: "100%",
              height: "100%",
              backgroundColor: PAI_THEME.colors.background,
              padding: "40px 60px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-around",
              gap: 24,
            }}
          >
            {/* Uniform-motion strip — equal-spaced dots */}
            <div>
              <p
                style={{
                  margin: "0 0 14px 0",
                  color: PAI_THEME.colors.success,
                  fontSize: 22,
                  fontWeight: 700,
                  fontFamily: PAI_THEME.typography.fontFamily,
                }}
              >
                Uniform motion (equal gaps every second)
              </p>
              <svg width="100%" height="80">
                <line
                  x1="20"
                  y1="40"
                  x2="950"
                  y2="40"
                  stroke={PAI_THEME.colors.textMuted}
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                {[0, 1, 2, 3, 4, 5, 6].map((i) => {
                  const baseX = 30 + i * 155;
                  const offset = dotProgress * 30;
                  return (
                    <circle
                      key={i}
                      cx={baseX + offset}
                      cy={40}
                      r={11}
                      fill={PAI_THEME.colors.success}
                      stroke={PAI_THEME.colors.text}
                      strokeWidth={1.5}
                    />
                  );
                })}
              </svg>
            </div>
            {/* Accelerated-motion strip — t² spacing */}
            <div>
              <p
                style={{
                  margin: "0 0 14px 0",
                  color: PAI_THEME.colors.error,
                  fontSize: 22,
                  fontWeight: 700,
                  fontFamily: PAI_THEME.typography.fontFamily,
                }}
              >
                Accelerated motion (gaps grow each second)
              </p>
              <svg width="100%" height="80">
                <line
                  x1="20"
                  y1="40"
                  x2="950"
                  y2="40"
                  stroke={PAI_THEME.colors.textMuted}
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                {[0, 1, 2, 3, 4, 5, 6].map((i) => {
                  const baseX = 30 + (i * i * 25);
                  const offset = dotProgress * 30;
                  return (
                    <circle
                      key={i}
                      cx={baseX + offset}
                      cy={40}
                      r={11}
                      fill={PAI_THEME.colors.error}
                      stroke={PAI_THEME.colors.text}
                      strokeWidth={1.5}
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
