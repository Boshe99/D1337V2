'use client';

import { memo } from 'react';
import { Flexbox } from 'react-layout-kit';

import PreviewPanel from './PreviewPanel';

const D1337AgentBody = memo(() => {
  return (
    <Flexbox
      className={'portal-d1337-agent'}
      flex={1}
      height={'100%'}
      style={{ overflow: 'hidden' }}
    >
      <PreviewPanel />
    </Flexbox>
  );
});

export default D1337AgentBody;
