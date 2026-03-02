/**
 * GraphQL Client
 *
 * Centralized GraphQL client for API calls with authentication and error handling.
 */

import { GRAPHQL_ENDPOINT } from './constants'

interface GraphQLResponse<T = unknown> {
  data?: T
  errors?: Array<{ message: string; locations?: Array<{ line: number; column: number }>; path?: string[] }>
}

interface GraphQLRequestOptions {
  requiresAuth?: boolean
  signal?: AbortSignal
}

/**
 * Execute a GraphQL query or mutation
 */
export async function graphqlRequest<T = unknown>(
  query: string,
  variables?: Record<string, unknown>,
  options: GraphQLRequestOptions = {}
): Promise<T> {
  const { requiresAuth = true, signal } = options

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  if (requiresAuth) {
    const authStorage = localStorage.getItem('auth-storage')
    if (authStorage) {
      const { state } = JSON.parse(authStorage)
      if (state?.accessToken) {
        headers['Authorization'] = `Bearer ${state.accessToken}`
      }
    }
  }

  const response = await fetch(GRAPHQL_ENDPOINT, {
    method: 'POST',
    headers,
    body: JSON.stringify({ query, variables }),
    signal,
  })

  const result: GraphQLResponse<T> = await response.json()

  if (result.errors && result.errors.length > 0) {
    const errorMessage = result.errors.map(e => e.message).join(', ')
    throw new GraphQLError(errorMessage, result.errors)
  }

  if (!result.data) {
    throw new Error('No data returned from GraphQL')
  }

  return result.data
}

/**
 * Custom GraphQL Error class
 */
export class GraphQLError extends Error {
  errors: Array<{ message: string; locations?: Array<{ line: number; column: number }>; path?: string[] }>

  constructor(message: string, errors: Array<{ message: string }>) {
    super(message)
    this.name = 'GraphQLError'
    this.errors = errors
  }
}

// ============================================================================
// GraphQL Queries
// ============================================================================

