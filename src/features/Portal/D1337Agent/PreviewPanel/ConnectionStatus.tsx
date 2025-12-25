'use client';

import { ActionIcon, Input } from '@lobehub/ui';
import { Button, Tooltip } from 'antd';
import { Link2, Link2Off, Settings } from 'lucide-react';
import { memo, useState } from 'react';
import { Flexbox } from 'react-layout-kit';

interface ConnectionStatusProps {
  isConnected: boolean;
  error: string | null;
  onConnect: (config?: { baseUrl?: string; conversationId?: string }) => void;
  onDisconnect: () => void;
}

const ConnectionStatus = memo<ConnectionStatusProps>(
  ({ isConnected, error, onConnect, onDisconnect }) => {
    const [showConfig, setShowConfig] = useState(false);
    const [baseUrl, setBaseUrl] = useState(
      process.env.NEXT_PUBLIC_D1337_AGENT_URL || '/agent'
    );
    const [conversationId, setConversationId] = useState('');

    const handleConnect = () => {
      onConnect({ baseUrl, conversationId });
    };

    return (
      <Flexbox gap={8} padding={8} style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        {/* Status bar */}
        <Flexbox align="center" horizontal justify="space-between">
          <Flexbox align="center" gap={8} horizontal>
            <div
              style={{
                backgroundColor: isConnected ? '#4ec9b0' : error ? '#f14c4c' : '#6a6a6a',
                borderRadius: '50%',
                height: 8,
                width: 8,
              }}
            />
            <span style={{ color: '#d4d4d4', fontSize: 12 }}>
              {isConnected ? 'Connected' : error ? 'Error' : 'Disconnected'}
            </span>
          </Flexbox>

          <Flexbox gap={4} horizontal>
            <Tooltip title="Connection Settings">
              <ActionIcon
                icon={Settings}
                onClick={() => setShowConfig(!showConfig)}
                size="small"
              />
            </Tooltip>
            {isConnected ? (
              <Button
                danger
                icon={<Link2Off size={14} />}
                onClick={onDisconnect}
                size="small"
              >
                Disconnect
              </Button>
            ) : (
              <Button
                icon={<Link2 size={14} />}
                onClick={handleConnect}
                size="small"
                type="primary"
              >
                Connect
              </Button>
            )}
          </Flexbox>
        </Flexbox>

        {/* Error message */}
        {error && (
          <div
            style={{
              backgroundColor: 'rgba(241, 76, 76, 0.1)',
              borderRadius: 4,
              color: '#f14c4c',
              fontSize: 12,
              padding: 8,
            }}
          >
            {error}
          </div>
        )}

        {/* Configuration panel */}
        {showConfig && (
          <Flexbox gap={8} style={{ backgroundColor: '#252526', borderRadius: 4, padding: 12 }}>
            <Flexbox gap={4}>
              <label style={{ color: '#9cdcfe', fontSize: 11 }}>OpenHands URL</label>
              <Input
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="/agent or http://localhost:3000"
                size="small"
                value={baseUrl}
              />
            </Flexbox>
            <Flexbox gap={4}>
              <label style={{ color: '#9cdcfe', fontSize: 11 }}>
                Conversation ID (optional)
              </label>
              <Input
                onChange={(e) => setConversationId(e.target.value)}
                placeholder="Leave empty for new conversation"
                size="small"
                value={conversationId}
              />
            </Flexbox>
            <div style={{ color: '#6a6a6a', fontSize: 11 }}>
              Tip: Start a conversation in OpenHands first, then copy the conversation ID from the
              URL to connect to an existing session.
            </div>
          </Flexbox>
        )}
      </Flexbox>
    );
  }
);

export default ConnectionStatus;
