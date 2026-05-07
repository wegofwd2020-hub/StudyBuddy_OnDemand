import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

export const ClosingScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOpacity = interpolate(frame, [30, 60], [0, 1], { extrapolateRight: 'clamp' });
  const pathOpacity = interpolate(frame, [60, 90], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.backgroundAlt} 0%, ${PAI_THEME.colors.background} 100%)`,
      justifyContent: 'center', alignItems: 'center', flexDirection: 'column',
    }}>
      <h1 style={{
        ...PAI_THEME.typography.title, fontSize: 90,
        color: PAI_THEME.colors.text,
        opacity: titleOpacity, transform: `scale(${titleScale})`,
        margin: 0, textAlign: 'center',
      }}>
        Sets and Functions
      </h1>
      <div style={{
        color: PAI_THEME.colors.accentLight, fontSize: 32,
        opacity: subOpacity, marginTop: 20,
      }}>
        full chapter — lesson, tutorial, quizzes
      </div>
      <div style={{
        marginTop: 56, padding: '14px 26px', borderRadius: 8,
        background: PAI_THEME.colors.background,
        border: `1px solid ${PAI_THEME.colors.accent}`,
        fontFamily: PAI_THEME.typography.fontFamilyMono, fontSize: 22,
        color: PAI_THEME.colors.textMuted, opacity: pathOpacity,
      }}>
        sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Sets_and_Functions.md
      </div>
    </AbsoluteFill>
  );
};