export const QUERIES = {
  // User Queries
  ME: `
    query Me {
      me {
        id
        email
        firstName
        lastName
        fullName
        isActive
        isVerified
        isSuperuser
        organization {
          id
          name
          slug
          subscriptionTier
          maxUsers
          maxModels
          maxDatasets
        }
        roles {
          id
          name
          description
        }
        createdAt
        updatedAt
      }
    }
  `,

  USER: `
    query User($id: UUID!) {
      user(id: $id) {
        id
        email
        firstName
        lastName
        fullName
        isActive
        isVerified
        isSuperuser
        organization {
          id
          name
        }
        roles {
          id
          name
          description
        }
        createdAt
        updatedAt
      }
    }
  `,

  USERS: `
    query Users($limit: Int, $offset: Int) {
      users(limit: $limit, offset: $offset) {
        id
        email
        firstName
        lastName
        fullName
        isActive
        isVerified
        isSuperuser
        roles {
          id
          name
        }
        createdAt
        updatedAt
      }
    }
  `,

  ORGANIZATION: `
    query Organization($id: UUID) {
      organization(id: $id) {
        id
        name
        slug
        description
        isActive
        subscriptionTier
        maxUsers
        maxModels
        maxDatasets
        createdAt
        updatedAt
      }
    }
  `,

  // Model Queries
  MODEL: `
    query Model($id: UUID!) {
      model(id: $id) {
        id
        name
        description
        modelType
        status
        config
        hyperparameters
        versions {
          id
          version
          description
          isCurrent
          status
          trainingDurationSeconds
          mlflowRunId
          metrics
          createdAt
        }
        parameters {
          id
          parameterName
          parameterType
          value
          stdError
          ciLower
          ciUpper
          posteriorMean
          posteriorStd
        }
        adstockConfigs {
          id
          channelName
          adstockType
          decayRate
          shape
          scale
          maxLag
          normalize
          fittedParams
        }
        saturationConfigs {
          id
          channelName
          saturationType
          alpha
          gamma
          k
          m
          vmax
          km
          fittedParams
        }
        createdAt
        updatedAt
      }
    }
  `,

  MODELS: `
    query Models($modelType: String, $status: String, $limit: Int, $offset: Int) {
      models(modelType: $modelType, status: $status, limit: $limit, offset: $offset) {
        id
        name
        description
        modelType
        status
        versions {
          id
          version
          isCurrent
          status
          metrics
          createdAt
        }
        createdAt
        updatedAt
      }
    }
  `,

  EXPERIMENT: `
    query Experiment($id: UUID!) {
      experiment(id: $id) {
        id
        name
        description
        status
        mlflowExperimentId
        config
        runs {
          id
          runName
          status
          mlflowRunId
          parameters
          hyperparameters
          metrics
          durationSeconds
          createdAt
        }
        createdAt
        updatedAt
      }
    }
  `,

  EXPERIMENTS: `
    query Experiments($status: String, $limit: Int, $offset: Int) {
      experiments(status: $status, limit: $limit, offset: $offset) {
        id
        name
        description
        status
        runs {
          id
          status
          metrics
          createdAt
        }
        createdAt
        updatedAt
      }
    }
  `,

  // Health Check
  HEALTH: `
    query Health {
      health
      version
    }
  `,

  // ============================================================================
  // Phase 6: Monitoring Queries
  // ============================================================================
  ALERTS: `
    query Alerts($severity: String, $acknowledged: Boolean, $limit: Int, $offset: Int) {
      alerts(severity: $severity, acknowledged: $acknowledged, limit: $limit, offset: $offset) {
        id
        alertType
        severity
        title
        message
        modelId
        metricName
        currentValue
        threshold
        isAcknowledged
        acknowledgedBy
        acknowledgedAt
        createdAt
      }
    }
  `,

  ACTIVE_ALERTS: `
    query ActiveAlerts($modelId: UUID) {
      activeAlerts(modelId: $modelId) {
        id
        alertType
        severity
        title
        message
        modelId
        metricName
        currentValue
        threshold
        createdAt
      }
    }
  `,

  MONITOR_CONFIGS: `
    query MonitorConfigs($modelId: UUID, $isActive: Boolean) {
      monitorConfigs(modelId: $modelId, isActive: $isActive) {
        id
        modelId
        metricName
        alertType
        threshold
        windowSize
        checkFrequency
        isActive
        lastChecked
        createdAt
      }
    }
  `,

  MONITORING_SUMMARY: `
    query MonitoringSummary($modelId: UUID) {
      monitoringSummary(modelId: $modelId) {
        totalAlerts
        criticalAlerts
        warningAlerts
        infoAlerts
        acknowledgedAlerts
        activeMonitors
        lastCheckTime
      }
    }
  `,

  MODEL_METRICS_HISTORY: `
    query ModelMetricsHistory($modelId: UUID!, $metricName: String!, $startDate: DateTime, $endDate: DateTime) {
      modelMetricsHistory(modelId: $modelId, metricName: $metricName, startDate: $startDate, endDate: $endDate) {
        timestamp
        value
        metricName
      }
    }
  `,

  // ============================================================================
  // Phase 6: ETL Pipeline Queries
  // ============================================================================
  ETL_PIPELINES: `
    query EtlPipelines($status: String, $limit: Int, $offset: Int) {
      etlPipelines(status: $status, limit: $limit, offset: $offset) {
        id
        name
        description
        status
        schedule
        lastRunAt
        nextRunAt
        createdAt
        updatedAt
      }
    }
  `,

  ETL_PIPELINE: `
    query EtlPipeline($id: UUID!) {
      etlPipeline(id: $id) {
        id
        name
        description
        status
        schedule
        config
        lastRunAt
        nextRunAt
        steps {
          id
          name
          stepType
          stepOrder
          config
          status
        }
        createdAt
        updatedAt
      }
    }
  `,

  ETL_PIPELINE_RUNS: `
    query EtlPipelineRuns($pipelineId: UUID!, $status: String, $limit: Int, $offset: Int) {
      etlPipelineRuns(pipelineId: $pipelineId, status: $status, limit: $limit, offset: $offset) {
        id
        pipelineId
        status
        startedAt
        completedAt
        error
        metrics
      }
    }
  `,

  ETL_PIPELINE_RUN: `
    query EtlPipelineRun($id: UUID!) {
      etlPipelineRun(id: $id) {
        id
        pipelineId
        status
        startedAt
        completedAt
        error
        metrics
        stepResults {
          stepId
          status
          startedAt
          completedAt
          error
          outputMetrics
        }
      }
    }
  `,

  // ============================================================================
  // Phase 6: Model Registry Queries
  // ============================================================================
  REGISTERED_MODELS: `
    query RegisteredModels($stage: String, $limit: Int, $offset: Int) {
      registeredModels(stage: $stage, limit: $limit, offset: $offset) {
        id
        name
        description
        currentStage
        latestVersion
        tags
        createdAt
        updatedAt
      }
    }
  `,

  REGISTERED_MODEL: `
    query RegisteredModel($id: UUID!) {
      registeredModel(id: $id) {
        id
        name
        description
        currentStage
        latestVersion
        tags
        versions {
          id
          version
          stage
          description
          mlflowRunId
          metrics
          createdAt
        }
        createdAt
        updatedAt
      }
    }
  `,

  MODEL_VERSION: `
    query ModelVersion($modelId: UUID!, $version: String!) {
      modelVersion(modelId: $modelId, version: $version) {
        id
        version
        stage
        description
        mlflowRunId
        metrics
        artifactPath
        createdAt
      }
    }
  `,

  MODEL_VERSIONS: `
    query ModelVersions($modelId: UUID!, $stage: String, $limit: Int, $offset: Int) {
      modelVersions(modelId: $modelId, stage: $stage, limit: $limit, offset: $offset) {
        id
        version
        stage
        description
        mlflowRunId
        metrics
        createdAt
      }
    }
  `,

  COMPARE_MODEL_VERSIONS: `
    query CompareModelVersions($modelId: UUID!, $versions: [String!]!) {
      compareModelVersions(modelId: $modelId, versions: $versions) {
        versions {
          version
          stage
          metrics
          createdAt
        }
        metricDiffs
      }
    }
  `,

  // ============================================================================
  // Phase 6: Job Scheduler Queries
  // ============================================================================
  SCHEDULED_JOBS: `
    query ScheduledJobs($status: String, $jobType: String, $limit: Int, $offset: Int) {
      scheduledJobs(status: $status, jobType: $jobType, limit: $limit, offset: $offset) {
        id
        name
        description
        jobType
        schedule
        scheduleType
        status
        lastRunAt
        nextRunAt
        config
        createdAt
        updatedAt
      }
    }
  `,

  SCHEDULED_JOB: `
    query ScheduledJob($id: UUID!) {
      scheduledJob(id: $id) {
        id
        name
        description
        jobType
        schedule
        scheduleType
        status
        lastRunAt
        nextRunAt
        config
        runs {
          id
          status
          startedAt
          completedAt
          error
        }
        createdAt
        updatedAt
      }
    }
  `,

  JOB_RUNS: `
    query JobRuns($jobId: UUID!, $status: String, $limit: Int, $offset: Int) {
      jobRuns(jobId: $jobId, status: $status, limit: $limit, offset: $offset) {
        id
        jobId
        status
        startedAt
        completedAt
        error
        output
      }
    }
  `,

  SCHEDULER_STATUS: `
    query SchedulerStatus {
      schedulerStatus {
        isRunning
        activeJobs
        pendingJobs
        failedJobs
        lastHeartbeat
      }
    }
  `,

  // ============================================================================
  // Phase 6: Data Versioning Queries
  // ============================================================================
  DATA_VERSIONS: `
    query DataVersions($datasetId: UUID!, $limit: Int, $offset: Int) {
      dataVersions(datasetId: $datasetId, limit: $limit, offset: $offset) {
        id
        datasetId
        version
        description
        rowCount
        columnCount
        checksum
        createdBy
        createdAt
      }
    }
  `,

  DATA_VERSION: `
    query DataVersion($id: UUID!) {
      dataVersion(id: $id) {
        id
        datasetId
        version
        description
        rowCount
        columnCount
        schema
        checksum
        storagePath
        createdBy
        createdAt
      }
    }
  `,

  COMPARE_DATA_VERSIONS: `
    query CompareDataVersions($datasetId: UUID!, $version1: String!, $version2: String!) {
      compareDataVersions(datasetId: $datasetId, version1: $version1, version2: $version2) {
        addedRows
        removedRows
        modifiedRows
        schemaChanges
      }
    }
  `,

  // ============================================================================
  // Phase 6: Consent Management Queries
  // ============================================================================
  CONSENT_RECORDS: `
    query ConsentRecords($userId: UUID, $consentType: String, $limit: Int, $offset: Int) {
      consentRecords(userId: $userId, consentType: $consentType, limit: $limit, offset: $offset) {
        id
        userId
        consentType
        status
        version
        grantedAt
        expiresAt
        revokedAt
        ipAddress
      }
    }
  `,

  CONSENT_RECORD: `
    query ConsentRecord($id: UUID!) {
      consentRecord(id: $id) {
        id
        userId
        consentType
        status
        version
        consentText
        grantedAt
        expiresAt
        revokedAt
        ipAddress
        metadata
      }
    }
  `,

  USER_CONSENT_STATUS: `
    query UserConsentStatus($userId: UUID!) {
      userConsentStatus(userId: $userId) {
        userId
        consents {
          consentType
          status
          version
          grantedAt
          expiresAt
        }
      }
    }
  `,

  // ============================================================================
  // Reports Queries
  // ============================================================================
  REPORTS: `
    query Reports($reportType: String, $limit: Int, $offset: Int) {
      reports(reportType: $reportType, limit: $limit, offset: $offset) {
        id
        name
        description
        reportType
        template
        sections
        availableFormats
        createdAt
        updatedAt
      }
    }
  `,

  REPORT: `
    query Report($id: UUID!) {
      report(id: $id) {
        id
        name
        description
        reportType
        template
        sections
        availableFormats
        createdAt
        updatedAt
      }
    }
  `,

  SCHEDULED_REPORTS: `
    query ScheduledReports($isActive: Boolean, $limit: Int, $offset: Int) {
      scheduledReports(isActive: $isActive, limit: $limit, offset: $offset) {
        id
        name
        isActive
        scheduleType
        scheduleConfig
        timezone
        deliveryMethod
        deliveryConfig
        recipients
        exportFormat
        lastRunAt
        lastRunStatus
        nextRunAt
        reportId
        createdAt
        updatedAt
      }
    }
  `,

  EXPORT: `
    query Export($id: UUID!) {
      export(id: $id) {
        id
        exportType
        exportFormat
        status
        filePath
        fileSizeBytes
        downloadUrl
        expiresAt
        errorMessage
        createdAt
        updatedAt
      }
    }
  `,

  REPORT_TEMPLATES: `
    query ReportTemplates {
      reportTemplates {
        id
        name
        description
        reportType
        sections
        availableFormats
      }
    }
  `,

  // ============================================================================
  // Data Connectors Queries
  // ============================================================================
  DATA_CONNECTORS: `
    query DataConnectors($isActive: Boolean, $limit: Int, $offset: Int) {
      dataConnectors(isActive: $isActive, limit: $limit, offset: $offset) {
        id
        name
        description
        sourceType
        isActive
        createdAt
        updatedAt
      }
    }
  `,

  DATA_CONNECTOR: `
    query DataConnector($id: UUID!) {
      dataConnector(id: $id) {
        id
        name
        description
        sourceType
        isActive
        createdAt
        updatedAt
      }
    }
  `,

  CONNECTOR_TYPES: `
    query ConnectorTypes {
      connectorTypes {
        id
        name
        category
        description
        requiredFields
      }
    }
  `,

  // ============================================================================
  // Geo Experiment Queries
  // ============================================================================
  GEO_EXPERIMENTS: `
    query GeoExperiments($filter: GeoExperimentFilterInput, $limit: Int, $offset: Int) {
      geoExperiments(filter: $filter, limit: $limit, offset: $offset) {
        id
        name
        description
        status
        testRegions
        controlRegions
        holdoutRegions
        startDate
        endDate
        warmupDays
        powerAnalysis
        minimumDetectableEffect
        targetPower
        results
        absoluteLift
        relativeLift
        pValue
        confidenceIntervalLower
        confidenceIntervalUpper
        primaryMetric
        secondaryMetrics
        organizationId
        createdById
        createdAt
        updatedAt
        completedAt
      }
    }
  `,

  GEO_EXPERIMENT: `
    query GeoExperiment($experimentId: UUID!) {
      geoExperiment(experimentId: $experimentId) {
        id
        name
        description
        status
        testRegions
        controlRegions
        holdoutRegions
        startDate
        endDate
        warmupDays
        powerAnalysis
        minimumDetectableEffect
        targetPower
        results
        absoluteLift
        relativeLift
        pValue
        confidenceIntervalLower
        confidenceIntervalUpper
        primaryMetric
        secondaryMetrics
        organizationId
        createdById
        createdAt
        updatedAt
        completedAt
      }
    }
  `,

  GEO_EXPERIMENT_STATUSES: `
    query GeoExperimentStatuses {
      geoExperimentStatuses
    }
  `,

  GEO_EXPERIMENTS_SUMMARY: `
    query GeoExperimentsSummary {
      geoExperimentsSummary
    }
  `,
}

