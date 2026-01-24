/**
 * Data Preprocessing API Hooks
 *
 * Hooks for data quality assessment, schema inference,
 * data cleaning, and feature selection
 */

import { useState, useCallback } from 'react'
import { graphqlRequest } from '@/lib/graphql'

// ============================================================================
// Types
// ============================================================================

export interface QualityDimension {
  name: string
  score: number
  status: 'good' | 'warning' | 'critical'
}

export interface ColumnQualityScore {
  columnName: string
  completenessScore: number
  accuracyScore: number
  consistencyScore: number
  validityScore: number
  overallScore: number
  issues: string[]
  recommendations: string[]
  statistics: Record<string, unknown>
}

export interface DataQualityReport {
  overallScore: number
  grade: string
  dimensionScores: Record<string, number>
  columnScores: ColumnQualityScore[]
  summary: Record<string, unknown>
  issues: Array<{
    dimension: string
    severity: string
    column: string | null
    message: string
    metricValue: number
  }>
  recommendations: string[]
  profilingStats: Record<string, unknown>
  createdAt: string
}

export interface ColumnSchema {
  name: string
  dataType: string
  semanticType: string
  nullable: boolean
  unique: boolean
  sampleValues: string[]
  statistics: Record<string, unknown>
  formatPattern: string | null
  recommendedTransformations: string[]
  confidence: number
}

export interface InferredSchema {
  columns: ColumnSchema[]
  rowCount: number
  detectedDelimiter: string | null
  detectedEncoding: string
  hasHeader: boolean
  dateColumns: string[]
  numericColumns: string[]
  categoricalColumns: string[]
  idColumns: string[]
  targetColumnCandidates: string[]
  recommendations: string[]
}

export interface CleaningResult {
  action: string
  column: string | null
  rowsAffected: number
  details: Record<string, unknown>
  beforeSample: string[]
  afterSample: string[]
}

export interface CleaningReport {
  originalRows: number
  finalRows: number
  originalColumns: number
  finalColumns: number
  actionsPerformed: CleaningResult[]
  totalChanges: number
  warnings: string[]
  recommendations: string[]
}

export interface FeatureScore {
  name: string
  score: number
  rank: number
  selected: boolean
  method: string
  statistics: Record<string, unknown>
  correlations: Record<string, number>
  recommendation: string
}

export interface FeatureSelectionResult {
  selectedFeatures: string[]
  removedFeatures: string[]
  featureScores: FeatureScore[]
  correlationMatrix: Record<string, Record<string, number>>
  highCorrelations: Array<{
    feature1: string
    feature2: string
    correlation: number
  }>
  multicollinearGroups: string[][]
  recommendations: string[]
  summary: Record<string, unknown>
}

// ============================================================================
// GraphQL Queries
// ============================================================================

const DATA_QUALITY_REPORT_QUERY = `
  query DataQualityReport($datasetId: ID!, $dateColumn: String, $freshnessThresholdDays: Int) {
    dataQualityReport(
      datasetId: $datasetId
      dateColumn: $dateColumn
      freshnessThresholdDays: $freshnessThresholdDays
    ) {
      overallScore
      grade
      dimensionScores
      columnScores {
        columnName
        completenessScore
        accuracyScore
        consistencyScore
        validityScore
        overallScore
        issues
        recommendations
        statistics
      }
      summary
      issues {
        dimension
        severity
        column
        message
        metricValue
      }
      recommendations
      profilingStats
      createdAt
    }
  }
`

const INFERRED_SCHEMA_QUERY = `
  query InferredSchema($datasetId: ID!, $sampleSize: Int) {
    inferredSchema(datasetId: $datasetId, sampleSize: $sampleSize) {
      columns {
        name
        dataType
        semanticType
        nullable
        unique
        sampleValues
        statistics
        formatPattern
        recommendedTransformations
        confidence
      }
      rowCount
      detectedDelimiter
      detectedEncoding
      hasHeader
      dateColumns
      numericColumns
      categoricalColumns
      idColumns
      targetColumnCandidates
      recommendations
    }
  }
`

const FEATURE_SELECTION_QUERY = `
  query FeatureSelectionResult($datasetId: ID!, $targetColumn: String, $method: String, $correlationThreshold: Float) {
    featureSelectionResult(
      datasetId: $datasetId
      targetColumn: $targetColumn
      method: $method
      correlationThreshold: $correlationThreshold
    ) {
      selectedFeatures
      removedFeatures
      featureScores {
        name
        score
        rank
        selected
        method
        statistics
        correlations
        recommendation
      }
      correlationMatrix
      highCorrelations {
        feature1
        feature2
        correlation
      }
      multicollinearGroups
      recommendations
      summary
    }
  }
`

