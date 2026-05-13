import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { BernoulliVenturiScene } from './scenes/BernoulliVenturiScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="bulk-matter-bernoulli-venturi"
        component={BernoulliVenturiScene}
        durationInFrames={30 * 26}     // 26 s
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