// ============================================================================
// GraphQL Mutations
// ============================================================================

export const MUTATIONS = {
  // Auth Mutations (already in authStore, but for reference)
  LOGIN: `
    mutation Login($input: LoginInput!) {
      login(input: $input) {
        token {
          accessToken
          refreshToken
          expiresIn
        }
        user {
          id
          email
          firstName
          lastName
          fullName
          isActive
          isVerified
          isSuperuser
          roles {
            name
          }
        }
      }
    }
  `,

  REGISTER: `
    mutation Register($input: RegisterInput!) {
      register(input: $input) {
        token {
          accessToken
          refreshToken
          expiresIn
        }
        user {
          id
          email
          firstName
          lastName
          fullName
          isActive
          isVerified
          isSuperuser
          roles {
            name
          }
        }
      }
    }
  `,

  UPDATE_PROFILE: `
    mutation UpdateProfile($input: UpdateUserInput!) {
      updateProfile(input: $input) {
        id
        email
        firstName
        lastName
        fullName
        isActive
        isVerified
        isSuperuser
        roles {
          name
        }
      }
    }
  `,

  CHANGE_PASSWORD: `
    mutation ChangePassword($input: ChangePasswordInput!) {
      changePassword(input: $input)
    }
  `,

  // Model Mutations
  CREATE_MODEL: `
    mutation CreateModel($input: CreateModelInput!) {
      createModel(input: $input) {
        id
        name
        description
        modelType
        status
        createdAt
      }
    }
  `,

  DELETE_MODEL: `
    mutation DeleteModel($id: UUID!) {
      deleteModel(id: $id)
    }
  `,

  TRAIN_MODEL: `
    mutation TrainModel($modelId: UUID!) {
      trainModel(modelId: $modelId) {
        modelId
        versionId
        status
        message
      }
    }
  `,

  // Inference Mutations
  PREDICT: `
    mutation Predict($input: PredictInput!) {
      predict(input: $input) {
        modelId
        modelVersion
        predictions
        contributionByChannel
        confidenceIntervals
      }
    }
  `,

  DECOMPOSE_CONTRIBUTIONS: `
    mutation DecomposeContributions($input: DecomposeInput!) {
      decomposeContributions(input: $input) {
        modelId
        modelVersion
        totalContribution
        baselineContribution
        channelContributions
        timeSeriesDecomposition
      }
    }
  `,

  // ============================================================================
  // Phase 6: Monitoring Mutations
  // ============================================================================
  CREATE_MONITOR_CONFIG: `
    mutation CreateMonitorConfig($input: CreateMonitorConfigInput!) {
      createMonitorConfig(input: $input) {
        id
        modelId
        metricName
        alertType
        threshold
        windowSize
        checkFrequency
        isActive
        createdAt
      }
    }
  `,

  UPDATE_MONITOR_CONFIG: `
    mutation UpdateMonitorConfig($id: UUID!, $input: UpdateMonitorConfigInput!) {
      updateMonitorConfig(id: $id, input: $input) {
        id
        metricName
        alertType
        threshold
        windowSize
        checkFrequency
        isActive
      }
    }
  `,

  DELETE_MONITOR_CONFIG: `
    mutation DeleteMonitorConfig($id: UUID!) {
      deleteMonitorConfig(id: $id)
    }
  `,

  ACKNOWLEDGE_ALERT: `
    mutation AcknowledgeAlert($id: UUID!, $note: String) {
      acknowledgeAlert(id: $id, note: $note) {
        id
        isAcknowledged
        acknowledgedBy
        acknowledgedAt
      }
    }
  `,

  DISMISS_ALERT: `
    mutation DismissAlert($id: UUID!) {
      dismissAlert(id: $id)
    }
  `,

  CHECK_MODEL_DRIFT: `
    mutation CheckModelDrift($modelId: UUID!) {
      checkModelDrift(modelId: $modelId) {
        hasDrift
        driftScore
        driftDetails
      }
    }
  `,

  CHECK_MODEL_PERFORMANCE: `
    mutation CheckModelPerformance($modelId: UUID!) {
      checkModelPerformance(modelId: $modelId) {
        isHealthy
        metrics
        issues
      }
    }
  `,

  // ============================================================================
  // Phase 6: ETL Pipeline Mutations
  // ============================================================================
  CREATE_ETL_PIPELINE: `
    mutation CreateEtlPipeline($input: CreateEtlPipelineInput!) {
      createEtlPipeline(input: $input) {
        id
        name
        description
        status
        schedule
        createdAt
      }
    }
  `,

  UPDATE_ETL_PIPELINE: `
    mutation UpdateEtlPipeline($id: UUID!, $input: UpdateEtlPipelineInput!) {
      updateEtlPipeline(id: $id, input: $input) {
        id
        name
        description
        status
        schedule
        updatedAt
      }
    }
  `,

  DELETE_ETL_PIPELINE: `
    mutation DeleteEtlPipeline($id: UUID!) {
      deleteEtlPipeline(id: $id)
    }
  `,

  ADD_ETL_STEP: `
    mutation AddEtlStep($pipelineId: UUID!, $input: CreateEtlStepInput!) {
      addEtlStep(pipelineId: $pipelineId, input: $input) {
        id
        name
        stepType
        stepOrder
        config
        status
      }
    }
  `,

  UPDATE_ETL_STEP: `
    mutation UpdateEtlStep($id: UUID!, $input: UpdateEtlStepInput!) {
      updateEtlStep(id: $id, input: $input) {
        id
        name
        stepType
        stepOrder
        config
        status
      }
    }
  `,

  DELETE_ETL_STEP: `
    mutation DeleteEtlStep($id: UUID!) {
      deleteEtlStep(id: $id)
    }
  `,

  RUN_ETL_PIPELINE: `
    mutation RunEtlPipeline($pipelineId: UUID!, $config: JSON) {
      runEtlPipeline(pipelineId: $pipelineId, config: $config) {
        id
        pipelineId
        status
        startedAt
      }
    }
  `,

  CANCEL_ETL_RUN: `
    mutation CancelEtlRun($runId: UUID!) {
      cancelEtlRun(runId: $runId) {
        id
        status
        completedAt
      }
    }
  `,

  RETRY_ETL_RUN: `
    mutation RetryEtlRun($runId: UUID!, $fromStep: String) {
      retryEtlRun(runId: $runId, fromStep: $fromStep) {
        id
        status
        startedAt
      }
    }
  `,

  // ============================================================================
  // Phase 6: Model Registry Mutations
  // ============================================================================
  REGISTER_MODEL: `
    mutation RegisterModel($input: RegisterModelInput!) {
      registerModel(input: $input) {
        id
        name
        description
        currentStage
        latestVersion
        tags
        createdAt
      }
    }
  `,

  CREATE_MODEL_VERSION: `
    mutation CreateModelVersion($modelId: UUID!, $input: CreateModelVersionInput!) {
      createModelVersion(modelId: $modelId, input: $input) {
        id
        version
        stage
        description
        mlflowRunId
        createdAt
      }
    }
  `,

  PROMOTE_MODEL_VERSION: `
    mutation PromoteModelVersion($modelId: UUID!, $version: String!, $stage: String!) {
      promoteModelVersion(modelId: $modelId, version: $version, stage: $stage) {
        id
        version
        stage
      }
    }
  `,

  ARCHIVE_MODEL_VERSION: `
    mutation ArchiveModelVersion($modelId: UUID!, $version: String!) {
      archiveModelVersion(modelId: $modelId, version: $version) {
        id
        version
        stage
      }
    }
  `,

  DELETE_MODEL_VERSION: `
    mutation DeleteModelVersion($modelId: UUID!, $version: String!) {
      deleteModelVersion(modelId: $modelId, version: $version)
    }
  `,

  UPDATE_MODEL_TAGS: `
    mutation UpdateModelTags($modelId: UUID!, $tags: JSON!) {
      updateModelTags(modelId: $modelId, tags: $tags) {
        id
        tags
      }
    }
  `,

  // ============================================================================
  // Phase 6: Job Scheduler Mutations
  // ============================================================================
  CREATE_SCHEDULED_JOB: `
    mutation CreateScheduledJob($input: CreateScheduledJobInput!) {
      createScheduledJob(input: $input) {
        id
        name
        description
        jobType
        schedule
        scheduleType
        status
        createdAt
      }
    }
  `,

  UPDATE_SCHEDULED_JOB: `
    mutation UpdateScheduledJob($id: UUID!, $input: UpdateScheduledJobInput!) {
      updateScheduledJob(id: $id, input: $input) {
        id
        name
        description
        schedule
        status
        updatedAt
      }
    }
  `,

  DELETE_SCHEDULED_JOB: `
    mutation DeleteScheduledJob($id: UUID!) {
      deleteScheduledJob(id: $id)
    }
  `,

  RUN_JOB_NOW: `
    mutation RunJobNow($jobId: UUID!) {
      runJobNow(jobId: $jobId) {
        id
        jobId
        status
        startedAt
      }
    }
  `,

  PAUSE_JOB: `
    mutation PauseJob($jobId: UUID!) {
      pauseJob(jobId: $jobId) {
        id
        status
      }
    }
  `,

  RESUME_JOB: `
    mutation ResumeJob($jobId: UUID!) {
      resumeJob(jobId: $jobId) {
        id
        status
      }
    }
  `,

  CANCEL_JOB_RUN: `
    mutation CancelJobRun($runId: UUID!) {
      cancelJobRun(runId: $runId) {
        id
        status
        completedAt
      }
    }
  `,

  // ============================================================================
  // Phase 6: Consent Management Mutations
  // ============================================================================
  GRANT_CONSENT: `
    mutation GrantConsent($input: GrantConsentInput!) {
      grantConsent(input: $input) {
        id
        userId
        consentType
        status
        version
        grantedAt
        expiresAt
      }
    }
  `,

  REVOKE_CONSENT: `
    mutation RevokeConsent($id: UUID!, $reason: String) {
      revokeConsent(id: $id, reason: $reason) {
        id
        status
        revokedAt
      }
    }
  `,

  UPDATE_CONSENT: `
    mutation UpdateConsent($id: UUID!, $input: UpdateConsentInput!) {
      updateConsent(id: $id, input: $input) {
        id
        status
        version
      }
    }
  `,

  // ============================================================================
  // Reports Mutations
  // ============================================================================
  CREATE_REPORT: `
    mutation CreateReport($input: CreateReportInput!) {
      createReport(input: $input) {
        id
        name
        description
        reportType
        template
        sections
        availableFormats
        createdAt
        updatedAt
      }
    }
  `,

  UPDATE_REPORT: `
    mutation UpdateReport($id: UUID!, $input: UpdateReportInput!) {
      updateReport(reportId: $id, input: $input) {
        id
        name
        description
        reportType
        template
        sections
        availableFormats
        updatedAt
      }
    }
  `,

  DELETE_REPORT: `
    mutation DeleteReport($id: UUID!) {
      deleteReport(reportId: $id)
    }
  `,

  SCHEDULE_REPORT: `
    mutation ScheduleReport($input: ScheduleReportInput!) {
      scheduleReport(input: $input) {
        id
        name
        isActive
        scheduleType
        scheduleConfig
        timezone
        deliveryMethod
        recipients
        exportFormat
        nextRunAt
        reportId
        createdAt
      }
    }
  `,

  CANCEL_SCHEDULED_REPORT: `
    mutation CancelScheduledReport($id: UUID!) {
      cancelScheduledReport(scheduledId: $id)
    }
  `,

  GENERATE_REPORT: `
    mutation GenerateReport($input: GenerateReportInput!) {
      generateReport(input: $input) {
        success
        message
        exportId
        downloadUrl
      }
    }
  `,

  // ============================================================================
  // Data Connector Mutations
  // ============================================================================
  CREATE_DATA_CONNECTOR: `
    mutation CreateDataConnector($input: CreateDataConnectorInput!) {
      createDataConnector(input: $input) {
        id
        name
        description
        sourceType
        isActive
        createdAt
        updatedAt
      }
    }
  `,

  UPDATE_DATA_CONNECTOR: `
    mutation UpdateDataConnector($id: UUID!, $input: UpdateDataConnectorInput!) {
      updateDataConnector(connectorId: $id, input: $input) {
        id
        name
        description
        sourceType
        isActive
        updatedAt
      }
    }
  `,

  DELETE_DATA_CONNECTOR: `
    mutation DeleteDataConnector($id: UUID!) {
      deleteDataConnector(connectorId: $id)
    }
  `,

  TEST_DATA_CONNECTOR: `
    mutation TestDataConnector($id: UUID!) {
      testDataConnector(connectorId: $id) {
        success
        message
        details
      }
    }
  `,

  SYNC_DATA_CONNECTOR: `
    mutation SyncDataConnector($id: UUID!, $startDate: String, $endDate: String) {
      syncDataConnector(connectorId: $id, startDate: $startDate, endDate: $endDate) {
        success
        message
        recordsSynced
        syncStartedAt
        syncCompletedAt
      }
    }
  `,

  // ============================================================================
  // Geo Experiment Mutations
  // ============================================================================
  CREATE_GEO_EXPERIMENT: `
    mutation CreateGeoExperiment($input: CreateGeoExperimentInput!) {
      createGeoExperiment(input: $input) {
        id
        name
        description
        status
        testRegions
        controlRegions
        holdoutRegions
        startDate
        endDate
        primaryMetric
        createdAt
      }
    }
  `,

  UPDATE_GEO_EXPERIMENT: `
    mutation UpdateGeoExperiment($experimentId: UUID!, $input: UpdateGeoExperimentInput!) {
      updateGeoExperiment(experimentId: $experimentId, input: $input) {
        id
        name
        description
        status
        testRegions
        controlRegions
        updatedAt
      }
    }
  `,

  DELETE_GEO_EXPERIMENT: `
    mutation DeleteGeoExperiment($experimentId: UUID!) {
      deleteGeoExperiment(experimentId: $experimentId)
    }
  `,

  START_GEO_EXPERIMENT: `
    mutation StartGeoExperiment($experimentId: UUID!) {
      startGeoExperiment(experimentId: $experimentId) {
        id
        status
      }
    }
  `,

  COMPLETE_GEO_EXPERIMENT: `
    mutation CompleteGeoExperiment($experimentId: UUID!) {
      completeGeoExperiment(experimentId: $experimentId) {
        id
        status
        completedAt
      }
    }
  `,

  ARCHIVE_GEO_EXPERIMENT: `
    mutation ArchiveGeoExperiment($experimentId: UUID!) {
      archiveGeoExperiment(experimentId: $experimentId) {
        id
        status
      }
    }
  `,

  MARK_EXPERIMENT_READY: `
    mutation MarkExperimentReady($experimentId: UUID!) {
      markExperimentReady(experimentId: $experimentId) {
        id
        status
      }
    }
  `,

  RUN_POWER_ANALYSIS: `
    mutation RunPowerAnalysis($input: RunPowerAnalysisInput!) {
      runPowerAnalysis(input: $input) {
        requiredSampleSize
        estimatedPower
        minimumDetectableEffect
        confidenceLevel
        testRegionsCount
        controlRegionsCount
        recommendations
      }
    }
  `,

  ANALYZE_GEO_EXPERIMENT: `
    mutation AnalyzeGeoExperiment($experimentId: UUID!) {
      analyzeGeoExperiment(experimentId: $experimentId) {
        experimentId
        absoluteLift
        relativeLift
        pValue
        confidenceIntervalLower
        confidenceIntervalUpper
        isSignificant
        testMetricValue
        controlMetricValue
        regionLevelResults
        timeSeriesComparison
        diagnostics
      }
    }
  `,
}

