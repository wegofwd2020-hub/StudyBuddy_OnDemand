/**
 * PAI Theme for Remotion + circuit-schematic palette.
 */

export const PAI_THEME = {
  colors: {
    background: '#0f172a',
    backgroundAlt: '#1e293b',
    backgroundDark: '#020617',

    accent: '#8b5cf6',
    accentLight: '#a78bfa',
    accentDark: '#7c3aed',
    accentMuted: '#6366f1',

    text: '#f1f5f9',
    textMuted: '#94a3b8',
    textDark: '#64748b',

    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',

    // Circuit palette — matches Phase-1 SVG catalogue
    wire: '#e2e8f0',           // light wires on dark bg (inverted for video legibility)
    resistor: '#f59e0b',
    batteryPos: '#ef4444',
    batteryNeg: '#cbd5e1',
    led: '#ef4444',
    ledGlow: '#fbbf24',
    lamp: '#fbbf24',
    switchColor: '#94a3b8',
    currentFlow: '#10b981',    // green charge dots
    capacitor: '#3b82f6',
  },

  typography: {
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontFamilyMono: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
  },

  animation: {
    springFast: { damping: 15, stiffness: 150 },
    springDefault: { damping: 12, stiffness: 100 },
    springSlow: { damping: 10, stiffness: 80 },
  },
} as const;

export type PAITheme = typeof PAI_THEME;
