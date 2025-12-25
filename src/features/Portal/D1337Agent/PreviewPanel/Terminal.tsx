'use client';

import { memo, useEffect, useRef } from 'react';
import { Flexbox } from 'react-layout-kit';

import type { TerminalLine } from './types';

interface TerminalProps {
  output: TerminalLine[];
}

const Terminal = memo<TerminalProps>(({ output }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new output arrives
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [output]);

  const getLineColor = (type: TerminalLine['type']) => {
    switch (type) {
      case 'command':
        return '#4ec9b0'; // Cyan for commands
      case 'error':
        return '#f14c4c'; // Red for errors
      case 'output':
      default:
        return '#d4d4d4'; // Light gray for output
    }
  };

  return (
    <Flexbox
      flex={1}
      ref={containerRef}
      style={{
        backgroundColor: '#1e1e1e',
        fontFamily: 'Consolas, Monaco, "Courier New", monospace',
        fontSize: 13,
        lineHeight: 1.5,
        overflow: 'auto',
        padding: 12,
      }}
    >
      {output.length === 0 ? (
        <Flexbox
          align="center"
          flex={1}
          justify="center"
          style={{ color: '#6a6a6a', fontStyle: 'italic' }}
        >
          Terminal output will appear here when connected to OpenHands...
        </Flexbox>
      ) : (
        output.map((line) => (
          <div
            key={line.id}
            style={{
              color: getLineColor(line.type),
              marginBottom: 4,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}
          >
            {line.content}
          </div>
        ))
      )}
    </Flexbox>
  );
});

export default Terminal;
