import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  CloudArrowUpIcon,
  DocumentIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'
import { useAuthStore } from '@/stores/authStore'
import { useNavigate } from '@tanstack/react-router'
import toast from 'react-hot-toast'

interface UploadedFile {
  file: File
  id: string
  status: 'pending' | 'uploading' | 'validating' | 'success' | 'error'
  progress: number
  error?: string
  preview?: DataPreview
  detectedColumns?: DetectedColumns | null
  validationWarnings?: string[]
}

interface DataPreview {
  columns: string[]
  rows: Record<string, string>[]
  totalRows: number
  warnings: string[]
}

interface DetectedColumns {
  dateColumns: string[]
  numericColumns: string[]
  categoricalColumns: string[]
  potentialTarget: string | null
  potentialSpendColumns: string[]
}

interface ValidationResult {
  isValid: boolean
  errors: string[]
  warnings: string[]
  rowCount: number | null
  columnCount: number | null
  detectedColumns: DetectedColumns | null
  preview?: DataPreview
}

interface UploadGuideline {
  text: string
  type: 'required' | 'recommended'
}

interface ColumnRequirement {
  name: string
  description: string
  type: 'required' | 'recommended' | 'optional'
  examples: string[]
}

interface UploadConfig {
  allowedExtensions: string[]
  maxFileSizeBytes: number
  maxFileSizeDisplay: string
  guidelines: UploadGuideline[]
  requiredColumns: ColumnRequirement[]
  optionalColumns: ColumnRequirement[]
  templateColumns: string[]
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Default config while loading
const DEFAULT_CONFIG: UploadConfig = {
  allowedExtensions: ['.csv', '.xlsx', '.xls', '.parquet'],
  maxFileSizeBytes: 100 * 1024 * 1024,
  maxFileSizeDisplay: '100MB',
  guidelines: [],
  requiredColumns: [],
  optionalColumns: [],
  templateColumns: ['date', 'revenue', 'tv_spend', 'digital_spend', 'search_spend', 'social_spend', 'email_spend'],
}

export function DataUpload() {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [selectedFile, setSelectedFile] = useState<UploadedFile | null>(null)
  const [uploadConfig, setUploadConfig] = useState<UploadConfig>(DEFAULT_CONFIG)
  const [configLoading, setConfigLoading] = useState(true)
  const { accessToken, tokenExpiresAt, refreshAccessToken, logout } = useAuthStore()
  const navigate = useNavigate()

  // Helper function to get a valid access token (refreshes if expired)
  const getValidToken = async (): Promise<string | null> => {
    // Check if token exists
    if (!accessToken) {
      return null
    }

    // Check if token is expired or about to expire (within 1 minute)
    const now = Date.now()
    const expiresAt = tokenExpiresAt || 0
    const isExpired = expiresAt < now + 60000 // 1 minute buffer

    if (isExpired) {
      try {
        await refreshAccessToken()
        // Get the new token from the store
        return useAuthStore.getState().accessToken
      } catch (error) {
        console.error('Failed to refresh token:', error)
        toast.error('Session expired. Please log in again.')
        logout()
        navigate({ to: '/login' })
        return null
      }
    }

    return accessToken
  }

  // Fetch upload configuration from API
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch(`${API_URL}/api/upload/config`)
        if (response.ok) {
          const config = await response.json()
          setUploadConfig(config)
        }
      } catch (error) {
        console.error('Failed to fetch upload config:', error)
        // Keep using default config
      } finally {
        setConfigLoading(false)
      }
    }
    fetchConfig()
  }, [])

  const downloadTemplate = () => {
    // Create CSV template content using dynamic columns from config
    const headers = uploadConfig.templateColumns
    const sampleRow = headers.map((col: string) => {
      if (col.toLowerCase().includes('date')) return '2024-01-01'
      if (col.toLowerCase().includes('revenue') || col.toLowerCase().includes('sales')) return '10000'
      if (col.toLowerCase().includes('spend') || col.toLowerCase().includes('cost')) return '500'
      return '100'
    })

    const csvContent = [
      headers.join(','),
      sampleRow.join(','),
      // Add a few more sample rows with varying data
      headers.map((col: string, i: number) => {
        if (col.toLowerCase().includes('date')) return '2024-01-08'
        const baseVal = parseInt(sampleRow[i]) || 100
        return String(Math.round(baseVal * 1.2))
      }).join(','),
      headers.map((col: string, i: number) => {
        if (col.toLowerCase().includes('date')) return '2024-01-15'
        const baseVal = parseInt(sampleRow[i]) || 100
        return String(Math.round(baseVal * 1.15))
      }).join(','),
      headers.map((col: string, i: number) => {
        if (col.toLowerCase().includes('date')) return '2024-01-22'
        const baseVal = parseInt(sampleRow[i]) || 100
        return String(Math.round(baseVal * 1.3))
      }).join(','),
    ].join('\n')

    // Create blob and download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'sales_forecasting_template.csv'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    toast.success('Template downloaded!')
  }

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file) => ({
      file,
      id: `${file.name}-${Date.now()}`,
      status: 'pending' as const,
      progress: 0,
    }))
    setFiles((prev) => [...prev, ...newFiles])
  }, [])

  // Build accept object dynamically from config
  const acceptConfig = uploadConfig.allowedExtensions.reduce((acc: Record<string, string[]>, ext: string) => {
    const mimeTypes: Record<string, string> = {
      '.csv': 'text/csv',
      '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      '.xls': 'application/vnd.ms-excel',
      '.parquet': 'application/octet-stream',
    }
    const mime = mimeTypes[ext] || 'application/octet-stream'
    acc[mime] = [...(acc[mime] || []), ext]
    return acc
  }, {} as Record<string, string[]>)

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptConfig,
    maxSize: uploadConfig.maxFileSizeBytes,
    multiple: true,
  })

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
    if (selectedFile?.id === id) {
      setSelectedFile(null)
    }
  }

  const uploadFile = async (uploadFile: UploadedFile) => {
    // Get a valid token (refresh if expired)
    const token = await getValidToken()
    if (!token) {
      const errorMsg = 'Not authenticated. Please log in again.'
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id ? { ...f, status: 'error', error: errorMsg } : f
        )
      )
      toast.error(errorMsg)
      return
    }

    setFiles((prev) =>
      prev.map((f) =>
        f.id === uploadFile.id ? { ...f, status: 'uploading', progress: 0 } : f
      )
    )

    try {
      const formData = new FormData()
      formData.append('file', uploadFile.file)

      // First, validate the file
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id ? { ...f, status: 'validating', progress: 50 } : f
        )
      )

      const validateResponse = await fetch(`${API_URL}/api/upload/validate`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      })

      if (!validateResponse.ok) {
        // Extract detailed error from response
        let errorMessage = 'Validation failed'
        try {
          const errorData = await validateResponse.json()
          errorMessage = errorData.detail || errorData.message || errorData.errors?.join(', ') || `Validation failed (${validateResponse.status})`
        } catch {
          errorMessage = `Validation failed: ${validateResponse.status} ${validateResponse.statusText}`
        }
        throw new Error(errorMessage)
      }

      const validation: ValidationResult = await validateResponse.json()

      if (!validation.isValid) {
        const errorMsg = validation.errors.join('; ')
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id
              ? { ...f, status: 'error', error: errorMsg }
              : f
          )
        )
        toast.error(`Validation failed: ${errorMsg}`)
        return
      }

      // Upload the file
      const uploadFormData = new FormData()
      uploadFormData.append('file', uploadFile.file)

      const uploadResponse = await fetch(`${API_URL}/api/upload/data`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: uploadFormData,
      })

      if (!uploadResponse.ok) {
        // Extract detailed error from response
        let errorMessage = 'Upload failed'
        try {
          const errorData = await uploadResponse.json()
          errorMessage = errorData.detail || errorData.message || `Upload failed (${uploadResponse.status})`
        } catch {
          errorMessage = `Upload failed: ${uploadResponse.status} ${uploadResponse.statusText}`
        }
        throw new Error(errorMessage)
      }

      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? {
                ...f,
                status: 'success',
                progress: 100,
                preview: validation.preview,
                detectedColumns: validation.detectedColumns,
                validationWarnings: validation.warnings,
              }
            : f
        )
      )

      // Show warnings if any
      if (validation.warnings && validation.warnings.length > 0) {
        toast(`${uploadFile.file.name} uploaded with warnings`, { icon: '⚠️' })
      } else {
        toast.success(`${uploadFile.file.name} uploaded successfully!`)
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed'
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? { ...f, status: 'error', error: errorMessage }
            : f
        )
      )
      toast.error(`Failed: ${errorMessage}`)
      console.error('Upload error:', error)
    }
  }

  const uploadAll = () => {
    const pendingFiles = files.filter((f) => f.status === 'pending')
    pendingFiles.forEach(uploadFile)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'error':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
      case 'uploading':
      case 'validating':
        return <ArrowPathIcon className="h-5 w-5 text-primary-500 animate-spin" />
      default:
        return <DocumentIcon className="h-5 w-5 text-gray-400" />
    }
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Upload Data</h1>
        <p className="mt-1 text-sm text-gray-600">
          Upload your sales data, marketing spend, and other datasets for analysis.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Area */}
        <div className="lg:col-span-2 space-y-6">
          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
            }`}
          >
            <input {...getInputProps()} />
            <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-4 text-sm font-medium text-gray-900">
              {isDragActive ? 'Drop files here' : 'Drag and drop files here'}
            </p>
            <p className="mt-1 text-sm text-gray-500">or click to browse</p>
            <p className="mt-2 text-xs text-gray-400">
              Supported formats: {uploadConfig.allowedExtensions.join(', ')} - Max {uploadConfig.maxFileSizeDisplay} per file
            </p>
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="bg-white shadow rounded-lg">
              <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                <h2 className="text-lg font-medium text-gray-900">Files ({files.length})</h2>
                {files.some((f) => f.status === 'pending') && (
                  <button onClick={uploadAll} className="btn btn-primary btn-sm">
                    Upload all
                  </button>
                )}
              </div>

              <ul className="divide-y divide-gray-200">
                {files.map((f) => (
                  <li key={f.id} className="px-6 py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center min-w-0 flex-1">
                        {getStatusIcon(f.status)}
                        <div className="ml-3 min-w-0 flex-1">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {f.file.name}
                          </p>
                          <p className="text-sm text-gray-500">
                            {formatFileSize(f.file.size)}
                            {f.status === 'validating' && ' - Validating...'}
                            {f.status === 'uploading' && ' - Uploading...'}
                            {f.status === 'success' && ' - Uploaded'}
                            {f.status === 'error' && ` - ${f.error}`}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        {f.status === 'pending' && (
                          <button
                            onClick={() => uploadFile(f)}
                            className="btn btn-outline btn-sm"
                          >
                            Upload
                          </button>
                        )}
                        {f.status === 'success' && f.preview && (
                          <button
                            onClick={() => setSelectedFile(f)}
                            className="btn btn-outline btn-sm"
                          >
                            Preview
                          </button>
                        )}
                        <button
                          onClick={() => removeFile(f.id)}
                          className="p-1 text-gray-400 hover:text-red-500"
                        >
                          <XMarkIcon className="h-5 w-5" />
                        </button>
                      </div>
                    </div>

                    {(f.status === 'uploading' || f.status === 'validating') && (
                      <div className="mt-2">
                        <div className="bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${f.progress}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Instructions */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Upload Guidelines</h3>
            {configLoading ? (
              <div className="flex items-center justify-center py-4">
                <ArrowPathIcon className="h-5 w-5 text-gray-400 animate-spin" />
                <span className="ml-2 text-sm text-gray-500">Loading...</span>
              </div>
            ) : (
              <ul className="space-y-3 text-sm text-gray-600">
                {uploadConfig.guidelines.map((guideline, index) => (
                  <li key={index} className="flex items-start">
                    {guideline.type === 'required' ? (
                      <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                    ) : (
                      <InformationCircleIcon className="h-5 w-5 text-blue-500 mr-2 flex-shrink-0" />
                    )}
                    <span>{guideline.text}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Required Columns */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Data Columns</h3>
            {configLoading ? (
              <div className="flex items-center justify-center py-4">
                <ArrowPathIcon className="h-5 w-5 text-gray-400 animate-spin" />
                <span className="ml-2 text-sm text-gray-500">Loading...</span>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Required Columns */}
                {uploadConfig.requiredColumns.length > 0 && (
                  <div className="space-y-2">
                    {uploadConfig.requiredColumns.map((col: ColumnRequirement, index: number) => (
                      <div key={index} className="group">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-700 font-medium">{col.name}</span>
                          <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded capitalize">
                            {col.type}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5">{col.description}</p>
                        {col.examples.length > 0 && (
                          <p className="text-xs text-gray-400 mt-0.5">
                            e.g., {col.examples.join(', ')}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Optional Columns */}
                {uploadConfig.optionalColumns.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-gray-100">
                    {uploadConfig.optionalColumns.map((col: ColumnRequirement, index: number) => (
                      <div key={index} className="group">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600">{col.name}</span>
                          <span className={`text-xs px-2 py-0.5 rounded capitalize ${
                            col.type === 'recommended'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {col.type}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5">{col.description}</p>
                        {col.examples.length > 0 && (
                          <p className="text-xs text-gray-400 mt-0.5">
                            e.g., {col.examples.join(', ')}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sample Download */}
          <div className="bg-primary-50 rounded-lg p-6">
            <h3 className="text-lg font-medium text-primary-900 mb-2">Need a template?</h3>
            <p className="text-sm text-primary-700 mb-4">
              Download our sample template to ensure your data is formatted correctly.
            </p>
            <button onClick={downloadTemplate} className="btn btn-primary w-full">Download Template</button>
          </div>
        </div>
      </div>

      {/* Preview Modal */}
      {selectedFile?.preview && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75" onClick={() => setSelectedFile(null)} />
            <div className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                <h3 className="text-lg font-medium text-gray-900">
                  Data Preview: {selectedFile.file.name}
                </h3>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="text-gray-400 hover:text-gray-500"
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>

              <div className="p-6 overflow-auto max-h-[60vh]">
                {/* Validation Warnings */}
                {selectedFile.validationWarnings && selectedFile.validationWarnings.length > 0 && (
                  <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <h4 className="text-sm font-medium text-yellow-800 mb-2">Warnings</h4>
                    <ul className="list-disc list-inside text-sm text-yellow-700">
                      {selectedFile.validationWarnings.map((warning, i) => (
                        <li key={i}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Detected Columns */}
                {selectedFile.detectedColumns && (
                  <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h4 className="text-sm font-medium text-blue-800 mb-3">Detected Column Types</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      {selectedFile.detectedColumns.dateColumns.length > 0 && (
                        <div>
                          <span className="font-medium text-blue-700">Date Columns:</span>
                          <p className="text-blue-600">{selectedFile.detectedColumns.dateColumns.join(', ')}</p>
                        </div>
                      )}
                      {selectedFile.detectedColumns.potentialTarget && (
                        <div>
                          <span className="font-medium text-green-700">Target Column:</span>
                          <p className="text-green-600">{selectedFile.detectedColumns.potentialTarget}</p>
                        </div>
                      )}
                      {selectedFile.detectedColumns.potentialSpendColumns.length > 0 && (
                        <div>
                          <span className="font-medium text-purple-700">Spend Columns:</span>
                          <p className="text-purple-600">{selectedFile.detectedColumns.potentialSpendColumns.join(', ')}</p>
                        </div>
                      )}
                      {selectedFile.detectedColumns.numericColumns.length > 0 && (
                        <div>
                          <span className="font-medium text-gray-700">Numeric Columns:</span>
                          <p className="text-gray-600">{selectedFile.detectedColumns.numericColumns.slice(0, 5).join(', ')}{selectedFile.detectedColumns.numericColumns.length > 5 ? ` +${selectedFile.detectedColumns.numericColumns.length - 5} more` : ''}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <p className="text-sm text-gray-500 mb-4">
                  Showing first 10 of {selectedFile.preview.totalRows.toLocaleString()} rows
                </p>

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        {selectedFile.preview.columns.map((col) => (
                          <th
                            key={col}
                            className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {selectedFile.preview.rows.map((row, i) => (
                        <tr key={i}>
                          {selectedFile.preview!.columns.map((col) => (
                            <td key={col} className="px-4 py-2 text-sm text-gray-900 whitespace-nowrap">
                              {row[col]}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
                <button onClick={() => setSelectedFile(null)} className="btn btn-outline">
                  Close
                </button>
                <button className="btn btn-primary">Configure Dataset</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
