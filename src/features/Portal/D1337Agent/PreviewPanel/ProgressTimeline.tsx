'use client';

import { memo } from 'react';
import { Flexbox } from 'react-layout-kit';

import type { OpenHandsEvent } from './types';

interface ProgressTimelineProps {
  events: OpenHandsEvent[];
}

const getEventIcon = (event: OpenHandsEvent) => {
  if (event.action === 'run') return '⚡';
  if (event.action === 'write' || event.action === 'edit') return '📝';
  if (event.action === 'read') return '📖';
  if (event.action === 'browse') return '🌐';
  if (event.action === 'think') return '💭';
  if (event.type === 'message') return event.source === 'user' ? '👤' : '🤖';
  return '📌';
};

const getEventTitle = (event: OpenHandsEvent) => {
  if (event.action === 'run' && event.args?.command) {
    return `Run: ${event.args.command.slice(0, 50)}${event.args.command.length > 50 ? '...' : ''}`;
  }
  if ((event.action === 'write' || event.action === 'edit') && event.args?.path) {
    return `${event.action === 'write' ? 'Write' : 'Edit'}: ${event.args.path}`;
  }
  if (event.action === 'read' && event.args?.path) {
    return `Read: ${event.args.path}`;
  }
  if (event.action === 'browse' && event.args?.url) {
    return `Browse: ${event.args.url.slice(0, 50)}${event.args.url.length > 50 ? '...' : ''}`;
  }
  if (event.action === 'think' && event.args?.thought) {
    return `Think: ${event.args.thought.slice(0, 50)}${event.args.thought.length > 50 ? '...' : ''}`;
  }
  if (event.message) {
    return event.message.slice(0, 60) + (event.message.length > 60 ? '...' : '');
  }
  return event.type || 'Event';
};

const formatTime = (timestamp: string) => {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  } catch {
    return timestamp;
  }
};

const ProgressTimeline = memo<ProgressTimelineProps>(({ events }) => {
  if (events.length === 0) {
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
        Progress timeline will appear here when connected to OpenHands...
      </Flexbox>
    );
  }

  return (
    <Flexbox
      flex={1}
      gap={4}
      style={{
        backgroundColor: '#1e1e1e',
        overflow: 'auto',
        padding: 12,
      }}
    >
      {events.map((event, index) => (
        <Flexbox
          horizontal
          key={event.id || index}
          style={{
            alignItems: 'flex-start',
            borderLeft: '2px solid #3c3c3c',
            marginLeft: 8,
            paddingBottom: 12,
            paddingLeft: 16,
            position: 'relative',
          }}
        >
          {/* Timeline dot */}
          <div
            style={{
              backgroundColor: event.source === 'agent' ? '#4ec9b0' : '#569cd6',
              borderRadius: '50%',
              height: 10,
              left: -6,
              position: 'absolute',
              top: 4,
              width: 10,
            }}
          />

          <Flexbox flex={1} gap={4}>
            {/* Event header */}
            <Flexbox horizontal justify="space-between" style={{ width: '100%' }}>
              <span style={{ color: '#d4d4d4', fontSize: 13 }}>
                {getEventIcon(event)} {getEventTitle(event)}
              </span>
              <span style={{ color: '#6a6a6a', fontSize: 11 }}>
                {formatTime(event.timestamp)}
              </span>
            </Flexbox>

            {/* Event details */}
            {event.result && (
              <div
                style={{
                  backgroundColor: '#252526',
                  borderRadius: 4,
                  color: '#9cdcfe',
                  fontSize: 12,
                  maxHeight: 100,
                  overflow: 'auto',
                  padding: 8,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {event.result.slice(0, 200)}
                {event.result.length > 200 ? '...' : ''}
              </div>
            )}
          </Flexbox>
        </Flexbox>
      ))}
    </Flexbox>
  );
});

export default ProgressTimeline;
