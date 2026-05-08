import React from "react";

/**
 * <DashboardPage> — student dashboard tile-grid view.
 *
 * Stand-in for the curriculum / subjects landing page rendered by the
 * student portal. Six unit tiles in a 3 × 2 grid with status badges
 * (locked / in-progress / done) plus a hero "Continue where you left off"
 * card at the top.
 *
 * The currently-active unit gets a glowing blue ring so the cursor
 * (driven by <CursorTrace>) can land on it convincingly.
 */
const DASH_TOKENS = {
  bgWhite: "#ffffff",
  borderDefault: "#e5e7eb",
  textGray900: "#111827",
  textGray700: "#374151",
  textGray500: "#6b7280",
  textGray400: "#9ca3af",
  bgGray50: "#f9fafb",

  blue50: "#eff6ff",
  blue100: "#dbeafe",
  blue200: "#bfdbfe",
  blue500: "#3b82f6",
  blue600: "#2563eb",
  blue700: "#1d4ed8",
  blue800: "#1e40af",

  green100: "#dcfce7",
  green600: "#16a34a",
  green800: "#166534",

  amber100: "#fef3c7",
  amber700: "#b45309",
} as const;

export interface UnitTile {
  unitId: string; // e.g. "G11-CHEM-007"
  title: string;
  status: "done" | "active" | "locked";
}

const StatusBadge: React.FC<{ status: UnitTile["status"] }> = ({ status }) => {
  const cfg = {
    done: { bg: DASH_TOKENS.green100, fg: DASH_TOKENS.green800, label: "✓ Complete" },
    active: { bg: DASH_TOKENS.blue100, fg: DASH_TOKENS.blue800, label: "▸ Continue" },
    locked: { bg: DASH_TOKENS.amber100, fg: DASH_TOKENS.amber700, label: "🔒 Locked" },
  }[status];
  return (
    <span
      style={{
        backgroundColor: cfg.bg,
        color: cfg.fg,
        padding: "4px 10px",
        fontSize: 11,
        fontWeight: 700,
        borderRadius: 999,
        letterSpacing: 0.5,
      }}
    >
      {cfg.label}
    </span>
  );
};

export const DashboardPage: React.FC<{
  greeting: string; // e.g. "Welcome back, Aditi"
  subjectName: string; // e.g. "Grade 11 — Chemistry"
  unitTiles: UnitTile[];
  highlightActiveRing?: boolean; // pulse glow on the active tile
}> = ({ greeting, subjectName, unitTiles, highlightActiveRing }) => {
  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", flexDirection: "column", gap: 28 }}>
      {/* Greeting + subject row */}
      <div>
        <h1
          style={{
            margin: 0,
            fontSize: 32,
            fontWeight: 700,
            color: DASH_TOKENS.textGray900,
            letterSpacing: -0.5,
          }}
        >
          {greeting}
        </h1>
        <p style={{ margin: "6px 0 0 0", fontSize: 16, color: DASH_TOKENS.textGray500 }}>
          {subjectName}
        </p>
      </div>

      {/* Continue card (hero) */}
      {(() => {
        const active = unitTiles.find((u) => u.status === "active");
        if (!active) return null;
        return (
          <div
            style={{
              background: `linear-gradient(135deg, ${DASH_TOKENS.blue50}, ${DASH_TOKENS.blue100})`,
              border: `1px solid ${DASH_TOKENS.blue200}`,
              borderRadius: 12,
              padding: 24,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
            }}
          >
            <div>
              <p
                style={{
                  margin: "0 0 6px 0",
                  fontSize: 12,
                  fontWeight: 700,
                  color: DASH_TOKENS.blue700,
                  letterSpacing: 1.4,
                  textTransform: "uppercase",
                }}
              >
                Continue where you left off
              </p>
              <h2
                style={{
                  margin: 0,
                  fontSize: 26,
                  fontWeight: 700,
                  color: DASH_TOKENS.blue800,
                }}
              >
                {active.title}
              </h2>
              <p style={{ margin: "4px 0 0 0", fontSize: 13, color: DASH_TOKENS.textGray500 }}>
                {active.unitId}
              </p>
            </div>
            <div
              style={{
                backgroundColor: DASH_TOKENS.blue600,
                color: "#fff",
                padding: "12px 24px",
                borderRadius: 8,
                fontSize: 15,
                fontWeight: 600,
                boxShadow: "0 4px 6px -1px rgba(37, 99, 235, 0.3)",
              }}
            >
              ▸ Open lesson
            </div>
          </div>
        );
      })()}

      {/* Unit tile grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 16,
        }}
      >
        {unitTiles.map((tile, i) => {
          const isActive = tile.status === "active";
          return (
            <div
              key={i}
              style={{
                backgroundColor: DASH_TOKENS.bgWhite,
                border: `${isActive ? 2 : 1}px solid ${
                  isActive ? DASH_TOKENS.blue500 : DASH_TOKENS.borderDefault
                }`,
                borderRadius: 10,
                padding: 18,
                display: "flex",
                flexDirection: "column",
                gap: 10,
                boxShadow: isActive && highlightActiveRing
                  ? `0 0 0 4px ${DASH_TOKENS.blue200}, 0 4px 12px rgba(59,130,246,0.25)`
                  : "0 1px 2px rgba(0,0,0,0.04)",
                opacity: tile.status === "locked" ? 0.6 : 1,
                minHeight: 120,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: DASH_TOKENS.textGray400,
                    letterSpacing: 1,
                    fontFamily: "ui-monospace, SFMono-Regular, monospace",
                  }}
                >
                  {tile.unitId}
                </span>
                <StatusBadge status={tile.status} />
              </div>
              <h3
                style={{
                  margin: 0,
                  fontSize: 16,
                  fontWeight: 600,
                  color: DASH_TOKENS.textGray900,
                  lineHeight: 1.35,
                }}
              >
                {tile.title}
              </h3>
            </div>
          );
        })}
      </div>
    </div>
  );
};