// ============================================================================
// Type Definitions for GraphQL Responses
// ============================================================================

export interface UserType {
  id: string
  email: string
  firstName?: string
  lastName?: string
  fullName: string
  isActive: boolean
  isVerified: boolean
  isSuperuser: boolean
  organization?: OrganizationType
  roles: RoleType[]
  createdAt: string
  updatedAt: string
}

export interface RoleType {
  id: string
  name: string
  description?: string
}

export interface OrganizationType {
  id: string
  name: string
  slug: string
  description?: string
  isActive: boolean
  subscriptionTier: string
  maxUsers: number
  maxModels: number
  maxDatasets: number
  createdAt: string
  updatedAt: string
}

export interface ModelType {
  id: string
  name: string
  description?: string
  modelType: string
  status: string
  config?: Record<string, unknown>
  hyperparameters?: Record<string, unknown>
  versions: ModelVersionType[]
  parameters?: ModelParameterType[]
  adstockConfigs?: AdstockConfigType[]
  saturationConfigs?: SaturationConfigType[]
  createdAt: string
  updatedAt: string
}

export interface ModelVersionType {
  id: string
  version: string
  description?: string
  isCurrent: boolean
  status: string
  trainingDurationSeconds?: number
  mlflowRunId?: string
  metrics?: Record<string, unknown>
  createdAt: string
}

