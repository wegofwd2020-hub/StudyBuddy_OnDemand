import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { CurrentFlowScene } from './scenes/CurrentFlowScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="electronics-current-flow"
      component={CurrentFlowScene}
      durationInFrames={30 * 24}
      fps={FPS}
      width={W}
      height={H}
      schema={schema}
      defaultProps={{}}
    />
  );
};
