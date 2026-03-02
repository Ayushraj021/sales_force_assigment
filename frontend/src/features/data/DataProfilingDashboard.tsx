import { useState, useEffect, useCallback } from 'react'
import {
  ChartBarIcon,
  TableCellsIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  FunnelIcon,
  BeakerIcon,
  SparklesIcon,
  DocumentMagnifyingGlassIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import {
  useDataQualityReport,
  useInferredSchema,
  useFeatureSelection,
  useAssessDataQuality,
  useInferSchema,
  useCleanDataset,
  useSelectFeatures,
  type DataQualityReport,
  type InferredSchema,
  type FeatureSelectionResult,
  type CleaningConfig,
} from '@/hooks/useDataPreprocessing'

interface QualityDimension {
  name: string
  score: number
  status: 'good' | 'warning' | 'critical'
}

interface ColumnProfile {
  name: string
  dataType: string
  semanticType: string
  nullPercentage: number
  uniquePercentage: number
  overallScore: number
  issues: string[]
  recommendations: string[]
}

interface DisplayQualityReport {
  overallScore: number
  grade: string
  dimensions: QualityDimension[]
  columns: ColumnProfile[]
  totalRows: number
  totalColumns: number
  missingPercentage: number
  duplicateRows: number
  recommendations: string[]
}

interface FeatureScore {
  name: string
  score: number
  rank: number
  selected: boolean
  importance: number
  correlation: number
}

// Cleaning configuration state
interface CleaningOptions {
  standardizeNulls: boolean
  trimWhitespace: boolean
  removeDuplicates: boolean
  handleOutliers: boolean
  normalizeCase: boolean
  fixEncoding: boolean
  numericImputation: string
  categoricalImputation: string
  dateImputation: string
  outlierStrategy: string
  outlierMethod: string
}

// Transform API response to display format
function transformQualityReport(report: DataQualityReport | null): DisplayQualityReport | null {
  if (!report) return null

  const dimensionNames = ['completeness', 'accuracy', 'consistency', 'validity', 'uniqueness', 'timeliness']
  const dimensions: QualityDimension[] = dimensionNames.map(name => {
    const score = report.dimensionScores?.[name] ?? 0
    return {
      name: name.charAt(0).toUpperCase() + name.slice(1),
      score: Math.round(score * 100) / 100,
      status: score >= 90 ? 'good' : score >= 70 ? 'warning' : 'critical'
    }
  })

  const columns: ColumnProfile[] = (report.columnScores || []).map(col => ({
    name: col.columnName,
    dataType: (col.statistics as Record<string, unknown>)?.dataType as string || 'unknown',
    semanticType: (col.statistics as Record<string, unknown>)?.semanticType as string || 'UNKNOWN',
    nullPercentage: Math.round((100 - col.completenessScore) * 100) / 100,
    uniquePercentage: Math.round(((col.statistics as Record<string, unknown>)?.uniquePercentage as number || 0) * 100) / 100,
    overallScore: Math.round(col.overallScore * 100) / 100,
    issues: col.issues || [],
    recommendations: col.recommendations || []
  }))

  const summary = report.summary as Record<string, unknown> || {}

  return {
    overallScore: Math.round(report.overallScore * 100) / 100,
    grade: report.grade,
    dimensions,
    columns,
    totalRows: (summary.totalRows as number) || 0,
    totalColumns: columns.length,
    missingPercentage: Math.round(((summary.missingPercentage as number) || 0) * 100) / 100,
    duplicateRows: (summary.duplicateRows as number) || 0,
    recommendations: report.recommendations || []
  }
}

// Transform feature selection result to display format
function transformFeatureScores(result: FeatureSelectionResult | null): FeatureScore[] {
  if (!result || !result.featureScores) return []

  return result.featureScores.map(feat => ({
    name: feat.name,
    score: feat.score,
    rank: feat.rank,
    selected: feat.selected,
    importance: (feat.statistics as Record<string, unknown>)?.importance as number || feat.score,
    correlation: feat.correlations?.target || Object.values(feat.correlations || {})[0] || 0
  }))
}

export function DataProfilingDashboard() {
  const [activeTab, setActiveTab] = useState<'quality' | 'schema' | 'features' | 'cleaning'>('quality')
  const [selectedDataset, setSelectedDataset] = useState<string>('sales_data_2024')
  const [availableDatasets] = useState<string[]>(['sales_data_2024', 'marketing_spend', 'customer_data'])

  // Cleaning options state
  const [cleaningOptions, setCleaningOptions] = useState<CleaningOptions>({
    standardizeNulls: true,
    trimWhitespace: true,
    removeDuplicates: true,
    handleOutliers: true,
    normalizeCase: false,
    fixEncoding: false,
    numericImputation: 'median',
    categoricalImputation: 'mode',
    dateImputation: 'forward_fill',
    outlierStrategy: 'cap',
    outlierMethod: 'zscore'
  })

  // API hooks
  const { report: apiQualityReport, loading: qualityLoading, error: qualityError, fetchReport } = useDataQualityReport()
  const { schema: apiSchema, loading: schemaLoading, error: schemaError, fetchSchema } = useInferredSchema()
  const { result: featureResult, loading: featureLoading, error: featureError, fetchFeatureSelection } = useFeatureSelection()
  const { assessQuality, loading: assessLoading, error: assessError } = useAssessDataQuality()
  const { inferSchema, loading: inferLoading, error: inferError } = useInferSchema()
  const { cleanDataset, loading: cleanLoading, error: cleanError } = useCleanDataset()
  const { selectFeatures, loading: selectLoading, error: selectError } = useSelectFeatures()

  // Transform API data for display
  const qualityReport = transformQualityReport(apiQualityReport)
  const featureScores = transformFeatureScores(featureResult)

  // Loading state
  const loading = qualityLoading || schemaLoading || featureLoading || assessLoading || inferLoading || cleanLoading || selectLoading

  // Load initial data
  useEffect(() => {
    if (selectedDataset) {
      fetchReport(selectedDataset)
      fetchSchema(selectedDataset)
      fetchFeatureSelection(selectedDataset)
    }
  }, [selectedDataset, fetchReport, fetchSchema, fetchFeatureSelection])

  // Show errors as toasts
  useEffect(() => {
    if (qualityError) toast.error(qualityError)
    if (schemaError) toast.error(schemaError)
    if (featureError) toast.error(featureError)
    if (assessError) toast.error(assessError)
    if (inferError) toast.error(inferError)
    if (cleanError) toast.error(cleanError)
    if (selectError) toast.error(selectError)
  }, [qualityError, schemaError, featureError, assessError, inferError, cleanError, selectError])

  const handleRefresh = useCallback(async () => {
    await Promise.all([
      fetchReport(selectedDataset),
      fetchSchema(selectedDataset),
      fetchFeatureSelection(selectedDataset)
    ])
    toast.success('Data profile refreshed')
  }, [selectedDataset, fetchReport, fetchSchema, fetchFeatureSelection])

  const handleRunQualityAssessment = useCallback(async () => {
    const result = await assessQuality(selectedDataset)
    if (result) {
      toast.success('Quality assessment completed')
      await fetchReport(selectedDataset)
    }
  }, [selectedDataset, assessQuality, fetchReport])

  const handleInferSchema = useCallback(async () => {
    const result = await inferSchema(selectedDataset)
    if (result) {
      toast.success('Schema inference completed')
      await fetchSchema(selectedDataset)
    }
  }, [selectedDataset, inferSchema, fetchSchema])

  const handleSelectFeatures = useCallback(async () => {
    const result = await selectFeatures({
      datasetId: selectedDataset,
      method: 'combined',
      correlationThreshold: 0.8
    })
    if (result) {
      toast.success(`Feature selection completed: ${result.selectedFeatures.length} features selected`)
      await fetchFeatureSelection(selectedDataset)
    }
  }, [selectedDataset, selectFeatures, fetchFeatureSelection])

  const handleCleanData = useCallback(async () => {
    const config: CleaningConfig = {
      datasetId: selectedDataset,
      standardizeNulls: cleaningOptions.standardizeNulls,
      trimWhitespace: cleaningOptions.trimWhitespace,
      removeDuplicates: cleaningOptions.removeDuplicates,
      normalizeCaseColumns: cleaningOptions.normalizeCase ? [] : undefined, // Apply to all if enabled
      caseStyle: 'lower',
      outlierConfigs: cleaningOptions.handleOutliers ? [
        {
          column: '*',
          strategy: cleaningOptions.outlierStrategy,
          threshold: cleaningOptions.outlierMethod === 'zscore' ? 3.0 : 1.5
        }
      ] : undefined
    }

    const result = await cleanDataset(config)
    if (result) {
      toast.success(`Data cleaning completed: ${result.totalChanges} changes made`)
      // Refresh quality report to show improved scores
      await fetchReport(selectedDataset)
    }
  }, [selectedDataset, cleaningOptions, cleanDataset, fetchReport])

  const handleDatasetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedDataset(e.target.value)
  }

  const handleCleaningOptionChange = (option: keyof CleaningOptions, value: boolean | string) => {
    setCleaningOptions(prev => ({ ...prev, [option]: value }))
  }

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case 'A': return 'text-green-600 bg-green-100'
      case 'B': return 'text-blue-600 bg-blue-100'
      case 'C': return 'text-yellow-600 bg-yellow-100'
      case 'D': return 'text-orange-600 bg-orange-100'
      case 'F': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600'
    if (score >= 70) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getStatusIcon = (status: 'good' | 'warning' | 'critical') => {
    switch (status) {
      case 'good':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
      case 'critical':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
    }
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Profiling & Quality</h1>
          <p className="mt-1 text-sm text-gray-600">
            Analyze, clean, and prepare your data for modeling
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <select
            value={selectedDataset}
            className="text-sm border-gray-300 rounded-md"
            onChange={handleDatasetChange}
          >
            {availableDatasets.map(ds => (
              <option key={ds} value={ds}>{ds}</option>
            ))}
          </select>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="btn btn-outline"
          >
            <ArrowPathIcon className={`h-5 w-5 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'quality', name: 'Data Quality', icon: ChartBarIcon },
            { id: 'schema', name: 'Schema & Types', icon: TableCellsIcon },
            { id: 'features', name: 'Feature Selection', icon: FunnelIcon },
            { id: 'cleaning', name: 'Data Cleaning', icon: SparklesIcon },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`
                flex items-center py-4 px-1 border-b-2 font-medium text-sm
                ${activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              <tab.icon className="h-5 w-5 mr-2" />
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Quality Tab */}
      {activeTab === 'quality' && (
        <div className="space-y-6">
          {/* Loading State */}
          {qualityLoading && (
            <div className="bg-white shadow rounded-lg p-6 flex items-center justify-center">
              <ArrowPathIcon className="h-8 w-8 animate-spin text-blue-500 mr-3" />
              <span className="text-gray-600">Loading quality report...</span>
            </div>
          )}

          {/* Overall Score Card */}
          {!qualityLoading && (
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-medium text-gray-900">Overall Data Quality</h2>
                  <p className="text-sm text-gray-500">Dataset: {selectedDataset}</p>
                </div>
                <div className="text-center">
                  <div className={`text-4xl font-bold ${getScoreColor(qualityReport?.overallScore ?? 0)}`}>
                    {qualityReport?.overallScore ?? 'N/A'}%
                  </div>
                  <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getGradeColor(qualityReport?.grade ?? 'N/A')}`}>
                    Grade {qualityReport?.grade ?? 'N/A'}
                  </span>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-4 gap-4 text-center">
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-2xl font-semibold">{(qualityReport?.totalRows ?? 0).toLocaleString()}</div>
                  <div className="text-sm text-gray-500">Total Rows</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-2xl font-semibold">{qualityReport?.totalColumns ?? 0}</div>
                  <div className="text-sm text-gray-500">Columns</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-2xl font-semibold text-yellow-600">{qualityReport?.missingPercentage ?? 0}%</div>
                  <div className="text-sm text-gray-500">Missing</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-2xl font-semibold text-orange-600">{qualityReport?.duplicateRows ?? 0}</div>
                  <div className="text-sm text-gray-500">Duplicates</div>
                </div>
              </div>

              <button
                onClick={handleRunQualityAssessment}
                disabled={assessLoading}
                className="mt-4 btn btn-primary"
              >
                <BeakerIcon className={`h-5 w-5 mr-2 ${assessLoading ? 'animate-spin' : ''}`} />
                {assessLoading ? 'Assessing...' : 'Run Quality Assessment'}
              </button>
            </div>
          )}

          {/* Quality Dimensions */}
          {!qualityLoading && qualityReport?.dimensions && (
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Quality Dimensions</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {qualityReport.dimensions.map((dim) => (
                  <div key={dim.name} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">{dim.name}</span>
                      {getStatusIcon(dim.status)}
                    </div>
                    <div className="flex items-end">
                      <span className={`text-2xl font-bold ${getScoreColor(dim.score)}`}>
                        {dim.score}%
                      </span>
                    </div>
                    <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          dim.score >= 90 ? 'bg-green-500' :
                          dim.score >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${dim.score}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Column Quality Table */}
          {!qualityLoading && qualityReport?.columns && (
            <div className="bg-white shadow rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Column Quality Scores</h3>
              </div>
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Column</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Null %</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Unique %</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Issues</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {qualityReport.columns.map((col) => (
                    <tr key={col.name}>
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900">{col.name}</div>
                        <div className="text-xs text-gray-500">{col.semanticType}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        <span className="px-2 py-1 bg-gray-100 rounded text-xs">{col.dataType}</span>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <span className={col.nullPercentage > 5 ? 'text-red-600' : col.nullPercentage > 0 ? 'text-yellow-600' : 'text-green-600'}>
                          {col.nullPercentage}%
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">{col.uniquePercentage}%</td>
                      <td className="px-6 py-4">
                        <span className={`text-sm font-medium ${getScoreColor(col.overallScore)}`}>
                          {col.overallScore}%
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {col.issues.length > 0 ? (
                          <div className="text-xs text-red-600">
                            {col.issues.length} issue(s)
                          </div>
                        ) : (
                          <span className="text-xs text-green-600">No issues</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Recommendations */}
          {!qualityLoading && qualityReport?.recommendations && qualityReport.recommendations.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Recommendations</h3>
              <ul className="space-y-3">
                {qualityReport.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start">
                    <SparklesIcon className="h-5 w-5 text-blue-500 mr-3 mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-gray-700">{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* No Data State */}
          {!qualityLoading && !qualityReport && (
            <div className="bg-white shadow rounded-lg p-6 text-center">
              <ChartBarIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Quality Report Available</h3>
              <p className="text-gray-500 mb-4">Click the button below to run a quality assessment on your dataset.</p>
              <button
                onClick={handleRunQualityAssessment}
                disabled={assessLoading}
                className="btn btn-primary"
              >
                <BeakerIcon className={`h-5 w-5 mr-2 ${assessLoading ? 'animate-spin' : ''}`} />
                {assessLoading ? 'Assessing...' : 'Run Quality Assessment'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Schema Tab */}
      {activeTab === 'schema' && (
        <div className="space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Inferred Schema</h3>
              <button onClick={handleInferSchema} disabled={inferLoading} className="btn btn-primary btn-sm">
                <DocumentMagnifyingGlassIcon className={`h-4 w-4 mr-2 ${inferLoading ? 'animate-spin' : ''}`} />
                {inferLoading ? 'Inferring...' : 'Re-infer Schema'}
              </button>
            </div>

            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="text-2xl font-bold text-blue-600">
                  {apiSchema?.numericColumns?.length ?? qualityReport?.columns.filter(c => ['integer', 'float'].includes(c.dataType)).length ?? 0}
                </div>
                <div className="text-sm text-blue-700">Numeric Columns</div>
              </div>
              <div className="bg-purple-50 rounded-lg p-4">
                <div className="text-2xl font-bold text-purple-600">
                  {apiSchema?.categoricalColumns?.length ?? qualityReport?.columns.filter(c => c.dataType === 'categorical').length ?? 0}
                </div>
                <div className="text-sm text-purple-700">Categorical Columns</div>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <div className="text-2xl font-bold text-green-600">
                  {apiSchema?.dateColumns?.length ?? qualityReport?.columns.filter(c => c.dataType === 'datetime').length ?? 0}
                </div>
                <div className="text-sm text-green-700">Date Columns</div>
              </div>
            </div>

            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Column</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Inferred Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Semantic Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sample Values</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Transformations</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {apiSchema?.columns ? (
                  apiSchema.columns.map((col) => (
                    <tr key={col.name}>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">{col.name}</td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">{col.dataType}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs">{col.semanticType}</span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        <code className="text-xs bg-gray-100 px-1 rounded">
                          {col.sampleValues?.slice(0, 3).join(', ') || 'N/A'}
                        </code>
                      </td>
                      <td className="px-6 py-4">
                        {col.recommendedTransformations?.length > 0 ? (
                          <span className="text-xs text-gray-600">{col.recommendedTransformations[0]}</span>
                        ) : (
                          <span className="text-xs text-green-600">Ready to use</span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : qualityReport?.columns ? (
                  qualityReport.columns.map((col) => (
                    <tr key={col.name}>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">{col.name}</td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">{col.dataType}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs">{col.semanticType}</span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        <code className="text-xs bg-gray-100 px-1 rounded">N/A</code>
                      </td>
                      <td className="px-6 py-4">
                        {col.recommendations.length > 0 ? (
                          <span className="text-xs text-gray-600">{col.recommendations[0]}</span>
                        ) : (
                          <span className="text-xs text-green-600">Ready to use</span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                      No schema data available. Click "Re-infer Schema" to analyze the dataset.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Features Tab */}
      {activeTab === 'features' && (
        <div className="space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-medium text-gray-900">Feature Selection</h3>
                <p className="text-sm text-gray-500">Automatically select most predictive features</p>
              </div>
              <button onClick={handleSelectFeatures} disabled={selectLoading} className="btn btn-primary btn-sm">
                <FunnelIcon className={`h-4 w-4 mr-2 ${selectLoading ? 'animate-spin' : ''}`} />
                {selectLoading ? 'Running...' : 'Run Feature Selection'}
              </button>
            </div>

            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-green-50 rounded-lg p-4">
                <div className="text-2xl font-bold text-green-600">
                  {featureResult?.selectedFeatures?.length ?? featureScores.filter(f => f.selected).length}
                </div>
                <div className="text-sm text-green-700">Selected Features</div>
              </div>
              <div className="bg-red-50 rounded-lg p-4">
                <div className="text-2xl font-bold text-red-600">
                  {featureResult?.removedFeatures?.length ?? featureScores.filter(f => !f.selected).length}
                </div>
                <div className="text-sm text-red-700">Removed Features</div>
              </div>
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="text-2xl font-bold text-blue-600">
                  {featureResult?.highCorrelations?.length ?? 0}
                </div>
                <div className="text-sm text-blue-700">High Correlations</div>
              </div>
            </div>

            {featureLoading ? (
              <div className="flex items-center justify-center py-8">
                <ArrowPathIcon className="h-8 w-8 animate-spin text-blue-500 mr-3" />
                <span className="text-gray-600">Loading feature scores...</span>
              </div>
            ) : featureScores.length > 0 ? (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rank</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Feature</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Importance</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Correlation</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {featureScores.map((feat) => (
                    <tr key={feat.name} className={feat.selected ? '' : 'bg-gray-50'}>
                      <td className="px-6 py-4 text-sm text-gray-500">#{feat.rank}</td>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">{feat.name}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="h-2 rounded-full bg-blue-600"
                              style={{ width: `${feat.score * 100}%` }}
                            />
                          </div>
                          <span className="text-sm text-gray-600">{(feat.score * 100).toFixed(0)}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">{(feat.importance * 100).toFixed(0)}%</td>
                      <td className="px-6 py-4 text-sm text-gray-500">{feat.correlation.toFixed(2)}</td>
                      <td className="px-6 py-4">
                        {feat.selected ? (
                          <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">Selected</span>
                        ) : (
                          <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs">Removed</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-center py-8">
                <FunnelIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No Feature Scores Available</h3>
                <p className="text-gray-500">Click "Run Feature Selection" to analyze your features.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Cleaning Tab */}
      {activeTab === 'cleaning' && (
        <div className="space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-medium text-gray-900">Data Cleaning Pipeline</h3>
                <p className="text-sm text-gray-500">Configure and run data cleaning operations</p>
              </div>
              <button onClick={handleCleanData} disabled={cleanLoading} className="btn btn-primary">
                <SparklesIcon className={`h-5 w-5 mr-2 ${cleanLoading ? 'animate-spin' : ''}`} />
                {cleanLoading ? 'Cleaning...' : 'Run Cleaning Pipeline'}
              </button>
            </div>

            <div className="space-y-4">
              {/* Cleaning Options */}
              <div className="border rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                  <AdjustmentsHorizontalIcon className="h-5 w-5 mr-2 text-gray-400" />
                  Cleaning Operations
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={cleaningOptions.standardizeNulls}
                      onChange={(e) => handleCleaningOptionChange('standardizeNulls', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600"
                    />
                    <span className="ml-2 text-sm text-gray-700">Standardize null values</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={cleaningOptions.trimWhitespace}
                      onChange={(e) => handleCleaningOptionChange('trimWhitespace', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600"
                    />
                    <span className="ml-2 text-sm text-gray-700">Trim whitespace</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={cleaningOptions.removeDuplicates}
                      onChange={(e) => handleCleaningOptionChange('removeDuplicates', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600"
                    />
                    <span className="ml-2 text-sm text-gray-700">Remove duplicates</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={cleaningOptions.handleOutliers}
                      onChange={(e) => handleCleaningOptionChange('handleOutliers', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600"
                    />
                    <span className="ml-2 text-sm text-gray-700">Handle outliers</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={cleaningOptions.normalizeCase}
                      onChange={(e) => handleCleaningOptionChange('normalizeCase', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600"
                    />
                    <span className="ml-2 text-sm text-gray-700">Normalize case</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={cleaningOptions.fixEncoding}
                      onChange={(e) => handleCleaningOptionChange('fixEncoding', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600"
                    />
                    <span className="ml-2 text-sm text-gray-700">Fix encoding issues</span>
                  </label>
                </div>
              </div>

              {/* Missing Value Imputation */}
              <div className="border rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-3">Missing Value Strategy</h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-sm text-gray-600">Numeric Columns</label>
                    <select
                      value={cleaningOptions.numericImputation}
                      onChange={(e) => handleCleaningOptionChange('numericImputation', e.target.value)}
                      className="mt-1 block w-full text-sm border-gray-300 rounded-md"
                    >
                      <option value="median">Median</option>
                      <option value="mean">Mean</option>
                      <option value="mode">Mode</option>
                      <option value="drop">Drop rows</option>
                      <option value="interpolate">Interpolate</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">Categorical Columns</label>
                    <select
                      value={cleaningOptions.categoricalImputation}
                      onChange={(e) => handleCleaningOptionChange('categoricalImputation', e.target.value)}
                      className="mt-1 block w-full text-sm border-gray-300 rounded-md"
                    >
                      <option value="mode">Mode</option>
                      <option value="constant">Constant (Unknown)</option>
                      <option value="drop">Drop rows</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">Date Columns</label>
                    <select
                      value={cleaningOptions.dateImputation}
                      onChange={(e) => handleCleaningOptionChange('dateImputation', e.target.value)}
                      className="mt-1 block w-full text-sm border-gray-300 rounded-md"
                    >
                      <option value="forward_fill">Forward fill</option>
                      <option value="backward_fill">Backward fill</option>
                      <option value="interpolate">Interpolate</option>
                      <option value="drop">Drop rows</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Outlier Handling */}
              <div className="border rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-3">Outlier Handling</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-gray-600">Strategy</label>
                    <select
                      value={cleaningOptions.outlierStrategy}
                      onChange={(e) => handleCleaningOptionChange('outlierStrategy', e.target.value)}
                      className="mt-1 block w-full text-sm border-gray-300 rounded-md"
                    >
                      <option value="cap">Cap (Winsorize)</option>
                      <option value="remove">Remove</option>
                      <option value="replace_mean">Replace with mean</option>
                      <option value="replace_median">Replace with median</option>
                      <option value="keep">Keep</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">Detection Method</label>
                    <select
                      value={cleaningOptions.outlierMethod}
                      onChange={(e) => handleCleaningOptionChange('outlierMethod', e.target.value)}
                      className="mt-1 block w-full text-sm border-gray-300 rounded-md"
                    >
                      <option value="zscore">Z-score (3 std)</option>
                      <option value="iqr">IQR (1.5x)</option>
                      <option value="percentile">Percentile (1%-99%)</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Cleaning Preview */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Cleaning Preview</h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Estimated Changes</h4>
                  <ul className="space-y-2 text-sm">
                    <li className="flex justify-between">
                      <span className="text-gray-600">Null values to impute:</span>
                      <span className="font-medium">250</span>
                    </li>
                    <li className="flex justify-between">
                      <span className="text-gray-600">Duplicates to remove:</span>
                      <span className="font-medium">25</span>
                    </li>
                    <li className="flex justify-between">
                      <span className="text-gray-600">Outliers to handle:</span>
                      <span className="font-medium">45</span>
                    </li>
                    <li className="flex justify-between">
                      <span className="text-gray-600">Whitespace fixes:</span>
                      <span className="font-medium">120</span>
                    </li>
                  </ul>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Expected Result</h4>
                  <ul className="space-y-2 text-sm">
                    <li className="flex justify-between">
                      <span className="text-gray-600">Final row count:</span>
                      <span className="font-medium">9,975</span>
                    </li>
                    <li className="flex justify-between">
                      <span className="text-gray-600">Missing values:</span>
                      <span className="font-medium text-green-600">0%</span>
                    </li>
                    <li className="flex justify-between">
                      <span className="text-gray-600">Quality score:</span>
                      <span className="font-medium text-green-600">95%+</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
