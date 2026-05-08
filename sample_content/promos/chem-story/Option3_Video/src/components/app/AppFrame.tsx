import React from "react";
import { PAI_THEME } from "../../theme";

/**
 * <AppFrame> — pixel-faithful replica of the student-portal chrome.
 *
 * Mirrors the layout produced by `web/components/layout/PortalHeader.tsx`:
 *   - 52 px white header bar with bottom border
 *   - Portal icon (small) at left
 *   - Username + clock at right
 *   - Slate-tinted main content area below
 *
 * The header is rendered statically (no actual hooks). Clock face is
 * frozen at the time the user sees the persona for the slide; this
 * avoids visual flicker over the slide's 16-second window.
 *
 * Children render INSIDE the content area, and should respect a
 * 1920×1010 (1080 − 70 header) usable region with padding.
 */
const STUDENT_TOKENS = {
  // Tailwind tokens used by PortalHeader (faithful subset)
  white: "#ffffff",
  borderGray100: "#f3f4f6",
  textGray400: "#9ca3af",
  textGray600: "#4b5563",
  textGray800: "#1f2937",
  borderGray200: "#e5e7eb",
  blue50: "#eff6ff",
  blue200: "#bfdbfe",
  blue500: "#3b82f6",
  blue600: "#2563eb",
  // Student-portal page background (Tailwind `bg-slate-50`)
  bgPage: "#f8fafc",
} as const;

export const APP_TOKENS = STUDENT_TOKENS;

const HEADER_HEIGHT = 70; // matches min-h-[52px] + py-2 visual height

export const AppFrame: React.FC<{
  userName: string;
  clockTime?: string; // e.g. "9:14 PM"
  children: React.ReactNode;
}> = ({ userName, clockTime = "9:14 PM", children }) => {
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundColor: STUDENT_TOKENS.bgPage,
        fontFamily:
          'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header bar — replicates PortalHeader */}
      <div
        style={{
          height: HEADER_HEIGHT,
          backgroundColor: STUDENT_TOKENS.white,
          borderBottom: `1px solid ${STUDENT_TOKENS.borderGray100}`,
          padding: "0 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          boxShadow: "0 1px 2px rgba(0, 0, 0, 0.04)",
          flexShrink: 0,
        }}
      >
        {/* Left: brand + portal icon */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {/* Stylised "books" glyph standing in for the student-portal icon */}
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: `linear-gradient(135deg, ${PAI_THEME.colors.accent}, ${PAI_THEME.colors.accentLight})`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontSize: 22,
              fontWeight: 800,
            }}
          >
            📚
          </div>
          <span
            style={{
              fontWeight: 700,
              fontSize: 19,
              color: STUDENT_TOKENS.textGray800,
              letterSpacing: -0.3,
            }}
          >
            StudyBuddy
          </span>
        </div>
        {/* Right: dyslexia eye toggle + username + clock */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: 6,
              border: `1px solid ${STUDENT_TOKENS.borderGray200}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: STUDENT_TOKENS.textGray400,
              fontSize: 16,
            }}
          >
            👁
          </div>
          <span
            style={{
              fontSize: 16,
              fontWeight: 600,
              color: STUDENT_TOKENS.textGray800,
            }}
          >
            {userName}
          </span>
          <span
            style={{
              fontSize: 14,
              color: STUDENT_TOKENS.textGray400,
              fontFamily: PAI_THEME.typography.fontFamilyMono,
            }}
          >
            {clockTime}
          </span>
        </div>
      </div>

      {/* Main content area */}
      <div
        style={{
          flex: 1,
          padding: "40px 80px",
          overflow: "hidden",
          position: "relative",
        }}
      >
        {children}
      </div>
    </div>
  );
};
