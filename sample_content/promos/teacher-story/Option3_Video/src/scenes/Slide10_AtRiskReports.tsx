import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { CursorTrace } from "../components/CursorTrace";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 10 — "At-risk students surface automatically"
 *
 * Visual: the /school/reports/at-risk page renders. Three student
 * names appear with red/amber badges. The cursor moves to expand one
 * row, revealing pass-rate trend and attempt history.
 */
export const Slide10_AtRiskReports: React.FC = () => {
  const frame = useCurrentFrame();

  const students = [
    { name: "Fatima Al-Hassan", trend: "−18%", level: "high", color: PAI_THEME.colors.error },
    { name: "Liam O'Brien", trend: "−9%", level: "med", color: PAI_THEME.colors.warning },
    { name: "Carlos Mendez", trend: "−7%", level: "med", color: PAI_THEME.colors.warning },
  ];

  return (
    <SceneFrame
      slideNumber={10}
      totalSlides={12}
      audioFile="slide-10.mp3"
      caption="Students whose first-attempt pass rate slips get flagged on the reports page. No spreadsheet, no guessing."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 30,
        }}
      >
        <h2
          style={{
            margin: 0,
            color: PAI_THEME.colors.text,
            fontSize: 44,
            fontWeight: 700,
            fontFamily: PAI_THEME.typography.fontFamily,
            opacity: interpolate(frame, [0, 24], [0, 1], {
              extrapolateRight: "clamp",
            }),
          }}
        >
          At-risk students — flagged automatically
        </h2>

        <div
          style={{
            width: 1100,
            padding: 32,
            backgroundColor: PAI_THEME.colors.paperGround,
            borderRadius: 12,
            display: "flex",
            flexDirection: "column",
            gap: 14,
          }}
        >
          {students.map((s, i) => {
            const start = 30 + i * 30;
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "18px 24px",
                  backgroundColor: PAI_THEME.colors.text,
                  borderRadius: 8,
                  borderLeft: `6px solid ${s.color}`,
                  opacity: interpolate(frame, [start, start + 24], [0, 1], {
                    extrapolateRight: "clamp",
                  }),
                }}
              >
                <span
                  style={{
                    color: PAI_THEME.colors.background,
                    fontSize: 26,
                    fontFamily: PAI_THEME.typography.fontFamily,
                    fontWeight: 600,
                  }}
                >
                  {s.name}
                </span>
                <span
                  style={{
                    color: s.color,
                    fontSize: 24,
                    fontWeight: 700,
                    fontFamily: PAI_THEME.typography.fontFamilyMono,
                  }}
                >
                  pass rate {s.trend}
                </span>
              </div>
            );
          })}
        </div>

        {/* Cursor moves to first student row, clicks to expand */}
        <CursorTrace
          path={[
            { x: 1700, y: 200, atFrame: 200 },
            { x: 760, y: 470, atFrame: 280 },
            { x: 760, y: 470, atFrame: 320 },
          ]}
          clickAt={310}
        />
      </AbsoluteFill>
    </SceneFrame>
  );
};