const FEATURE_IMPORTANCE_QUERY = `
  query FeatureImportance($datasetId: ID!, $targetColumn: String!, $method: String) {
    featureImportance(datasetId: $datasetId, targetColumn: $targetColumn, method: $method) {
      name
      score
      rank
      selected
      method
      statistics
      correlations
      recommendation
    }
  }
`

// ============================================================================
// GraphQL Mutations
// ============================================================================

const ASSESS_DATA_QUALITY_MUTATION = `
  mutation AssessDataQuality($datasetId: ID!, $dateColumn: String, $freshnessThresholdDays: Int) {
    assessDataQuality(
      datasetId: $datasetId
      dateColumn: $dateColumn
      freshnessThresholdDays: $freshnessThresholdDays
    ) {
      overallScore
      grade
      dimensionScores
      columnScores {
        columnName
        completenessScore
        accuracyScore
        consistencyScore
        validityScore
        overallScore
        issues
        recommendations
        statistics
      }
      summary
      issues {
        dimension
        severity
        column
        message
        metricValue
      }
      recommendations
      profilingStats
      createdAt
    }
  }
`

const INFER_SCHEMA_MUTATION = `
  mutation InferSchema($datasetId: ID!, $sampleSize: Int) {
    inferSchema(datasetId: $datasetId, sampleSize: $sampleSize) {
      columns {
        name
        dataType
        semanticType
        nullable
        unique
        sampleValues
        statistics
        formatPattern
        recommendedTransformations
        confidence
      }
      rowCount
      detectedDelimiter
      detectedEncoding
      hasHeader
      dateColumns
      numericColumns
      categoricalColumns
      idColumns
      targetColumnCandidates
      recommendations
    }
  }
`

const CLEAN_DATASET_MUTATION = `
  mutation CleanDataset($input: DataCleaningInput!) {
    cleanDataset(input: $input) {
      originalRows
      finalRows
      originalColumns
      finalColumns
      actionsPerformed {
        action
        column
        rowsAffected
        details
        beforeSample
        afterSample
      }
      totalChanges
      warnings
      recommendations
    }
  }
`

const SELECT_FEATURES_MUTATION = `
  mutation SelectFeatures($input: FeatureSelectionInput!) {
    selectFeatures(input: $input) {
      selectedFeatures
      removedFeatures
      featureScores {
        name
        score
        rank
        selected
        method
        statistics
        correlations
        recommendation
      }
      correlationMatrix
      highCorrelations {
        feature1
        feature2
        correlation
      }
      multicollinearGroups
      recommendations
      summary
    }
  }
`

const IMPUTE_MISSING_VALUES_MUTATION = `
  mutation ImputeMissingValues($datasetId: ID!, $column: String!, $strategy: ImputationStrategyType!, $fillValue: String) {
    imputeMissingValues(datasetId: $datasetId, column: $column, strategy: $strategy, fillValue: $fillValue) {
      action
      column
      rowsAffected
      details
      beforeSample
      afterSample
    }
  }
`

const HANDLE_OUTLIERS_MUTATION = `
  mutation HandleOutliers($datasetId: ID!, $column: String!, $strategy: OutlierStrategyType!, $threshold: Float) {
    handleOutliers(datasetId: $datasetId, column: $column, strategy: $strategy, threshold: $threshold) {
      action
      column
      rowsAffected
      details
      beforeSample
      afterSample
    }
  }
`

// ============================================================================
// Hooks
// ============================================================================

export function useDataQualityReport(datasetId?: string) {
  const [report, setReport] = useState<DataQualityReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchReport = useCallback(async (
    id?: string,
    dateColumn?: string,
    freshnessThresholdDays: number = 7
  ) => {
    const targetId = id || datasetId
    if (!targetId) return

    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ dataQualityReport: DataQualityReport }>(
        DATA_QUALITY_REPORT_QUERY,
        { datasetId: targetId, dateColumn, freshnessThresholdDays }
      )
      setReport(data.dataQualityReport)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch quality report')
    } finally {
      setLoading(false)
    }
  }, [datasetId])

  return { report, loading, error, fetchReport }
}

export function useInferredSchema(datasetId?: string) {
  const [schema, setSchema] = useState<InferredSchema | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSchema = useCallback(async (id?: string, sampleSize: number = 10000) => {
    const targetId = id || datasetId
    if (!targetId) return

    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ inferredSchema: InferredSchema }>(
        INFERRED_SCHEMA_QUERY,
        { datasetId: targetId, sampleSize }
      )
      setSchema(data.inferredSchema)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch schema')
    } finally {
      setLoading(false)
    }
  }, [datasetId])

  return { schema, loading, error, fetchSchema }
}

