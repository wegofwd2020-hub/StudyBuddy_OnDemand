export const PAI_THEME = {
  colors: {
    background: '#0f172a',
    backgroundAlt: '#1e293b',
    accent: '#8b5cf6',
    accentLight: '#a78bfa',
    text: '#f1f5f9',
    textMuted: '#94a3b8',
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
    curve: '#3b82f6',
    secant: '#f59e0b',
    tangent: '#10b981',
    point: '#fbbf24',
  },
  typography: {
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontFamilyMono: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
  },
  animation: {
    springDefault: { damping: 12, stiffness: 100 },
  },
} as const;