export interface ModelParameterType {
  id: string
  parameterName: string
  parameterType: string
  value?: number
  stdError?: number
  ciLower?: number
  ciUpper?: number
  posteriorMean?: number
  posteriorStd?: number
}

export interface AdstockConfigType {
  id: string
  channelName: string
  adstockType: string
  decayRate?: number
  shape?: number
  scale?: number
  maxLag: number
  normalize: boolean
  fittedParams?: Record<string, unknown>
}

export interface SaturationConfigType {
  id: string
  channelName: string
  saturationType: string
  alpha?: number
  gamma?: number
  k?: number
  m?: number
  vmax?: number
  km?: number
  fittedParams?: Record<string, unknown>
}

export interface ExperimentType {
  id: string
  name: string
  description?: string
  status: string
  mlflowExperimentId?: string
  config?: Record<string, unknown>
  runs: ExperimentRunType[]
  createdAt: string
  updatedAt: string
}

export interface ExperimentRunType {
  id: string
  runName?: string
  status: string
  mlflowRunId?: string
  parameters?: Record<string, unknown>
  hyperparameters?: Record<string, unknown>
  metrics?: Record<string, unknown>
  durationSeconds?: number
  createdAt: string
}

export interface PredictionResult {
  modelId: string
  modelVersion: string
  predictions: unknown[]
  contributionByChannel?: Record<string, unknown>
  confidenceIntervals?: Record<string, unknown>
}