export function useFeatureSelection(datasetId?: string) {
  const [result, setResult] = useState<FeatureSelectionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchFeatureSelection = useCallback(async (
    id?: string,
    targetColumn?: string,
    method: string = 'combined',
    correlationThreshold: number = 0.8
  ) => {
    const targetId = id || datasetId
    if (!targetId) return

    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ featureSelectionResult: FeatureSelectionResult }>(
        FEATURE_SELECTION_QUERY,
        { datasetId: targetId, targetColumn, method, correlationThreshold }
      )
      setResult(data.featureSelectionResult)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch feature selection')
    } finally {
      setLoading(false)
    }
  }, [datasetId])

  return { result, loading, error, fetchFeatureSelection }
}

export function useFeatureImportance() {
  const [scores, setScores] = useState<FeatureScore[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const calculateImportance = useCallback(async (
    datasetId: string,
    targetColumn: string,
    method: string = 'random_forest'
  ) => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ featureImportance: FeatureScore[] }>(
        FEATURE_IMPORTANCE_QUERY,
        { datasetId, targetColumn, method }
      )
      setScores(data.featureImportance)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to calculate feature importance')
    } finally {
      setLoading(false)
    }
  }, [])

  return { scores, loading, error, calculateImportance }
}

// ============================================================================
// Mutation Hooks
// ============================================================================

export function useAssessDataQuality() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const assessQuality = useCallback(async (
    datasetId: string,
    dateColumn?: string,
    freshnessThresholdDays: number = 7
  ): Promise<DataQualityReport | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ assessDataQuality: DataQualityReport }>(
        ASSESS_DATA_QUALITY_MUTATION,
        { datasetId, dateColumn, freshnessThresholdDays }
      )
      return data.assessDataQuality
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assess data quality')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { assessQuality, loading, error }
}

export function useInferSchema() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const inferSchema = useCallback(async (
    datasetId: string,
    sampleSize: number = 10000
  ): Promise<InferredSchema | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ inferSchema: InferredSchema }>(
        INFER_SCHEMA_MUTATION,
        { datasetId, sampleSize }
      )
      return data.inferSchema
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to infer schema')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { inferSchema, loading, error }
}

export interface CleaningConfig {
  datasetId: string
  standardizeNulls?: boolean
  trimWhitespace?: boolean
  removeDuplicates?: boolean
  duplicateSubset?: string[]
  normalizeCaseColumns?: string[]
  caseStyle?: string
  outlierConfigs?: Array<{
    column: string
    strategy: string
    threshold: number
  }>
  imputeConfigs?: Array<{
    column: string
    strategy: string
    fillValue?: string
  }>
  normalizePhones?: boolean
  phoneColumns?: string[]
  normalizeEmails?: boolean
  emailColumns?: string[]
}

export function useCleanDataset() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const cleanDataset = useCallback(async (config: CleaningConfig): Promise<CleaningReport | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ cleanDataset: CleaningReport }>(
        CLEAN_DATASET_MUTATION,
        { input: config }
      )
      return data.cleanDataset
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clean dataset')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { cleanDataset, loading, error }
}

export interface FeatureSelectionConfig {
  datasetId: string
  targetColumn?: string
  method?: string
  correlationMethod?: string
  correlationThreshold?: number
  varianceThreshold?: number
  maxFeatures?: number
}

export function useSelectFeatures() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectFeatures = useCallback(async (config: FeatureSelectionConfig): Promise<FeatureSelectionResult | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ selectFeatures: FeatureSelectionResult }>(
        SELECT_FEATURES_MUTATION,
        { input: config }
      )
      return data.selectFeatures
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to select features')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { selectFeatures, loading, error }
}

export function useImputeMissingValues() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const imputeMissing = useCallback(async (
    datasetId: string,
    column: string,
    strategy: string,
    fillValue?: string
  ): Promise<CleaningResult | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ imputeMissingValues: CleaningResult }>(
        IMPUTE_MISSING_VALUES_MUTATION,
        { datasetId, column, strategy, fillValue }
      )
      return data.imputeMissingValues
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to impute missing values')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { imputeMissing, loading, error }
}

export function useHandleOutliers() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleOutliers = useCallback(async (
    datasetId: string,
    column: string,
    strategy: string,
    threshold: number = 3.0
  ): Promise<CleaningResult | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ handleOutliers: CleaningResult }>(
        HANDLE_OUTLIERS_MUTATION,
        { datasetId, column, strategy, threshold }
      )
      return data.handleOutliers
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to handle outliers')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { handleOutliers, loading, error }
}
