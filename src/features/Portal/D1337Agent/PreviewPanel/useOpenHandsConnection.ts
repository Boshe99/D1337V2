'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import type { ConnectionConfig, FileState, OpenHandsEvent, TerminalLine } from './types';

// Default OpenHands URL - can be configured via environment variable
const DEFAULT_OPENHANDS_URL = process.env.NEXT_PUBLIC_D1337_AGENT_URL || '/agent';

interface UseOpenHandsConnectionReturn {
  isConnected: boolean;
  connectionError: string | null;
  events: OpenHandsEvent[];
  currentFile: FileState | null;
  terminalOutput: TerminalLine[];
  connect: (config?: Partial<ConnectionConfig>) => void;
  disconnect: () => void;
  sendMessage: (message: string) => void;
}

export const useOpenHandsConnection = (): UseOpenHandsConnectionReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [events, setEvents] = useState<OpenHandsEvent[]>([]);
  const [currentFile, setCurrentFile] = useState<FileState | null>(null);
  const [terminalOutput, setTerminalOutput] = useState<TerminalLine[]>([]);

  const socketRef = useRef<WebSocket | null>(null);
  const configRef = useRef<ConnectionConfig>({
    baseUrl: DEFAULT_OPENHANDS_URL,
    conversationId: '',
  });

  // Process incoming OpenHands events
  const processEvent = useCallback((event: OpenHandsEvent) => {
    setEvents((prev) => [...prev, event]);

    // Handle different event types
    if (event.action === 'run' && event.args?.command) {
      // Terminal command execution
      const commandLine: TerminalLine = {
        content: `$ ${event.args.command}`,
        id: `cmd-${event.id}`,
        timestamp: event.timestamp,
        type: 'command',
      };
      setTerminalOutput((prev) => [...prev, commandLine]);

      if (event.result || event.observation) {
        const outputLine: TerminalLine = {
          content: event.result || event.observation || '',
          id: `out-${event.id}`,
          timestamp: event.timestamp,
          type: 'output',
        };
        setTerminalOutput((prev) => [...prev, outputLine]);
      }
    }

    if ((event.action === 'write' || event.action === 'edit') && event.args?.path) {
      // File write/edit
      const extension = event.args.path.split('.').pop() || 'txt';
      const languageMap: Record<string, string> = {
        css: 'css',
        html: 'html',
        js: 'javascript',
        json: 'json',
        jsx: 'jsx',
        md: 'markdown',
        py: 'python',
        rs: 'rust',
        ts: 'typescript',
        tsx: 'tsx',
        yaml: 'yaml',
        yml: 'yaml',
      };

      setCurrentFile({
        content: event.args.content || '',
        language: languageMap[extension] || 'plaintext',
        path: event.args.path,
      });
    }
  }, []);

  // Connect to OpenHands WebSocket
  const connect = useCallback((config?: Partial<ConnectionConfig>) => {
    if (config) {
      configRef.current = { ...configRef.current, ...config };
    }

    const { baseUrl, conversationId } = configRef.current;

    // Disconnect existing connection
    if (socketRef.current) {
      socketRef.current.close();
    }

    setConnectionError(null);

    try {
      // Build WebSocket URL for Socket.IO
      // Socket.IO uses a specific URL format: ws://host/socket.io/?EIO=4&transport=websocket
      let wsUrl = baseUrl;
      if (wsUrl.startsWith('/')) {
        // Relative URL - construct full WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${protocol}//${window.location.host}${baseUrl}`;
      } else if (wsUrl.startsWith('http')) {
        wsUrl = wsUrl.replace(/^http/, 'ws');
      }

      // Add Socket.IO parameters
      const socketIOUrl = `${wsUrl}/socket.io/?EIO=4&transport=websocket${conversationId ? `&conversation_id=${conversationId}` : ''}&latest_event_id=-1`;

      const socket = new WebSocket(socketIOUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        // Send Socket.IO handshake
        socket.send('40{}');
        setIsConnected(true);
        setConnectionError(null);

        // Add connection event to terminal
        setTerminalOutput((prev) => [
          ...prev,
          {
            content: `Connected to OpenHands at ${baseUrl}`,
            id: `sys-${Date.now()}`,
            timestamp: new Date().toISOString(),
            type: 'output',
          },
        ]);
      };

      socket.onmessage = (event) => {
        const data = event.data as string;

        // Socket.IO message format: <type><data>
        // 0 = open, 2 = ping, 3 = pong, 4 = message
        // 42 = event message
        if (data.startsWith('42')) {
          try {
            const jsonStr = data.slice(2);
            const parsed = JSON.parse(jsonStr);
            if (Array.isArray(parsed) && parsed[0] === 'oh_event') {
              processEvent(parsed[1] as OpenHandsEvent);
            }
          } catch {
            console.error('Failed to parse Socket.IO message:', data);
          }
        } else if (data === '2') {
          // Ping - respond with pong
          socket.send('3');
        }
      };

      socket.onerror = () => {
        setConnectionError('WebSocket connection error. Check if OpenHands is running.');
        setIsConnected(false);
      };

      socket.onclose = () => {
        setIsConnected(false);
        setTerminalOutput((prev) => [
          ...prev,
          {
            content: 'Disconnected from OpenHands',
            id: `sys-${Date.now()}`,
            timestamp: new Date().toISOString(),
            type: 'error',
          },
        ]);
      };
    } catch (error) {
      setConnectionError(`Failed to connect: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setIsConnected(false);
    }
  }, [processEvent]);

  // Disconnect from OpenHands
  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Send a message to OpenHands
  const sendMessage = useCallback((message: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      const action = {
        message,
        source: 'user',
        type: 'message',
      };
      socketRef.current.send(`42["oh_user_action",${JSON.stringify(action)}]`);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  return {
    connect,
    connectionError,
    currentFile,
    disconnect,
    events,
    isConnected,
    sendMessage,
    terminalOutput,
  };
};
