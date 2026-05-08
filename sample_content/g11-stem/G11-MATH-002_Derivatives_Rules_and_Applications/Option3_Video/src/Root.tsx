import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { TangentEmergenceScene } from './scenes/TangentEmergenceScene';

const schema = z.object({});

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="derivatives-tangent-emergence"
      component={TangentEmergenceScene}
      durationInFrames={30 * 24}
      fps={30}
      width={1920}
      height={1080}
      schema={schema}
      defaultProps={{}}
    />
  );
};