export interface DecompositionResult {
  modelId: string
  modelVersion: string
  totalContribution: number
  baselineContribution: number
  channelContributions: Record<string, unknown>
  timeSeriesDecomposition?: unknown[]
}

// ============================================================================
// Phase 6: Monitoring Types
// ============================================================================

export interface AlertType {
  id: string
  alertType: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  message: string
  modelId?: string
  metricName?: string
  currentValue?: number
  threshold?: number
  isAcknowledged: boolean
  acknowledgedBy?: string
  acknowledgedAt?: string
  createdAt: string
}

export interface MonitorConfigType {
  id: string
  modelId: string
  metricName: string
  alertType: string
  threshold: number
  windowSize: number
  checkFrequency: number
  isActive: boolean
  lastChecked?: string
  createdAt: string
}

export interface MonitoringSummaryType {
  totalAlerts: number
  criticalAlerts: number
  warningAlerts: number
  infoAlerts: number
  acknowledgedAlerts: number
  activeMonitors: number
  lastCheckTime?: string
}

export interface MetricHistoryPoint {
  timestamp: string
  value: number
  metricName: string
}

export interface DriftCheckResult {
  hasDrift: boolean
  driftScore: number
  driftDetails?: Record<string, unknown>
}

export interface PerformanceCheckResult {
  isHealthy: boolean
  metrics: Record<string, number>
  issues: string[]
}

