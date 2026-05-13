import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { NormalDistributionScene } from './scenes/NormalDistributionScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

// 5 phases × 150 frames + 30-frame outro = 780 frames ≈ 26 s @ 30 fps
const TOTAL_FRAMES = 30 * 26;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="stats-normal-distribution"
        component={NormalDistributionScene}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
