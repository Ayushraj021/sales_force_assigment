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

// Reports
export {
  useReports,
  useScheduledReports,
  useExport,
  useGenerateReport,
  useScheduleReport,
  useCancelScheduledReport,
  useReportMutations,
} from './useReports';

export type {
  ScheduleReportInput,
  GenerateReportInput,
} from './useReports';

// Data Connectors
export {
  useConnectors,
  useConnector,
  useCreateConnector,
  useUpdateConnector,
  useTestConnector,
  useSyncConnector,
  useDeleteConnector,
  useConnectorMutations,
} from './useConnectors';

export type {
  CreateConnectorInput,
  UpdateConnectorInput,
} from './useConnectors';

// Geo Experiments
export {
  useGeoExperiments,
  useGeoExperiment,
  useCreateGeoExperiment,
  useRunPowerAnalysis,
  useAnalyzeGeoExperiment,
  useGeoExperimentActions,
  useGeoExperimentMutations,
} from './useGeoExperiments';
