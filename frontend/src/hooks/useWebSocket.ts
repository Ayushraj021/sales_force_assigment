/**
 * WebSocket Hooks for Real-Time Communication
 *
 * Provides React hooks for real-time data streaming,
 * live updates, and bidirectional communication.
 */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';

// Types
export interface WebSocketConfig {
  url: string;
  protocols?: string | string[];
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  onMessage?: (data: unknown) => void;
  autoConnect?: boolean;
}

export interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  reconnectCount: number;
  lastMessage: unknown | null;
  lastMessageTime: Date | null;
  error: Event | null;
}

export interface WebSocketActions {
  connect: () => void;
  disconnect: () => void;
  send: (data: unknown) => void;
  sendJson: (data: object) => void;
}

export type WebSocketReturn = [WebSocketState, WebSocketActions];

// Default configuration
const DEFAULT_CONFIG: Partial<WebSocketConfig> = {
  reconnectAttempts: 5,
  reconnectInterval: 3000,
  heartbeatInterval: 30000,
  autoConnect: true,
};

/**
 * Main WebSocket hook for real-time communication.
 *
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Heartbeat/ping-pong for connection health
 * - JSON message parsing
 * - Connection state management
 *
 * @example
 * ```tsx
 * const [state, actions] = useWebSocket({
 *   url: 'wss://api.example.com/ws',
 *   onMessage: (data) => console.log('Received:', data),
 * });
 *
 * // Send data
 * actions.sendJson({ type: 'subscribe', channel: 'updates' });
 * ```
 */
