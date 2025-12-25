'use client';

import { Highlighter } from '@lobehub/ui';
import { memo } from 'react';
import { Flexbox } from 'react-layout-kit';

import type { FileState } from './types';

interface CodeEditorProps {
  file: FileState | null;
}

const CodeEditor = memo<CodeEditorProps>(({ file }) => {
  if (!file) {
    return (
      <Flexbox
        align="center"
        flex={1}
        justify="center"
        style={{
          backgroundColor: '#1e1e1e',
          color: '#6a6a6a',
          fontStyle: 'italic',
        }}
      >
        No file selected. File changes will appear here when the agent edits files...
      </Flexbox>
    );
  }

  return (
    <Flexbox flex={1} style={{ overflow: 'hidden' }}>
      {/* File path header */}
      <Flexbox
        horizontal
        padding={8}
        style={{
          backgroundColor: '#252526',
          borderBottom: '1px solid #3c3c3c',
          color: '#cccccc',
          fontSize: 12,
        }}
      >
        <span style={{ color: '#6a6a6a', marginRight: 8 }}>📄</span>
        {file.path}
      </Flexbox>

      {/* Code content */}
      <Flexbox flex={1} style={{ overflow: 'auto' }}>
        <Highlighter
          language={file.language || 'plaintext'}
          style={{
            fontSize: 13,
            height: '100%',
            margin: 0,
            overflow: 'auto',
          }}
        >
          {file.content}
        </Highlighter>
      </Flexbox>
    </Flexbox>
  );
});

export default CodeEditor;
