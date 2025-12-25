'use client';

import { Segmented } from 'antd';
import { memo, useState } from 'react';
import { Flexbox } from 'react-layout-kit';

import CodeEditor from './CodeEditor';
import ConnectionStatus from './ConnectionStatus';
import ProgressTimeline from './ProgressTimeline';
import Terminal from './Terminal';
import { useOpenHandsConnection } from './useOpenHandsConnection';

export type PreviewTab = 'editor' | 'terminal' | 'progress';

const PreviewPanel = memo(() => {
  const [activeTab, setActiveTab] = useState<PreviewTab>('terminal');
  const {
    isConnected,
    connectionError,
    events,
    currentFile,
    terminalOutput,
    connect,
    disconnect,
  } = useOpenHandsConnection();

  return (
    <Flexbox flex={1} height={'100%'} style={{ overflow: 'hidden' }}>
      {/* Connection Status Bar */}
      <ConnectionStatus
        error={connectionError}
        isConnected={isConnected}
        onConnect={connect}
        onDisconnect={disconnect}
      />

      {/* Tab Selector */}
      <Flexbox padding={8} style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <Segmented
          block
          onChange={(value) => setActiveTab(value as PreviewTab)}
          options={[
            { label: 'Terminal', value: 'terminal' },
            { label: 'Editor', value: 'editor' },
            { label: 'Progress', value: 'progress' },
          ]}
          value={activeTab}
        />
      </Flexbox>

      {/* Content Area */}
      <Flexbox flex={1} style={{ overflow: 'hidden' }}>
        {activeTab === 'terminal' && <Terminal output={terminalOutput} />}
        {activeTab === 'editor' && <CodeEditor file={currentFile} />}
        {activeTab === 'progress' && <ProgressTimeline events={events} />}
      </Flexbox>
    </Flexbox>
  );
});

export default PreviewPanel;