export function useWebSocket(config: WebSocketConfig): WebSocketReturn {
  const fullConfig = useMemo(
    () => ({ ...DEFAULT_CONFIG, ...config }),
    [config]
  );

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    reconnectCount: 0,
    lastMessage: null,
    lastMessageTime: null,
    error: null,
  });

  // Clear timers
  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  // Start heartbeat
  const startHeartbeat = useCallback(() => {
    if (!fullConfig.heartbeatInterval) return;

    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, fullConfig.heartbeatInterval);
  }, [fullConfig.heartbeatInterval]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setState((prev) => ({ ...prev, isConnecting: true, error: null }));

    try {
      wsRef.current = new WebSocket(fullConfig.url, fullConfig.protocols);

      wsRef.current.onopen = (event) => {
        setState((prev) => ({
          ...prev,
          isConnected: true,
          isConnecting: false,
          reconnectCount: 0,
          error: null,
        }));
        startHeartbeat();
        fullConfig.onOpen?.(event);
      };

      wsRef.current.onclose = (event) => {
        setState((prev) => ({
          ...prev,
          isConnected: false,
          isConnecting: false,
        }));
        clearTimers();
        fullConfig.onClose?.(event);

        // Auto-reconnect if not intentional close
        if (!event.wasClean && state.reconnectCount < (fullConfig.reconnectAttempts || 0)) {
          const delay = fullConfig.reconnectInterval! * Math.pow(2, state.reconnectCount);
          reconnectTimeoutRef.current = setTimeout(() => {
            setState((prev) => ({
              ...prev,
              reconnectCount: prev.reconnectCount + 1,
            }));
            connect();
          }, delay);
        }
      };

      wsRef.current.onerror = (event) => {
        setState((prev) => ({ ...prev, error: event }));
        fullConfig.onError?.(event);
      };

      wsRef.current.onmessage = (event) => {
        let data: unknown;
        try {
          data = JSON.parse(event.data);
        } catch {
          data = event.data;
        }

        // Handle pong messages
        if (typeof data === 'object' && data !== null && 'type' in data && (data as { type: string }).type === 'pong') {
          return;
        }

        setState((prev) => ({
          ...prev,
          lastMessage: data,
          lastMessageTime: new Date(),
        }));
        fullConfig.onMessage?.(data);
      };
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isConnecting: false,
        error: error as Event,
      }));
    }
  }, [fullConfig, state.reconnectCount, startHeartbeat, clearTimers]);

  // Disconnect
  const disconnect = useCallback(() => {
    clearTimers();
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }
    setState((prev) => ({
      ...prev,
      isConnected: false,
      isConnecting: false,
      reconnectCount: 0,
    }));
  }, [clearTimers]);

  // Send raw data
  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }, []);

  // Send JSON data
  const sendJson = useCallback((data: object) => {
    send(JSON.stringify(data));
  }, [send]);

  // Auto-connect on mount
  useEffect(() => {
    if (fullConfig.autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const actions: WebSocketActions = useMemo(
    () => ({ connect, disconnect, send, sendJson }),
    [connect, disconnect, send, sendJson]
  );

  return [state, actions];
}

/**
 * Hook for subscribing to specific WebSocket channels/topics.
 */
export interface ChannelSubscription<T = unknown> {
  channel: string;
  data: T | null;
  isSubscribed: boolean;
  subscribe: () => void;
  unsubscribe: () => void;
}

export function useWebSocketChannel<T = unknown>(
  ws: WebSocketReturn,
  channel: string
): ChannelSubscription<T> {
  const [state, actions] = ws;
  const [data, setData] = useState<T | null>(null);
  const [isSubscribed, setIsSubscribed] = useState(false);

  // Subscribe to channel
  const subscribe = useCallback(() => {
    if (state.isConnected) {
      actions.sendJson({ type: 'subscribe', channel });
      setIsSubscribed(true);
    }
  }, [state.isConnected, actions, channel]);

  // Unsubscribe
  const unsubscribe = useCallback(() => {
    if (state.isConnected) {
      actions.sendJson({ type: 'unsubscribe', channel });
      setIsSubscribed(false);
    }
  }, [state.isConnected, actions, channel]);

  // Handle incoming messages
  useEffect(() => {
    if (state.lastMessage) {
      const msg = state.lastMessage as { channel?: string; data?: T };
      if (msg.channel === channel && msg.data !== undefined) {
        setData(msg.data);
      }
    }
  }, [state.lastMessage, channel]);

  // Auto-subscribe when connected
  useEffect(() => {
    if (state.isConnected && !isSubscribed) {
      subscribe();
    }
  }, [state.isConnected, isSubscribed, subscribe]);

  return {
    channel,
    data,
    isSubscribed,
    subscribe,
    unsubscribe,
  };
}

/**
 * Hook for real-time model training updates.
 */
export interface TrainingUpdate {
  jobId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  currentEpoch?: number;
  totalEpochs?: number;
  metrics?: Record<string, number>;
  message?: string;
}

export function useTrainingUpdates(
  wsUrl: string,
  jobId: string
): {
  update: TrainingUpdate | null;
  isConnected: boolean;
  error: Event | null;
} {
  const [update, setUpdate] = useState<TrainingUpdate | null>(null);

  const [state] = useWebSocket({
    url: `${wsUrl}/training/${jobId}`,
    onMessage: (data) => {
      if (data && typeof data === 'object' && 'jobId' in data) {
        setUpdate(data as TrainingUpdate);
      }
    },
  });

  return {
    update,
    isConnected: state.isConnected,
    error: state.error,
  };
}

/**
 * Hook for real-time dashboard data updates.
 */
export interface DashboardUpdate {
  widgetId: string;
  data: unknown;
  timestamp: string;
}

export function useDashboardUpdates(
  wsUrl: string,
  dashboardId: string,
  widgetIds: string[]
): {
  updates: Map<string, DashboardUpdate>;
  isConnected: boolean;
  lastUpdate: Date | null;
} {
  const [updates, setUpdates] = useState<Map<string, DashboardUpdate>>(new Map());
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const [state, actions] = useWebSocket({
    url: `${wsUrl}/dashboard/${dashboardId}`,
    onMessage: (data) => {
      if (data && typeof data === 'object' && 'widgetId' in data) {
        const update = data as DashboardUpdate;
        setUpdates((prev) => new Map(prev).set(update.widgetId, update));
        setLastUpdate(new Date());
      }
    },
  });

  // Subscribe to widget updates when connected
  useEffect(() => {
    if (state.isConnected) {
      actions.sendJson({
        type: 'subscribe',
        widgets: widgetIds,
      });
    }
  }, [state.isConnected, widgetIds, actions]);

  return {
    updates,
    isConnected: state.isConnected,
    lastUpdate,
  };
}

/**
 * Hook for server-sent events (SSE) as an alternative to WebSocket.
 */
export function useServerSentEvents<T = unknown>(
  url: string,
  options?: { withCredentials?: boolean }
): {
  data: T | null;
  isConnected: boolean;
  error: Event | null;
  close: () => void;
} {
  const eventSourceRef = useRef<EventSource | null>(null);
  const [data, setData] = useState<T | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Event | null>(null);

  useEffect(() => {
    eventSourceRef.current = new EventSource(url, options);

    eventSourceRef.current.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    eventSourceRef.current.onmessage = (event) => {
      try {
        setData(JSON.parse(event.data));
      } catch {
        setData(event.data as unknown as T);
      }
    };

    eventSourceRef.current.onerror = (event) => {
      setError(event);
      setIsConnected(false);
    };

    return () => {
      eventSourceRef.current?.close();
    };
  }, [url, options]);

  const close = useCallback(() => {
    eventSourceRef.current?.close();
    setIsConnected(false);
  }, []);

  return { data, isConnected, error, close };
}

export default useWebSocket;
