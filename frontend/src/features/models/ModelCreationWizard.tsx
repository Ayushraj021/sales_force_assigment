import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useForm } from 'react-hook-form'
import {
  CubeIcon,
  CircleStackIcon,
  Cog6ToothIcon,
  CheckCircleIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { useModels } from '@/hooks/useModels'
import { useDatasets, type Dataset } from '@/hooks/useDatasets'

interface ModelFormData {
  name: string
  description: string
  type: 'mmm' | 'attribution' | 'causal' | 'forecast'
  datasetId: string
  targetColumn: string
  dateColumn: string
  channelColumns: string[]
  parameters: {
    adstockMaxLag: number
    saturationHillSlope: number
    mcmcSamples: number
    mcmcChains: number
    trainTestSplit: number
  }
}

const modelTypes = [
  {
    id: 'mmm',
    name: 'Marketing Mix Model',
    description: 'Analyze marketing effectiveness and optimize budget allocation',
    icon: SparklesIcon,
  },
  {
    id: 'attribution',
    name: 'Attribution Model',
    description: 'Understand the contribution of each touchpoint to conversions',
    icon: CubeIcon,
  },
  {
    id: 'forecast',
    name: 'Forecasting Model',
    description: 'Predict future sales and revenue trends',
    icon: SparklesIcon,
  },
  {
    id: 'causal',
    name: 'Causal Inference',
    description: 'Measure the causal impact of marketing interventions',
    icon: CubeIcon,
  },
]

const steps = [
  { id: 1, name: 'Model Type', icon: CubeIcon },
  { id: 2, name: 'Dataset', icon: CircleStackIcon },
  { id: 3, name: 'Configuration', icon: Cog6ToothIcon },
  { id: 4, name: 'Review', icon: CheckCircleIcon },
]

export function ModelCreationWizard() {
  const navigate = useNavigate()
  const { createModel, trainModel } = useModels({ autoFetch: false })
  const { datasets, loading: datasetsLoading, error: datasetsError } = useDatasets()
  const [currentStep, setCurrentStep] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ModelFormData>({
    defaultValues: {
      name: '',
      description: '',
      type: 'mmm',
      datasetId: '',
      targetColumn: '',
      dateColumn: '',
      channelColumns: [],
      parameters: {
        adstockMaxLag: 8,
        saturationHillSlope: 0.5,
        mcmcSamples: 2000,
        mcmcChains: 4,
        trainTestSplit: 0.8,
      },
    },
  })

  const watchType = watch('type')
  const watchDatasetId = watch('datasetId')

  const handleDatasetChange = (datasetId: string) => {
    const dataset = datasets.find((d) => d.id === datasetId)
    setSelectedDataset(dataset || null)
  }

  const onSubmit = async (data: ModelFormData) => {
    setIsSubmitting(true)
    try {
      // Map form type to API model type
      const modelTypeMap: Record<string, string> = {
        'mmm': 'pymc_mmm',
        'attribution': 'custom_mmm',
        'forecast': 'prophet',
        'causal': 'custom_mmm',
      }

      // Create the model
      const model = await createModel({
        name: data.name,
        description: data.description,
        modelType: modelTypeMap[data.type] || 'pymc_mmm',
        datasetId: data.datasetId,
        config: {
          targetColumn: data.targetColumn,
          dateColumn: data.dateColumn,
          channelColumns: data.channelColumns,
          parameters: data.parameters,
        },
      })

      // Start training
      await trainModel(model.id)

      toast.success('Model created successfully! Training has started.')
      navigate({ to: '/models' })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create model')
    } finally {
      setIsSubmitting(false)
    }
  }

  const nextStep = () => {
    if (currentStep < 4) setCurrentStep(currentStep + 1)
  }

  const prevStep = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <button
          onClick={() => navigate({ to: '/models' })}
          className="flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to models
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Create New Model</h1>
        <p className="mt-1 text-sm text-gray-600">
          Follow the steps below to configure and train your model.
        </p>
      </div>

      {/* Progress Steps */}
      <div className="mb-8">
        <nav aria-label="Progress">
          <ol className="flex items-center">
            {steps.map((step, stepIdx) => (
              <li
                key={step.name}
                className={`relative ${stepIdx !== steps.length - 1 ? 'pr-8 sm:pr-20 flex-1' : ''}`}
              >
                {stepIdx !== steps.length - 1 && (
                  <div className="absolute top-5 left-10 -ml-px h-0.5 w-full sm:w-20 -z-10">
                    <div
                      className={`h-full ${
                        step.id < currentStep ? 'bg-primary-600' : 'bg-gray-300'
                      }`}
                    />
                  </div>
                )}
                <div className="flex items-center">
                  <div
                    className={`relative z-10 flex h-10 w-10 items-center justify-center rounded-full ${
                      step.id < currentStep
                        ? 'bg-primary-600'
                        : step.id === currentStep
                        ? 'border-2 border-primary-600 bg-white'
                        : 'border-2 border-gray-300 bg-white'
                    }`}
                  >
                    {step.id < currentStep ? (
                      <CheckCircleIcon className="h-6 w-6 text-white" />
                    ) : (
                      <step.icon
                        className={`h-5 w-5 ${
                          step.id === currentStep ? 'text-primary-600' : 'text-gray-500'
                        }`}
                      />
                    )}
                  </div>
                  <span
                    className={`ml-4 text-sm font-medium bg-gray-50 px-1 ${
                      step.id <= currentStep ? 'text-primary-600' : 'text-gray-500'
                    }`}
                  >
                    {step.name}
                  </span>
                </div>
              </li>
            ))}
          </ol>
        </nav>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="bg-white shadow rounded-lg">
          {/* Step 1: Model Type */}
          {currentStep === 1 && (
            <div className="p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-6">Select Model Type</h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {modelTypes.map((type) => (
                  <label
                    key={type.id}
                    className={`relative flex cursor-pointer rounded-lg border p-4 focus:outline-none ${
                      watchType === type.id
                        ? 'border-primary-600 ring-2 ring-primary-600'
                        : 'border-gray-300 hover:border-gray-400'
                    }`}
                  >
                    <input
                      type="radio"
                      {...register('type')}
                      value={type.id}
                      className="sr-only"
                    />
                    <div className="flex items-start">
                      <type.icon className="h-8 w-8 text-primary-600" />
                      <div className="ml-4">
                        <span className="block text-sm font-medium text-gray-900">
                          {type.name}
                        </span>
                        <span className="mt-1 text-sm text-gray-500">{type.description}</span>
                      </div>
                    </div>
                    {watchType === type.id && (
                      <CheckCircleIcon className="absolute top-4 right-4 h-5 w-5 text-primary-600" />
                    )}
                  </label>
                ))}
              </div>

              <div className="mt-6 space-y-4">
                <div>
                  <label htmlFor="name" className="label">
                    Model Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="name"
                    type="text"
                    className="input"
                    placeholder="e.g., Q1 Marketing Mix Model"
                    {...register('name', { required: 'Model name is required' })}
                  />
                  {errors.name && (
                    <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="description" className="label">
                    Description
                  </label>
                  <textarea
                    id="description"
                    rows={3}
                    className="input"
                    placeholder="Describe the purpose of this model..."
                    {...register('description')}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Dataset */}
          {currentStep === 2 && (
            <div className="p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-6">Select Dataset</h2>

              {/* Loading state */}
              {datasetsLoading && (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mr-3"></div>
                  <span className="text-gray-600">Loading datasets...</span>
                </div>
              )}

              {/* Error state */}
              {datasetsError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                  <div className="flex items-center">
                    <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mr-2" />
                    <span className="text-red-700">{datasetsError}</span>
                  </div>
                </div>
              )}

              {/* No datasets */}
              {!datasetsLoading && !datasetsError && datasets.length === 0 && (
                <div className="text-center py-8">
                  <CircleStackIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No Datasets Available</h3>
                  <p className="text-gray-500">
                    Please upload a dataset first before creating a model.
                  </p>
                </div>
              )}

              {/* Dataset list */}
              {!datasetsLoading && datasets.length > 0 && (
                <div className="space-y-4">
                  {datasets.map((dataset) => (
                    <label
                      key={dataset.id}
                      className={`relative flex cursor-pointer rounded-lg border p-4 focus:outline-none ${
                        watchDatasetId === dataset.id
                          ? 'border-primary-600 ring-2 ring-primary-600'
                          : 'border-gray-300 hover:border-gray-400'
                      }`}
                    >
                      <input
                        type="radio"
                        {...register('datasetId', { required: 'Please select a dataset' })}
                        value={dataset.id}
                        onChange={(e) => {
                          handleDatasetChange(e.target.value)
                        }}
                        className="sr-only"
                      />
                      <CircleStackIcon className="h-8 w-8 text-primary-600" />
                      <div className="ml-4 flex-1">
                        <span className="block text-sm font-medium text-gray-900">
                          {dataset.name}
                        </span>
                        <span className="mt-1 text-sm text-gray-500">
                          {(dataset.rowCount || 0).toLocaleString()} rows | {dataset.columnNames?.length || 0} columns
                        </span>
                        {dataset.description && (
                          <span className="mt-1 text-xs text-gray-400 block">{dataset.description}</span>
                        )}
                      </div>
                      {watchDatasetId === dataset.id && (
                        <CheckCircleIcon className="absolute top-4 right-4 h-5 w-5 text-primary-600" />
                      )}
                    </label>
                  ))}
                </div>
              )}

              {errors.datasetId && (
                <p className="mt-2 text-sm text-red-600">{errors.datasetId.message}</p>
              )}

              {selectedDataset && (
                <div className="mt-6 space-y-4">
                  <div>
                    <label htmlFor="dateColumn" className="label">
                      Date Column <span className="text-red-500">*</span>
                    </label>
                    <select
                      id="dateColumn"
                      className="input"
                      {...register('dateColumn', { required: 'Please select date column' })}
                    >
                      <option value="">Select column</option>
                      {(selectedDataset.columnNames || []).map((col) => (
                        <option key={col} value={col}>
                          {col}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="targetColumn" className="label">
                      Target Column (Revenue/Sales) <span className="text-red-500">*</span>
                    </label>
                    <select
                      id="targetColumn"
                      className="input"
                      {...register('targetColumn', { required: 'Please select target column' })}
                    >
                      <option value="">Select column</option>
                      {(selectedDataset.columnNames || []).map((col) => (
                        <option key={col} value={col}>
                          {col}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="label">
                      Channel Columns (Marketing Spend) <span className="text-red-500">*</span>
                    </label>
                    <div className="mt-2 space-y-2">
                      {(selectedDataset.columnNames || [])
                        .filter((col) => !['date', 'revenue', 'target', 'time'].includes(col.toLowerCase()))
                        .map((col) => (
                          <label key={col} className="flex items-center">
                            <input
                              type="checkbox"
                              {...register('channelColumns')}
                              value={col}
                              className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                            />
                            <span className="ml-2 text-sm text-gray-700">{col}</span>
                          </label>
                        ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Configuration */}
          {currentStep === 3 && (
            <div className="p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-6">Model Parameters</h2>

              <div className="space-y-6">
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                  <div>
                    <label htmlFor="adstockMaxLag" className="label">
                      Adstock Max Lag (weeks)
                    </label>
                    <input
                      id="adstockMaxLag"
                      type="number"
                      min={1}
                      max={52}
                      className="input"
                      {...register('parameters.adstockMaxLag', { valueAsNumber: true })}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Maximum number of weeks for carryover effect
                    </p>
                  </div>

                  <div>
                    <label htmlFor="saturationHillSlope" className="label">
                      Saturation Hill Slope
                    </label>
                    <input
                      id="saturationHillSlope"
                      type="number"
                      step="0.1"
                      min={0.1}
                      max={2}
                      className="input"
                      {...register('parameters.saturationHillSlope', { valueAsNumber: true })}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Controls the steepness of diminishing returns
                    </p>
                  </div>

                  <div>
                    <label htmlFor="mcmcSamples" className="label">
                      MCMC Samples
                    </label>
                    <input
                      id="mcmcSamples"
                      type="number"
                      min={500}
                      max={10000}
                      step={500}
                      className="input"
                      {...register('parameters.mcmcSamples', { valueAsNumber: true })}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Number of MCMC samples for inference
                    </p>
                  </div>

                  <div>
                    <label htmlFor="mcmcChains" className="label">
                      MCMC Chains
                    </label>
                    <input
                      id="mcmcChains"
                      type="number"
                      min={1}
                      max={8}
                      className="input"
                      {...register('parameters.mcmcChains', { valueAsNumber: true })}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Number of parallel chains for sampling
                    </p>
                  </div>

                  <div>
                    <label htmlFor="trainTestSplit" className="label">
                      Train/Test Split Ratio
                    </label>
                    <input
                      id="trainTestSplit"
                      type="number"
                      step="0.05"
                      min={0.5}
                      max={0.95}
                      className="input"
                      {...register('parameters.trainTestSplit', { valueAsNumber: true })}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Proportion of data used for training
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Review */}
          {currentStep === 4 && (
            <div className="p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-6">Review & Create</h2>

              <div className="bg-gray-50 rounded-lg p-4 space-y-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Model Name</h3>
                  <p className="text-sm text-gray-900">{watch('name') || 'Not specified'}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Model Type</h3>
                  <p className="text-sm text-gray-900">
                    {modelTypes.find((t) => t.id === watchType)?.name}
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Dataset</h3>
                  <p className="text-sm text-gray-900">{selectedDataset?.name || 'Not selected'}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Target Column</h3>
                  <p className="text-sm text-gray-900">{watch('targetColumn') || 'Not selected'}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Channel Columns</h3>
                  <p className="text-sm text-gray-900">
                    {watch('channelColumns')?.join(', ') || 'Not selected'}
                  </p>
                </div>
              </div>

              <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-800">
                  <strong>Note:</strong> Training will begin immediately after creation. This may
                  take anywhere from a few minutes to several hours depending on the dataset size
                  and model complexity.
                </p>
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            <button
              type="button"
              onClick={prevStep}
              disabled={currentStep === 1}
              className="btn btn-outline disabled:opacity-50"
            >
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              Previous
            </button>

            {currentStep < 4 ? (
              <button type="button" onClick={nextStep} className="btn btn-primary">
                Next
                <ArrowRightIcon className="h-4 w-4 ml-2" />
              </button>
            ) : (
              <button type="submit" disabled={isSubmitting} className="btn btn-primary">
                {isSubmitting ? 'Creating...' : 'Create Model & Start Training'}
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  )
}
