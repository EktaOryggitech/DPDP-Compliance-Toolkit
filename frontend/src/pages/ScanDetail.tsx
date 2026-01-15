import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { scansApi, findingsApi, reportsApi } from '../lib/api'
import {
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  DocumentArrowDownIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

const severityConfig = {
  critical: {
    icon: ExclamationCircleIcon,
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
  },
  high: {
    icon: ExclamationTriangleIcon,
    color: 'text-orange-600',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
  },
  medium: {
    icon: InformationCircleIcon,
    color: 'text-yellow-600',
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
  },
  low: {
    icon: CheckCircleIcon,
    color: 'text-green-600',
    bg: 'bg-green-50',
    border: 'border-green-200',
  },
}

export default function ScanDetail() {
  const { scanId } = useParams<{ scanId: string }>()

  const { data: scan, isLoading: scanLoading } = useQuery({
    queryKey: ['scan', scanId],
    queryFn: () => scansApi.get(scanId!),
    enabled: !!scanId,
  })

  const { data: groupedFindings, isLoading: findingsLoading } = useQuery({
    queryKey: ['findings', scanId, 'grouped'],
    queryFn: () => findingsApi.getGrouped(scanId!),
    enabled: !!scanId,
  })

  const downloadPdf = async () => {
    try {
      const blob = await reportsApi.downloadPdf(scanId!)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `dpdp_compliance_report_${scanId}.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      toast.error('Failed to download PDF report')
    }
  }

  const downloadExcel = async () => {
    try {
      const blob = await reportsApi.downloadExcel(scanId!)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `dpdp_compliance_report_${scanId}.xlsx`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      toast.error('Failed to download Excel report')
    }
  }

  if (scanLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading scan details...</div>
      </div>
    )
  }

  if (!scan) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Scan not found</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Scan: {scan.application_name}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {scan.scan_type} scan started on{' '}
            {new Date(scan.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={downloadPdf}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <DocumentArrowDownIcon className="-ml-1 mr-2 h-5 w-5 text-gray-500" />
            Download PDF
          </button>
          <button
            onClick={downloadExcel}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <DocumentArrowDownIcon className="-ml-1 mr-2 h-5 w-5 text-gray-500" />
            Download Excel
          </button>
        </div>
      </div>

      {/* Scan Summary */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Scan Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div>
            <dt className="text-sm font-medium text-gray-500">Status</dt>
            <dd className="mt-1">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  scan.status === 'completed'
                    ? 'bg-green-100 text-green-800'
                    : scan.status === 'running'
                    ? 'bg-blue-100 text-blue-800'
                    : scan.status === 'failed'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {scan.status}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Pages Scanned</dt>
            <dd className="mt-1 text-2xl font-semibold text-gray-900">
              {scan.pages_scanned}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Total Findings</dt>
            <dd className="mt-1 text-2xl font-semibold text-gray-900">
              {scan.findings_count}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Compliance Score</dt>
            <dd
              className={`mt-1 text-2xl font-semibold ${
                (scan.compliance_score || 0) >= 80
                  ? 'text-green-600'
                  : (scan.compliance_score || 0) >= 60
                  ? 'text-yellow-600'
                  : 'text-red-600'
              }`}
            >
              {scan.compliance_score !== undefined ? `${scan.compliance_score}%` : '-'}
            </dd>
          </div>
        </div>
      </div>

      {/* Findings by Section */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">
            Findings by DPDP Section
          </h2>
        </div>
        <div className="p-6">
          {findingsLoading ? (
            <div className="text-center text-gray-500">Loading findings...</div>
          ) : groupedFindings?.sections ? (
            <div className="space-y-6">
              {Object.entries(groupedFindings.sections).map(
                ([section, findings]: [string, any]) => (
                  <div key={section}>
                    <h3 className="text-md font-medium text-gray-900 mb-3">
                      {section} ({findings.length} findings)
                    </h3>
                    <div className="space-y-3">
                      {findings.map((finding: any) => {
                        const config =
                          severityConfig[
                            finding.severity as keyof typeof severityConfig
                          ] || severityConfig.low
                        const Icon = config.icon

                        return (
                          <div
                            key={finding.id}
                            className={`p-4 rounded-lg border ${config.border} ${config.bg}`}
                          >
                            <div className="flex items-start">
                              <Icon
                                className={`h-5 w-5 ${config.color} mt-0.5`}
                                aria-hidden="true"
                              />
                              <div className="ml-3 flex-1">
                                <h4 className="text-sm font-medium text-gray-900">
                                  {finding.title}
                                </h4>
                                <p className="mt-1 text-sm text-gray-600">
                                  {finding.description}
                                </p>
                                {finding.page_url && (
                                  <p className="mt-1 text-xs text-gray-500">
                                    Found on: {finding.page_url}
                                  </p>
                                )}
                                {finding.remediation && (
                                  <div className="mt-2 p-2 bg-white rounded border">
                                    <p className="text-xs font-medium text-gray-700">
                                      Remediation:
                                    </p>
                                    <p className="text-xs text-gray-600">
                                      {finding.remediation}
                                    </p>
                                  </div>
                                )}
                              </div>
                              <span
                                className={`ml-4 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${config.bg} ${config.color}`}
                              >
                                {finding.severity}
                              </span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              )}
            </div>
          ) : (
            <div className="text-center text-gray-500">No findings yet</div>
          )}
        </div>
      </div>
    </div>
  )
}