// ============================================================================
// Phase 6: ETL Pipeline Types
// ============================================================================

export interface EtlPipelineType {
  id: string
  name: string
  description?: string
  status: 'active' | 'inactive' | 'running' | 'failed'
  schedule?: string
  config?: Record<string, unknown>
  lastRunAt?: string
  nextRunAt?: string
  steps?: EtlStepType[]
  createdAt: string
  updatedAt: string
}

export interface EtlStepType {
  id: string
  name: string
  stepType: 'extract' | 'transform' | 'load' | 'validate'
  stepOrder: number
  config?: Record<string, unknown>
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
}

export interface EtlPipelineRunType {
  id: string
  pipelineId: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  startedAt: string
  completedAt?: string
  error?: string
  metrics?: Record<string, unknown>
  stepResults?: EtlStepResultType[]
}

export interface EtlStepResultType {
  stepId: string
  status: string
  startedAt: string
  completedAt?: string
  error?: string
  outputMetrics?: Record<string, unknown>
}

// ============================================================================
// Phase 6: Model Registry Types
// ============================================================================

export interface RegisteredModelType {
  id: string
  name: string
  description?: string
  currentStage: 'development' | 'staging' | 'production' | 'archived'
  latestVersion: string
  tags?: Record<string, string>
  versions?: RegistryModelVersionType[]
  createdAt: string
  updatedAt: string
}

export interface RegistryModelVersionType {
  id: string
  version: string
  stage: 'development' | 'staging' | 'production' | 'archived'
  description?: string
  mlflowRunId?: string
  metrics?: Record<string, number>
  artifactPath?: string
  createdAt: string
}

export interface ModelVersionComparisonType {
  versions: RegistryModelVersionType[]
  metricDiffs: Record<string, number>
}

