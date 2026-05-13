import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { PhotosynthesisFlowScene } from './scenes/PhotosynthesisFlowScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="plant-physiol-photosynthesis-flow"
        component={PhotosynthesisFlowScene}
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
