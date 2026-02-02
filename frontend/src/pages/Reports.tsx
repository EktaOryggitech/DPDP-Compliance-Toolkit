import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { DocumentArrowDownIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { scansApi, reportsApi } from '../lib/api'

const PAGE_SIZE_OPTIONS = [5, 10, 20, 50, 100]
const DEFAULT_PAGE_SIZE = 5

export default function Reports() {
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)

  const { data: scans, isLoading } = useQuery({
    queryKey: ['scans', 'completed'],
    queryFn: () => scansApi.list({ status: 'completed', limit: 1000 }),
  })

  // Paginate data
  const paginatedData = useMemo(() => {
    if (!scans?.items) return []
    const start = (currentPage - 1) * pageSize
    return scans.items.slice(start, start + pageSize)
  }, [scans?.items, currentPage, pageSize])

  const totalItems = scans?.items?.length || 0
  const totalPages = Math.ceil(totalItems / pageSize)

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize)
    setCurrentPage(1)
  }

  const downloadPdf = async (scanId: string) => {
    try {
      const blob = await reportsApi.downloadPdf(scanId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `dpdp_compliance_report_${scanId}.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
      toast.success('PDF report downloaded')
    } catch (error) {
      toast.error('Failed to download PDF report')
    }
  }

  const downloadExcel = async (scanId: string) => {
    try {
      const blob = await reportsApi.downloadExcel(scanId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `dpdp_compliance_report_${scanId}.xlsx`
      a.click()
      window.URL.revokeObjectURL(url)
      toast.success('Excel report downloaded')
    } catch (error) {
      toast.error('Failed to download Excel report')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="mt-1 text-sm text-gray-500">
          Download compliance reports for completed scans
        </p>
      </div>

      {/* Reports List */}
      <div className="bg-white shadow overflow-hidden rounded-lg">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : totalItems > 0 ? (
          <>
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Application
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Scan Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Findings
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Compliance Score
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Download
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {paginatedData.map((scan: any) => (
                  <tr key={scan.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {scan.application_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(scan.completed_at || scan.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {scan.findings_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {scan.overall_score !== undefined ? (
                        <span
                          className={`text-sm font-medium ${
                            scan.overall_score >= 80
                              ? 'text-green-600'
                              : scan.overall_score >= 60
                              ? 'text-yellow-600'
                              : 'text-red-600'
                          }`}
                        >
                          {scan.overall_score}%
                        </span>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => downloadPdf(scan.id)}
                        className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm text-gray-700 bg-white hover:bg-gray-50 mr-2"
                      >
                        <DocumentArrowDownIcon className="h-4 w-4 mr-1" />
                        PDF
                      </button>
                      <button
                        onClick={() => downloadExcel(scan.id)}
                        className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm text-gray-700 bg-white hover:bg-gray-50"
                      >
                        <DocumentArrowDownIcon className="h-4 w-4 mr-1" />
                        Excel
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">Show</span>
                  <select
                    value={pageSize}
                    onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                    className="border border-gray-300 rounded-md text-sm py-1 px-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    {PAGE_SIZE_OPTIONS.map(size => (
                      <option key={size} value={size}>{size}</option>
                    ))}
                  </select>
                  <span className="text-sm text-gray-500">per page</span>
                </div>
                <div className="text-sm text-gray-500">
                  Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalItems)} of {totalItems} reports
                </div>
              </div>
              {totalPages > 1 && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="p-2 rounded-md border border-gray-300 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeftIcon className="h-4 w-4" />
                  </button>
                  <span className="text-sm text-gray-700">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="p-2 rounded-md border border-gray-300 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRightIcon className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="p-8 text-center text-gray-500">
            No completed scans available. Reports can be generated after a scan completes.
          </div>
        )}
      </div>

      {/* Report Types Info */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Report Formats</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="border rounded-lg p-4">
            <h3 className="font-medium text-gray-900">PDF Report</h3>
            <p className="mt-1 text-sm text-gray-500">
              Professional PDF compliance report suitable for management review and audit purposes.
              Includes executive summary, compliance scores, detailed findings with evidence, and
              remediation recommendations.
            </p>
          </div>
          <div className="border rounded-lg p-4">
            <h3 className="font-medium text-gray-900">Excel Report</h3>
            <p className="mt-1 text-sm text-gray-500">
              Detailed Excel workbook with multiple sheets for data analysis. Includes findings
              breakdown, DPDP section mapping, evidence references, and trend analysis. Ideal for
              technical teams and detailed remediation planning.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
