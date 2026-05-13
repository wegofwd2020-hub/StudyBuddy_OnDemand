import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { FunctionalGroupsScene } from './scenes/FunctionalGroupsScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="organic-chem-functional-groups"
        component={FunctionalGroupsScene}
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
