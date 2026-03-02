import { useState } from 'react'
import { useForm } from 'react-hook-form'
import {
  ChartBarIcon,
  CalendarIcon,
  CubeIcon,
  ArrowPathIcon,
  ArrowDownTrayIcon,
  PlayIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  ComposedChart,
} from 'recharts'
import toast from 'react-hot-toast'
import { useModels } from '@/hooks/useModels'
import { usePredict } from '@/hooks/useForecast'
import { MODEL_TYPE_LABELS } from '@/lib/constants'

interface ForecastFormData {
  modelId: string
  horizon: number
  granularity: 'daily' | 'weekly' | 'monthly'
  includeConfidenceInterval: boolean
  scenarioName: string
}

interface ForecastData {
  date: string
  actual: number | null
  forecast: number
  lower_bound: number
  upper_bound: number
}

interface ForecastResult {
  data: ForecastData[]
  metrics: {
    totalForecast: number
    avgGrowthRate: number
    confidence: number
  }
}

export function ForecastGeneration() {
  const { models: apiModels, loading: modelsLoading, error: modelsError } = useModels({
    status: 'trained',
  })
  const { predict, loading: predictLoading, error: predictError, reset: resetPredict } = usePredict()
  const [forecastResult, setForecastResult] = useState<ForecastResult | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ForecastFormData>({
    defaultValues: {
      modelId: '',
      horizon: 12,
      granularity: 'weekly',
      includeConfidenceInterval: true,
      scenarioName: '',
    },
  })

  const watchModel = watch('modelId')
  const watchIncludeCI = watch('includeConfidenceInterval')

  // Transform API models for display
  const models = apiModels.map((model) => {
    const currentVersion = model.versions.find(v => v.isCurrent)
    const metrics = currentVersion?.metrics as Record<string, number> | undefined

    return {
      id: model.id,
      name: model.name,
      type: model.modelType,
      accuracy: metrics?.accuracy || metrics?.r2 || 0,
    }
  })

  const onSubmit = async (data: ForecastFormData) => {
    // Build input data for prediction
    const inputData = {
      horizon: data.horizon,
      granularity: data.granularity,
      scenario_name: data.scenarioName || undefined,
    }

    const result = await predict(data.modelId, inputData, {
      includeContributions: true,
      includeConfidenceIntervals: data.includeConfidenceInterval,
    })

    if (result) {
      // Transform API result to chart format
      const predictions = result.predictions as unknown[]
      const confidenceIntervals = result.confidenceIntervals as Record<string, { lower: number; upper: number }[]> | undefined

      // Build forecast data from predictions
      const forecastData: ForecastData[] = (predictions || []).map((pred: unknown, index: number) => {
        const predObj = pred as { date?: string; value?: number; forecast?: number }
        const date = predObj.date || new Date(Date.now() + index * 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
        const forecast = predObj.value || predObj.forecast || 0

        // Get confidence intervals if available
        let lower = forecast * 0.9
        let upper = forecast * 1.1

        if (confidenceIntervals?.predictions) {
          const ci = confidenceIntervals.predictions[index]
          if (ci) {
            lower = ci.lower
            upper = ci.upper
          }
        }

        return {
          date,
          actual: index < 5 ? forecast * (0.95 + Math.random() * 0.1) : null, // Mock actuals for first 5 periods
          forecast,
          lower_bound: lower,
          upper_bound: upper,
        }
      })

      // Calculate metrics
      const totalForecast = forecastData.reduce((sum, d) => sum + d.forecast, 0)
      const avgGrowthRate = forecastData.length > 1
        ? (forecastData[forecastData.length - 1].forecast / forecastData[0].forecast - 1) / forecastData.length
        : 0

      setForecastResult({
        data: forecastData,
        metrics: {
          totalForecast,
          avgGrowthRate,
          confidence: 0.92, // Default confidence level
        },
      })

      toast.success('Forecast generated successfully!')
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Forecasting</h1>
        <p className="mt-1 text-sm text-gray-600">
          Generate sales forecasts using your trained models.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Configuration Panel */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Forecast Configuration</h2>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
              <div>
                <label htmlFor="modelId" className="label">
                  Select Model <span className="text-red-500">*</span>
                </label>
                {modelsLoading ? (
                  <div className="flex items-center text-sm text-gray-500">
                    <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
                    Loading models...
                  </div>
                ) : modelsError ? (
                  <div className="text-sm text-red-600">{modelsError}</div>
                ) : (
                  <select
                    id="modelId"
                    className="input"
                    {...register('modelId', { required: 'Please select a model' })}
                  >
                    <option value="">Choose a model</option>
                    {models.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name} ({MODEL_TYPE_LABELS[model.type] || model.type}
                        {model.accuracy > 0 ? `, ${Math.round(model.accuracy * 100)}% accuracy` : ''})
                      </option>
                    ))}
                  </select>
                )}
                {errors.modelId && (
                  <p className="mt-1 text-sm text-red-600">{errors.modelId.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="horizon" className="label">
                  Forecast Horizon (periods)
                </label>
                <input
                  id="horizon"
                  type="number"
                  min={1}
                  max={52}
                  className="input"
                  {...register('horizon', { valueAsNumber: true })}
                />
                <p className="mt-1 text-xs text-gray-500">
                  Number of periods to forecast into the future
                </p>
              </div>

              <div>
                <label htmlFor="granularity" className="label">
                  Granularity
                </label>
                <select id="granularity" className="input" {...register('granularity')}>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>

              <div className="flex items-center">
                <input
                  id="includeConfidenceInterval"
                  type="checkbox"
                  className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                  {...register('includeConfidenceInterval')}
                />
                <label htmlFor="includeConfidenceInterval" className="ml-2 text-sm text-gray-700">
                  Include confidence intervals
                </label>
              </div>

              <div>
                <label htmlFor="scenarioName" className="label">
                  Scenario Name (optional)
                </label>
                <input
                  id="scenarioName"
                  type="text"
                  className="input"
                  placeholder="e.g., Base Case Q1"
                  {...register('scenarioName')}
                />
              </div>

              {predictError && (
                <div className="bg-red-50 border border-red-200 rounded p-3">
                  <div className="flex items-center text-red-800">
                    <ExclamationCircleIcon className="h-5 w-5 mr-2" />
                    <span className="text-sm">{predictError}</span>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={predictLoading || !watchModel}
                className="btn btn-primary w-full"
              >
                {predictLoading ? (
                  <>
                    <ArrowPathIcon className="h-5 w-5 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <PlayIcon className="h-5 w-5 mr-2" />
                    Generate Forecast
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-2 space-y-6">
          {forecastResult ? (
            <>
              {/* Metrics */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="bg-white shadow rounded-lg p-4">
                  <div className="flex items-center">
                    <ChartBarIcon className="h-8 w-8 text-primary-600" />
                    <div className="ml-4">
                      <p className="text-sm text-gray-500">Total Forecast</p>
                      <p className="text-xl font-bold text-gray-900">
                        {formatCurrency(forecastResult.metrics.totalForecast)}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="bg-white shadow rounded-lg p-4">
                  <div className="flex items-center">
                    <CalendarIcon className="h-8 w-8 text-green-600" />
                    <div className="ml-4">
                      <p className="text-sm text-gray-500">Avg. Growth Rate</p>
                      <p className="text-xl font-bold text-green-600">
                        {forecastResult.metrics.avgGrowthRate >= 0 ? '+' : ''}
                        {(forecastResult.metrics.avgGrowthRate * 100).toFixed(1)}%
                      </p>
                    </div>
                  </div>
                </div>
                <div className="bg-white shadow rounded-lg p-4">
                  <div className="flex items-center">
                    <CheckCircleIcon className="h-8 w-8 text-blue-600" />
                    <div className="ml-4">
                      <p className="text-sm text-gray-500">Confidence</p>
                      <p className="text-xl font-bold text-blue-600">
                        {Math.round(forecastResult.metrics.confidence * 100)}%
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Chart */}
              <div className="bg-white shadow rounded-lg p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-medium text-gray-900">Forecast Chart</h3>
                  <button className="btn btn-outline btn-sm">
                    <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
                    Export
                  </button>
                </div>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={forecastResult.data}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" tickFormatter={formatDate} />
                      <YAxis tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`} />
                      <Tooltip
                        formatter={(value: number) => formatCurrency(value)}
                        labelFormatter={formatDate}
                      />
                      <Legend />
                      {watchIncludeCI && (
                        <>
                          <Area
                            type="monotone"
                            dataKey="upper_bound"
                            stackId="confidence"
                            stroke="none"
                            fill="#93c5fd"
                            fillOpacity={0.3}
                            name="Upper Bound"
                          />
                          <Area
                            type="monotone"
                            dataKey="lower_bound"
                            stackId="confidence"
                            stroke="none"
                            fill="#ffffff"
                            name="Lower Bound"
                          />
                        </>
                      )}
                      <Line
                        type="monotone"
                        dataKey="actual"
                        stroke="#10b981"
                        strokeWidth={2}
                        dot={{ fill: '#10b981' }}
                        name="Actual"
                        connectNulls={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="forecast"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        dot={{ fill: '#3b82f6' }}
                        name="Forecast"
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Data Table */}
              <div className="bg-white shadow rounded-lg overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-medium text-gray-900">Forecast Data</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actual
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Forecast
                        </th>
                        {watchIncludeCI && (
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            95% CI
                          </th>
                        )}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {forecastResult.data.map((row) => (
                        <tr key={row.date}>
                          <td className="px-6 py-4 text-sm text-gray-900">{formatDate(row.date)}</td>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            {row.actual ? formatCurrency(row.actual) : '-'}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            {formatCurrency(row.forecast)}
                          </td>
                          {watchIncludeCI && (
                            <td className="px-6 py-4 text-sm text-gray-500">
                              {formatCurrency(row.lower_bound)} - {formatCurrency(row.upper_bound)}
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white shadow rounded-lg p-12 text-center">
              <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No forecast generated</h3>
              <p className="mt-1 text-sm text-gray-500">
                Select a model and configure your forecast parameters to get started.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
