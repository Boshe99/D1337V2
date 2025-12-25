// OpenHands event types based on WebSocket API documentation
export interface OpenHandsEvent {
  id: string;
  source: 'user' | 'agent';
  timestamp: string;
  message?: string;
  type?: string;
  action?: 'run' | 'edit' | 'write' | 'read' | 'browse' | 'think';
  args?: {
    command?: string;
    path?: string;
    content?: string;
    thought?: string;
    url?: string;
  };
  result?: string;
  observation?: string;
}

export interface FileState {
  path: string;
  content: string;
  language: string;
}

export interface TerminalLine {
  id: string;
  type: 'command' | 'output' | 'error';
  content: string;
  timestamp: string;
}

export interface ConnectionConfig {
  baseUrl: string;
  conversationId: string;
}
