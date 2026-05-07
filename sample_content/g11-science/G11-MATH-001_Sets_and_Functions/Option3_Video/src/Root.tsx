import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { Video } from './Video';

const schema = z.object({});

// Scene durations in frames at 30 fps. Total = sum below.
export const SCENE = {
  title: 150,            //  5s
  venn: 600,             // 20s — 4 ops × 5s each
  vlt: 300,              // 10s
  arrow: 450,            // 15s — 3 categories × 5s each
  composition: 450,      // 15s
  inverse: 360,          // 12s
  transformations: 600,  // 20s — 4 steps × 5s each
  projectile: 450,       // 15s
  closing: 150,          //  5s
} as const;

export const TOTAL_DURATION = Object.values(SCENE).reduce((a, b) => a + b, 0);
// 3510 frames at 30 fps = 117 s ≈ 1m 57s

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="sets-and-functions"
      component={Video}
      durationInFrames={TOTAL_DURATION}
      fps={30}
      width={1920}
      height={1080}
      schema={schema}
      defaultProps={{}}
    />
  );
};