// ============================================================================
// Phase 6: Job Scheduler Types
// ============================================================================

export interface ScheduledJobType {
  id: string
  name: string
  description?: string
  jobType: string
  schedule: string
  scheduleType: 'cron' | 'interval' | 'once'
  status: 'active' | 'paused' | 'completed' | 'failed'
  lastRunAt?: string
  nextRunAt?: string
  config?: Record<string, unknown>
  runs?: JobRunType[]
  createdAt: string
  updatedAt: string
}

export interface JobRunType {
  id: string
  jobId: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  startedAt: string
  completedAt?: string
  error?: string
  output?: Record<string, unknown>
}

export interface SchedulerStatusType {
  isRunning: boolean
  activeJobs: number
  pendingJobs: number
  failedJobs: number
  lastHeartbeat?: string
}

// ============================================================================
// Phase 6: Data Versioning Types
// ============================================================================

export interface DataVersionType {
  id: string
  datasetId: string
  version: string
  description?: string
  rowCount: number
  columnCount: number
  schema?: Record<string, unknown>
  checksum: string
  storagePath?: string
  createdBy?: string
  createdAt: string
}

export interface DataVersionComparisonType {
  addedRows: number
  removedRows: number
  modifiedRows: number
  schemaChanges?: Record<string, unknown>
}

// ============================================================================
// Phase 6: Consent Management Types
// ============================================================================

export interface ConsentRecordType {
  id: string
  userId: string
  consentType: string
  status: 'granted' | 'revoked' | 'expired' | 'pending'
  version: string
  consentText?: string
  grantedAt: string
  expiresAt?: string
  revokedAt?: string
  ipAddress?: string
  metadata?: Record<string, unknown>
}

export interface UserConsentStatusType {
  userId: string
  consents: {
    consentType: string
    status: string
    version: string
    grantedAt: string
    expiresAt?: string
  }[]
}

// ============================================================================
// Reports Types
// ============================================================================

export interface ReportTemplateType {
  id: string
  name: string
  description?: string
  reportType: string
  template?: Record<string, unknown>
  sections?: string[]
  availableFormats: string[]
  createdAt: string
  updatedAt: string
}

export interface ScheduledReportItemType {
  id: string
  name: string
  isActive: boolean
  scheduleType: 'daily' | 'weekly' | 'monthly'
  scheduleConfig?: Record<string, unknown>
  timezone: string
  deliveryMethod: string
  deliveryConfig?: Record<string, unknown>
  recipients: string[]
  exportFormat: string
  lastRunAt?: string
  lastRunStatus?: string
  nextRunAt?: string
  reportId: string
  createdAt: string
  updatedAt: string
}

export interface ExportItemType {
  id: string
  exportType: string
  exportFormat: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  filePath?: string
  fileSizeBytes?: number
  downloadUrl?: string
  expiresAt?: string
  errorMessage?: string
  createdAt: string
  updatedAt: string
}

export interface GenerateReportResultType {
  success: boolean
  message: string
  exportId?: string
  downloadUrl?: string
}

// ============================================================================
// Data Connector Types
// ============================================================================

export interface DataConnectorType {
  id: string
  name: string
  description?: string
  sourceType: string
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface ConnectionTestResultType {
  success: boolean
  message: string
  details?: Record<string, unknown>
}

export interface SyncResultType {
  success: boolean
  message: string
  recordsSynced?: number
  syncStartedAt?: string
  syncCompletedAt?: string
}

export interface ConnectorTypeInfo {
  id: string
  name: string
  category: string
  description: string
  requiredFields: string[]
}

// ============================================================================
// Geo Experiment Types
// ============================================================================

export interface GeoExperimentType {
  id: string
  name: string
  description?: string
  status: 'draft' | 'designing' | 'ready' | 'running' | 'completed' | 'analyzed' | 'archived'
  testRegions: string[]
  controlRegions: string[]
  holdoutRegions?: string[]
  startDate?: string
  endDate?: string
  warmupDays?: number
  powerAnalysis?: Record<string, unknown>
  minimumDetectableEffect?: number
  targetPower?: number
  results?: Record<string, unknown>
  absoluteLift?: number
  relativeLift?: number
  pValue?: number
  confidenceIntervalLower?: number
  confidenceIntervalUpper?: number
  primaryMetric?: string
  secondaryMetrics?: string[]
  organizationId: string
  createdById?: string
  createdAt: string
  updatedAt: string
  completedAt?: string
}

export interface PowerAnalysisResultType {
  requiredSampleSize: number
  estimatedPower: number
  minimumDetectableEffect: number
  confidenceLevel: number
  testRegionsCount: number
  controlRegionsCount: number
  recommendations: string[]
}

export interface GeoExperimentResultType {
  experimentId: string
  absoluteLift: number
  relativeLift: number
  pValue: number
  confidenceIntervalLower: number
  confidenceIntervalUpper: number
  isSignificant: boolean
  testMetricValue: number
  controlMetricValue: number
  regionLevelResults?: Record<string, unknown>
  timeSeriesComparison?: Record<string, unknown>
  diagnostics?: Record<string, unknown>
}

export interface CreateGeoExperimentInput {
  name: string
  description?: string
  testRegions: string[]
  controlRegions: string[]
  holdoutRegions?: string[]
  startDate?: string
  endDate?: string
  warmupDays?: number
  minimumDetectableEffect?: number
  targetPower?: number
  primaryMetric?: string
  secondaryMetrics?: string[]
}

export interface RunPowerAnalysisInput {
  experimentId: string
  expectedEffectSize?: number
  significanceLevel?: number
}
