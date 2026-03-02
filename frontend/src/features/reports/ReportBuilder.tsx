import { useState, useEffect } from 'react'
import {
  DocumentTextIcon,
  DocumentArrowDownIcon,
  CalendarIcon,
  ChartBarIcon,
  TableCellsIcon,
  PhotoIcon,
  PlusIcon,
  TrashIcon,
  ArrowPathIcon,
  ClockIcon,
  CheckCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import {
  useScheduledReports,
  useReportMutations,
  useExport,
} from '@/hooks/useReports'

interface ReportTemplate {
  id: string
  name: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  sections: string[]
}

interface ScheduleFormData {
  name: string
  scheduleType: 'daily' | 'weekly' | 'monthly'
  recipients: string
  exportFormat: string
}

const templates: ReportTemplate[] = [
  {
    id: 'executive',
    name: 'Executive Summary',
    description: 'High-level overview of marketing performance and ROI',
    icon: DocumentTextIcon,
    sections: ['KPI Summary', 'Channel Performance', 'Top Insights'],
  },
  {
    id: 'channel',
    name: 'Channel Analysis',
    description: 'Detailed breakdown of each marketing channel',
    icon: ChartBarIcon,
    sections: ['Channel Metrics', 'Response Curves', 'Attribution'],
  },
  {
    id: 'forecast',
    name: 'Forecast Report',
    description: 'Sales forecasts and predictions',
    icon: CalendarIcon,
    sections: ['Forecast Summary', 'Trends', 'Confidence Intervals'],
  },
  {
    id: 'custom',
    name: 'Custom Report',
    description: 'Build a report from scratch',
    icon: TableCellsIcon,
    sections: [],
  },
]

const scheduleTypeLabels: Record<string, string> = {
  daily: 'Daily',
  weekly: 'Every week',
  monthly: '1st of every month',
}

const reportSections = [
  { id: 'kpi', name: 'KPI Summary', icon: ChartBarIcon },
  { id: 'channel', name: 'Channel Performance', icon: ChartBarIcon },
  { id: 'attribution', name: 'Attribution Analysis', icon: TableCellsIcon },
  { id: 'forecast', name: 'Forecasts', icon: CalendarIcon },
  { id: 'response', name: 'Response Curves', icon: ChartBarIcon },
  { id: 'insights', name: 'AI Insights', icon: DocumentTextIcon },
  { id: 'custom', name: 'Custom Chart', icon: PhotoIcon },
]

export function ReportBuilder() {
  const [selectedTemplate, setSelectedTemplate] = useState<ReportTemplate | null>(null)
  const [selectedSections, setSelectedSections] = useState<string[]>([])
  const [reportName, setReportName] = useState('')
  const [activeTab, setActiveTab] = useState<'create' | 'scheduled'>('create')
  const [showScheduleModal, setShowScheduleModal] = useState(false)
  const [scheduleForm, setScheduleForm] = useState<ScheduleFormData>({
    name: '',
    scheduleType: 'weekly',
    recipients: '',
    exportFormat: 'pdf',
  })
  const [currentExportId, setCurrentExportId] = useState<string | null>(null)

  // Hooks
  const { scheduledReports, loading: scheduledLoading, refetch: refetchScheduled } = useScheduledReports()
  const { createReport, generateReport, scheduleReport, cancelScheduledReport, loading: mutationLoading, result: exportResult } = useReportMutations()
  const { export: exportData } = useExport(currentExportId || undefined, { pollInterval: 2000 })

  const isGenerating = mutationLoading || (exportData?.status === 'pending' || exportData?.status === 'processing')

  // Handle export completion
  useEffect(() => {
    if (exportData?.status === 'completed' && exportData.downloadUrl) {
      toast.success('Report generated successfully!')
      // Trigger download
      window.open(exportData.downloadUrl, '_blank')
      setCurrentExportId(null)
    } else if (exportData?.status === 'failed') {
      toast.error(exportData.errorMessage || 'Failed to generate report')
      setCurrentExportId(null)
    }
  }, [exportData?.status, exportData?.downloadUrl, exportData?.errorMessage])

  const handleTemplateSelect = (template: ReportTemplate) => {
    setSelectedTemplate(template)
    setSelectedSections(template.sections.map((s) => s.toLowerCase().replace(/\s+/g, '-')))
    setReportName(`${template.name} - ${new Date().toLocaleDateString()}`)
  }

  const toggleSection = (sectionId: string) => {
    setSelectedSections((prev) =>
      prev.includes(sectionId)
        ? prev.filter((s) => s !== sectionId)
        : [...prev, sectionId]
    )
  }

  const handleGenerate = async (format: 'pdf' | 'excel' | 'pptx') => {
    if (!selectedTemplate) return

    try {
      // First, create the report in the database
      const reportDisplayName = reportName || selectedTemplate.name
      const createdReport = await createReport({
        name: reportDisplayName,
        description: selectedTemplate.description,
        reportType: selectedTemplate.id,
        sections: selectedSections,
        availableFormats: ['pdf', 'excel', 'pptx'],
      })

      if (!createdReport) {
        toast.error('Failed to create report')
        return
      }

      // Then generate the report
      const result = await generateReport({
        reportId: createdReport.id,
        exportFormat: format,
        parameters: {
          name: reportDisplayName,
          sections: selectedSections,
        },
      })

      if (result?.exportId) {
        setCurrentExportId(result.exportId)
        toast.loading('Generating report...', { id: 'report-generate' })
      } else if (result?.downloadUrl) {
        toast.success(`Report generated as ${format.toUpperCase()}!`)
        window.open(result.downloadUrl, '_blank')
      }
    } catch (error) {
      toast.error('Failed to generate report')
    }
  }

  const handleScheduleSubmit = async () => {
    if (!selectedTemplate) return

    try {
      const recipients = scheduleForm.recipients.split(',').map(r => r.trim()).filter(Boolean)
      if (recipients.length === 0) {
        toast.error('Please enter at least one recipient email')
        return
      }

      // First, create the report in the database
      const reportName = scheduleForm.name || `${selectedTemplate.name} - Scheduled`
      const createdReport = await createReport({
        name: reportName,
        description: selectedTemplate.description,
        reportType: selectedTemplate.id, // 'executive', 'channel', 'forecast', 'custom'
        sections: selectedSections,
        availableFormats: ['pdf', 'excel', 'pptx'],
      })

      if (!createdReport) {
        toast.error('Failed to create report template')
        return
      }

      // Then schedule the created report
      await scheduleReport({
        reportId: createdReport.id,
        name: reportName,
        scheduleType: scheduleForm.scheduleType,
        recipients,
        exportFormat: scheduleForm.exportFormat,
      })

      toast.success('Report scheduled successfully!')
      setShowScheduleModal(false)
      setScheduleForm({ name: '', scheduleType: 'weekly', recipients: '', exportFormat: 'pdf' })
      refetchScheduled()
    } catch (error) {
      toast.error('Failed to schedule report')
    }
  }

  const handleDeleteSchedule = async (scheduleId: string) => {
    if (!confirm('Are you sure you want to cancel this scheduled report?')) return

    try {
      await cancelScheduledReport(scheduleId)
      toast.success('Scheduled report cancelled')
      refetchScheduled()
    } catch (error) {
      toast.error('Failed to cancel scheduled report')
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="mt-1 text-sm text-gray-600">
          Generate custom reports and schedule automated report delivery.
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('create')}
            className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'create'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Create Report
          </button>
          <button
            onClick={() => setActiveTab('scheduled')}
            className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'scheduled'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Scheduled Reports
          </button>
        </nav>
      </div>

      {activeTab === 'create' ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Template Selection */}
          <div className="lg:col-span-2">
            {!selectedTemplate ? (
              <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Select a Template</h2>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {templates.map((template) => (
                    <button
                      key={template.id}
                      onClick={() => handleTemplateSelect(template)}
                      className="flex items-start p-4 border rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors text-left"
                    >
                      <template.icon className="h-8 w-8 text-primary-600 flex-shrink-0" />
                      <div className="ml-4">
                        <h3 className="text-sm font-medium text-gray-900">{template.name}</h3>
                        <p className="mt-1 text-sm text-gray-500">{template.description}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="bg-white shadow rounded-lg p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-lg font-medium text-gray-900">Report Configuration</h2>
                    <button
                      onClick={() => setSelectedTemplate(null)}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      Change template
                    </button>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label htmlFor="reportName" className="label">
                        Report Name
                      </label>
                      <input
                        id="reportName"
                        type="text"
                        value={reportName}
                        onChange={(e) => setReportName(e.target.value)}
                        className="input"
                      />
                    </div>

                    <div>
                      <label className="label">Include Sections</label>
                      <div className="mt-2 grid grid-cols-2 gap-2">
                        {reportSections.map((section) => (
                          <label
                            key={section.id}
                            className={`flex items-center p-3 border rounded-lg cursor-pointer ${
                              selectedSections.includes(section.id)
                                ? 'border-primary-500 bg-primary-50'
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={selectedSections.includes(section.id)}
                              onChange={() => toggleSection(section.id)}
                              className="sr-only"
                            />
                            <section.icon className="h-5 w-5 text-gray-400 mr-2" />
                            <span className="text-sm text-gray-700">{section.name}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Preview */}
                <div className="bg-white shadow rounded-lg p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Preview</h3>
                  <div className="border rounded-lg p-4 bg-gray-50 min-h-[200px]">
                    <div className="text-center text-gray-500">
                      <DocumentTextIcon className="h-12 w-12 mx-auto text-gray-400" />
                      <p className="mt-2 text-sm">Report preview will appear here</p>
                      <p className="text-xs text-gray-400 mt-1">
                        {selectedSections.length} sections selected
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Export Panel */}
          <div className="space-y-6">
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Export Options</h3>
              <div className="space-y-3">
                <button
                  onClick={() => handleGenerate('pdf')}
                  disabled={!selectedTemplate || isGenerating}
                  className="btn btn-primary w-full justify-center disabled:opacity-50"
                >
                  {isGenerating ? (
                    <ArrowPathIcon className="h-5 w-5 mr-2 animate-spin" />
                  ) : (
                    <DocumentArrowDownIcon className="h-5 w-5 mr-2" />
                  )}
                  Export as PDF
                </button>
                <button
                  onClick={() => handleGenerate('excel')}
                  disabled={!selectedTemplate || isGenerating}
                  className="btn btn-outline w-full justify-center disabled:opacity-50"
                >
                  <TableCellsIcon className="h-5 w-5 mr-2" />
                  Export as Excel
                </button>
                <button
                  onClick={() => handleGenerate('pptx')}
                  disabled={!selectedTemplate || isGenerating}
                  className="btn btn-outline w-full justify-center disabled:opacity-50"
                >
                  <PhotoIcon className="h-5 w-5 mr-2" />
                  Export as PowerPoint
                </button>
              </div>
            </div>

            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Schedule Report</h3>
              <p className="text-sm text-gray-500 mb-4">
                Set up automated report generation and delivery.
              </p>
              <button
                onClick={() => setShowScheduleModal(true)}
                disabled={!selectedTemplate}
                className="btn btn-outline w-full justify-center disabled:opacity-50"
              >
                <ClockIcon className="h-5 w-5 mr-2" />
                Schedule
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h2 className="text-lg font-medium text-gray-900">Scheduled Reports</h2>
            <button
              onClick={() => {
                setActiveTab('create')
                toast('Select a template first, then click Schedule')
              }}
              className="btn btn-primary btn-sm"
            >
              <PlusIcon className="h-4 w-4 mr-1" />
              New Schedule
            </button>
          </div>

          {scheduledLoading ? (
            <div className="p-12 text-center">
              <ArrowPathIcon className="mx-auto h-12 w-12 text-gray-400 animate-spin" />
              <p className="mt-2 text-sm text-gray-500">Loading scheduled reports...</p>
            </div>
          ) : scheduledReports.length === 0 ? (
            <div className="p-12 text-center">
              <ClockIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No scheduled reports</h3>
              <p className="mt-1 text-sm text-gray-500">
                Create a report and schedule it for automatic delivery.
              </p>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Report
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Schedule
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Run
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="relative px-6 py-3">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {scheduledReports.map((report) => (
                  <tr key={report.id}>
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{report.name}</p>
                        <p className="text-sm text-gray-500">{report.exportFormat.toUpperCase()}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {scheduleTypeLabels[report.scheduleType] || report.scheduleType}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {report.lastRunAt ? formatDate(report.lastRunAt) : 'Never'}
                    </td>
                    <td className="px-6 py-4">
                      {report.isActive ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          <CheckCircleIcon className="h-3 w-3 mr-1" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          Paused
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleDeleteSchedule(report.id)}
                        className="text-gray-400 hover:text-red-500"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Schedule Modal */}
      {showScheduleModal && selectedTemplate && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-screen items-center justify-center px-4">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75" onClick={() => setShowScheduleModal(false)} />
            <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-gray-900">Schedule Report</h3>
                <button onClick={() => setShowScheduleModal(false)} className="text-gray-400 hover:text-gray-600">
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="label">Report Template</label>
                  <p className="text-sm text-gray-600">{selectedTemplate.name}</p>
                </div>

                <div>
                  <label htmlFor="scheduleName" className="label">Schedule Name</label>
                  <input
                    id="scheduleName"
                    type="text"
                    className="input"
                    placeholder={`${selectedTemplate.name} - Weekly`}
                    value={scheduleForm.name}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, name: e.target.value })}
                  />
                </div>

                <div>
                  <label htmlFor="scheduleType" className="label">Frequency</label>
                  <select
                    id="scheduleType"
                    className="input"
                    value={scheduleForm.scheduleType}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, scheduleType: e.target.value as 'daily' | 'weekly' | 'monthly' })}
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="exportFormat" className="label">Export Format</label>
                  <select
                    id="exportFormat"
                    className="input"
                    value={scheduleForm.exportFormat}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, exportFormat: e.target.value })}
                  >
                    <option value="pdf">PDF</option>
                    <option value="excel">Excel</option>
                    <option value="pptx">PowerPoint</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="recipients" className="label">Recipients (comma-separated emails)</label>
                  <input
                    id="recipients"
                    type="text"
                    className="input"
                    placeholder="email@example.com, email2@example.com"
                    value={scheduleForm.recipients}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, recipients: e.target.value })}
                  />
                </div>
              </div>

              <div className="mt-6 flex justify-end space-x-3">
                <button onClick={() => setShowScheduleModal(false)} className="btn btn-outline">
                  Cancel
                </button>
                <button onClick={handleScheduleSubmit} disabled={mutationLoading} className="btn btn-primary">
                  {mutationLoading ? 'Scheduling...' : 'Create Schedule'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
