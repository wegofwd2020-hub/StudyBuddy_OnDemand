import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { PeriodicityTrendsScene } from './scenes/PeriodicityTrendsScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="periodicity-trends-walkthrough"
        component={PeriodicityTrendsScene}
        durationInFrames={30 * 32}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
