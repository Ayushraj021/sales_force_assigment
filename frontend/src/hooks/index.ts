/**
 * React Hooks
 *
 * Custom hooks for the marketing analytics platform.
 */

// Real-time communication
export {
  useWebSocket,
  useWebSocketChannel,
  useTrainingUpdates,
  useDashboardUpdates,
  useServerSentEvents,
} from './useWebSocket';

export type {
  WebSocketConfig,
  WebSocketState,
  WebSocketActions,
  WebSocketReturn,
  ChannelSubscription,
  TrainingUpdate,
  DashboardUpdate,
} from './useWebSocket';
