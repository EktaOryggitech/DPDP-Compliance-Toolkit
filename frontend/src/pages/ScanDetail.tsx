import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { scansApi, findingsApi, reportsApi } from '../lib/api'
import {
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  DocumentArrowDownIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ChevronLeftIcon,
  GlobeAltIcon,
  CodeBracketIcon,
  WrenchScrewdriverIcon,
  CurrencyRupeeIcon,
  BookOpenIcon,
  ArrowLeftIcon,
  PhotoIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

// Screenshot lightbox modal - uses direct image URL
function ScreenshotModal({ url, onClose }: { url: string; onClose: () => void }) {
  const [imageError, setImageError] = useState(false)
  const [imageLoading, setImageLoading] = useState(true)

  // Build the full image URL
  const getImageUrl = () => {
    // If it's already a full URL, use it
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url
    }
    // If it's a relative URL, prepend the API base
    if (url.startsWith('/api/v1')) {
      return `http://localhost:8000${url}`
    }
    if (url.startsWith('/')) {
      return `http://localhost:8000/api/v1${url}`
    }
    return `http://localhost:8000/api/v1/${url}`
  }

  const imageUrl = getImageUrl()

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75"
      onClick={onClose}
    >
      <div className="relative max-w-6xl max-h-[90vh] overflow-auto">
        <button
          onClick={onClose}
          className="absolute top-2 right-2 p-2 bg-white rounded-full shadow-lg hover:bg-gray-100 z-10"
        >
          <XMarkIcon className="h-6 w-6 text-gray-700" />
        </button>
        {imageLoading && !imageError && (
          <div className="flex items-center justify-center p-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
          </div>
        )}
        {imageError ? (
          <div className="bg-white p-8 rounded-lg text-center">
            <p className="text-red-600 font-medium">Failed to load screenshot</p>
            <p className="text-gray-500 text-sm mt-2 break-all">URL: {imageUrl}</p>
            <button
              onClick={onClose}
              className="mt-4 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
            >
              Close
            </button>
          </div>
        ) : (
          <img
            src={imageUrl}
            alt="Violation Screenshot"
            className={`max-w-full h-auto rounded-lg shadow-2xl ${imageLoading ? 'hidden' : ''}`}
            onClick={(e) => e.stopPropagation()}
            onLoad={() => setImageLoading(false)}
            onError={() => {
              setImageError(true)
              setImageLoading(false)
            }}
          />
        )}
      </div>
    </div>
  )
}

// Component to display detailed finding information
function FindingDetail({ finding }: { finding: any }) {
  const [showDetails, setShowDetails] = useState(false)
  const [showScreenshot, setShowScreenshot] = useState(false)
  const extra = finding.extra_data || {}

  const hasExtraData = extra.code_before || extra.code_after || extra.code_fix_example ||
                       extra.fix_steps || extra.penalty_risk || extra.visual_representation || extra.dpdp_reference

  const hasScreenshot = finding.screenshot_url || finding.screenshot_path

  return (
    <div className="mt-3">
      {/* Screenshot Modal */}
      {showScreenshot && finding.screenshot_url && (
        <ScreenshotModal url={finding.screenshot_url} onClose={() => setShowScreenshot(false)} />
      )}

      {/* Quick info row */}
      <div className="flex flex-wrap gap-2 mb-2">
        {extra.penalty_risk && (
          <span className="inline-flex items-center px-2 py-1 rounded text-xs bg-red-100 text-red-700">
            <CurrencyRupeeIcon className="h-3 w-3 mr-1" />
            Penalty: {extra.penalty_risk}
          </span>
        )}
        {finding.dpdp_section && (
          <span className="inline-flex items-center px-2 py-1 rounded text-xs bg-indigo-100 text-indigo-700">
            <BookOpenIcon className="h-3 w-3 mr-1" />
            {finding.dpdp_section}
          </span>
        )}
        {hasScreenshot && (
          <button
            onClick={() => setShowScreenshot(true)}
            className="inline-flex items-center px-2 py-1 rounded text-xs bg-blue-100 text-blue-700 hover:bg-blue-200"
          >
            <PhotoIcon className="h-3 w-3 mr-1" />
            View Screenshot
          </button>
        )}
      </div>

      {/* Remediation */}
      {finding.remediation && (
        <div className="mt-2 p-2 bg-white rounded border border-gray-200">
          <p className="text-xs font-semibold text-gray-700 flex items-center">
            <WrenchScrewdriverIcon className="h-4 w-4 mr-1 text-green-600" />
            Remediation:
          </p>
          <p className="text-xs text-gray-600 mt-1">{finding.remediation}</p>
        </div>
      )}

      {/* Show Details Button */}
      {hasExtraData && (
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="mt-2 text-xs text-indigo-600 hover:text-indigo-800 flex items-center"
        >
          {showDetails ? (
            <>
              <ChevronDownIcon className="h-4 w-4 mr-1" />
              Hide Details
            </>
          ) : (
            <>
              <ChevronRightIcon className="h-4 w-4 mr-1" />
              Show Code Fix & Details
            </>
          )}
        </button>
      )}

      {/* Detailed Information */}
      {showDetails && hasExtraData && (
        <div className="mt-3 space-y-3 border-t pt-3">
          {/* DPDP Reference */}
          {extra.dpdp_reference && (
            <div className="p-2 bg-indigo-50 rounded border border-indigo-200">
              <p className="text-xs font-semibold text-indigo-800">DPDP Reference:</p>
              <div className="text-xs text-indigo-700 mt-1">
                <p><strong>Section:</strong> {extra.dpdp_reference.section}</p>
                <p><strong>Requirement:</strong> {extra.dpdp_reference.requirement}</p>
                <p><strong>Penalty:</strong> {extra.dpdp_reference.penalty}</p>
              </div>
            </div>
          )}

          {/* Code Before/After */}
          {(extra.code_before || extra.code_after) && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-700 flex items-center">
                <CodeBracketIcon className="h-4 w-4 mr-1 text-blue-600" />
                Code Fix:
              </p>
              {extra.code_before && (
                <div>
                  <p className="text-xs text-red-600 font-medium">Before (Violation):</p>
                  <pre className="mt-1 p-2 bg-red-50 border border-red-200 rounded text-xs overflow-x-auto whitespace-pre-wrap">
                    {extra.code_before}
                  </pre>
                </div>
              )}
              {extra.code_after && (
                <div>
                  <p className="text-xs text-green-600 font-medium">After (Compliant):</p>
                  <pre className="mt-1 p-2 bg-green-50 border border-green-200 rounded text-xs overflow-x-auto whitespace-pre-wrap">
                    {extra.code_after}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Code Fix Example */}
          {extra.code_fix_example && (
            <div>
              <p className="text-xs font-semibold text-gray-700">Code Fix Example:</p>
              <pre className="mt-1 p-2 bg-gray-100 border rounded text-xs overflow-x-auto whitespace-pre-wrap">
                {extra.code_fix_example}
              </pre>
            </div>
          )}

          {/* Fix Steps */}
          {extra.fix_steps && extra.fix_steps.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-700 flex items-center">
                <WrenchScrewdriverIcon className="h-4 w-4 mr-1 text-green-600" />
                Fix Steps:
              </p>
              <ol className="mt-1 list-decimal list-inside text-xs text-gray-600 space-y-1">
                {extra.fix_steps.map((step: string, idx: number) => (
                  <li key={idx}>{step}</li>
                ))}
              </ol>
            </div>
          )}

          {/* Visual Representation */}
          {extra.visual_representation && (
            <div>
              <p className="text-xs font-semibold text-gray-700 mb-1">Visual Representation:</p>
              <pre
                className="p-4 bg-slate-900 text-emerald-400 rounded-lg text-sm overflow-x-auto shadow-inner border border-slate-700"
                style={{
                  fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', 'Monaco', monospace",
                  lineHeight: '1.4',
                  letterSpacing: '0.02em',
                }}
              >
                {extra.visual_representation}
              </pre>
            </div>
          )}

          {/* Element Selector */}
          {finding.element_selector && (
            <div>
              <p className="text-xs font-semibold text-gray-700">Element Detected:</p>
              <pre className="mt-1 p-2 bg-gray-100 border rounded text-xs overflow-x-auto whitespace-pre-wrap">
                {finding.element_selector}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

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

type ViewMode = 'section' | 'page'

const PAGE_SIZE_OPTIONS = [5, 10, 20, 50, 100]
const DEFAULT_PAGE_SIZE = 5

// Pagination options for DPDP sections (main section list)
const SECTION_PAGE_SIZE_OPTIONS = [2, 5, 10]
const DEFAULT_SECTION_PAGE_SIZE = 2

// Pagination options for findings within each DPDP section
const SECTION_FINDING_PAGE_SIZE_OPTIONS = [1, 2, 3, 5]
const DEFAULT_SECTION_FINDING_PAGE_SIZE = 1

// Component to display findings within a section with pagination
function SectionFindings({ sectionData }: { sectionData: any }) {
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_SECTION_FINDING_PAGE_SIZE)

  const findings = sectionData.findings || []
  const totalPages = Math.ceil(findings.length / pageSize)
  const startIndex = (currentPage - 1) * pageSize
  const endIndex = startIndex + pageSize
  const paginatedFindings = findings.slice(startIndex, endIndex)

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize)
    setCurrentPage(1)
  }

  return (
    <div key={sectionData.section} className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <h3 className="text-md font-medium text-gray-900">
          {sectionData.section_name || sectionData.section} ({findings.length} finding{findings.length !== 1 ? 's' : ''})
        </h3>
      </div>
      <div className="p-4 space-y-3">
        {paginatedFindings.map((finding: any) => {
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
                  className={`h-5 w-5 ${config.color} mt-0.5 flex-shrink-0`}
                  aria-hidden="true"
                />
                <div className="ml-3 flex-1">
                  <div className="flex items-start justify-between">
                    <h4 className="text-sm font-medium text-gray-900">
                      {finding.title}
                    </h4>
                    <span
                      className={`ml-4 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${config.bg} ${config.color} flex-shrink-0`}
                    >
                      {finding.severity}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-gray-600">
                    {finding.description}
                  </p>
                  {finding.location && (
                    <p className="mt-1 text-xs text-gray-500">
                      Found on: {finding.location}
                    </p>
                  )}
                  {/* Detailed Finding Information */}
                  <FindingDetail finding={finding} />
                </div>
              </div>
            </div>
          )
        })}
      </div>
      {/* Section Findings Pagination Footer */}
      {findings.length > 1 && (
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Show</span>
              <select
                value={pageSize}
                onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                className="border border-gray-300 rounded-md text-xs py-1 px-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                {SECTION_FINDING_PAGE_SIZE_OPTIONS.map(size => (
                  <option key={size} value={size}>{size}</option>
                ))}
              </select>
              <span className="text-xs text-gray-500">per page</span>
            </div>
            <div className="text-xs text-gray-600">
              Showing {startIndex + 1} to {Math.min(endIndex, findings.length)} of {findings.length}
            </div>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-2 py-1 rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed text-xs"
              >
                Prev
              </button>
              <span className="text-xs text-gray-600">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-2 py-1 rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed text-xs"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ScanDetail() {
  const { scanId } = useParams<{ scanId: string }>()
  const navigate = useNavigate()
  const [viewMode, setViewMode] = useState<ViewMode>('page')
  const [expandedPages, setExpandedPages] = useState<Set<string>>(new Set())
  const [currentPage, setCurrentPage] = useState(1)
  const [currentSectionPage, setCurrentSectionPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [sectionPageSize, setSectionPageSize] = useState(DEFAULT_SECTION_PAGE_SIZE)

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize)
    setCurrentPage(1)
  }

  const handleSectionPageSizeChange = (newSize: number) => {
    setSectionPageSize(newSize)
    setCurrentSectionPage(1)
  }

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

  const togglePageExpand = (pageUrl: string) => {
    setExpandedPages(prev => {
      const newSet = new Set(prev)
      if (newSet.has(pageUrl)) {
        newSet.delete(pageUrl)
      } else {
        newSet.add(pageUrl)
      }
      return newSet
    })
  }

  const expandAllPages = () => {
    if (scan?.findings_by_page) {
      setExpandedPages(new Set(scan.findings_by_page.map((p: any) => p.page_url)))
    }
  }

  const collapseAllPages = () => {
    setExpandedPages(new Set())
  }

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
        <div className="flex items-start gap-4">
          <button
            onClick={() => navigate('/scans')}
            className="mt-1 p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            title="Back to Scans"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Scan: {scan.application_name}
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              {scan.scan_type} scan started on{' '}
              {new Date(scan.created_at).toLocaleString()}
            </p>
          </div>
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
              {scan.status === 'failed' && scan.status_message && (
                <p className="mt-2 text-sm text-red-600">{scan.status_message}</p>
              )}
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
                (scan.overall_score || 0) >= 80
                  ? 'text-green-600'
                  : (scan.overall_score || 0) >= 60
                  ? 'text-yellow-600'
                  : 'text-red-600'
              }`}
            >
              {scan.overall_score !== undefined ? `${scan.overall_score}%` : '-'}
            </dd>
          </div>
        </div>
      </div>

      {/* Findings View Tabs */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <div className="flex space-x-4">
              <button
                onClick={() => { setViewMode('page'); setCurrentPage(1); setCurrentSectionPage(1); }}
                className={`px-4 py-2 text-sm font-medium rounded-md ${
                  viewMode === 'page'
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                }`}
              >
                <GlobeAltIcon className="h-4 w-4 inline-block mr-1" />
                By Page/Navigation
              </button>
              <button
                onClick={() => { setViewMode('section'); setCurrentPage(1); setCurrentSectionPage(1); }}
                className={`px-4 py-2 text-sm font-medium rounded-md ${
                  viewMode === 'section'
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                }`}
              >
                By DPDP Section
              </button>
            </div>
            {viewMode === 'page' && scan?.findings_by_page && scan.findings_by_page.length > 0 && (
              <div className="flex space-x-2">
                <button
                  onClick={expandAllPages}
                  className="text-xs text-indigo-600 hover:text-indigo-800"
                >
                  Expand All
                </button>
                <span className="text-gray-300">|</span>
                <button
                  onClick={collapseAllPages}
                  className="text-xs text-indigo-600 hover:text-indigo-800"
                >
                  Collapse All
                </button>
              </div>
            )}
          </div>
        </div>
        <div className="p-6">
          {/* Findings by Page View */}
          {viewMode === 'page' && (
            <>
              {scan?.findings_by_page && scan.findings_by_page.length > 0 ? (
                <div className="space-y-4">
                  {(() => {
                    const totalPages = Math.ceil(scan.findings_by_page.length / pageSize)
                    const startIndex = (currentPage - 1) * pageSize
                    const endIndex = startIndex + pageSize
                    const paginatedPages = scan.findings_by_page.slice(startIndex, endIndex)

                    return (
                      <>
                        {/* Page List */}
                        {paginatedPages.map((pageData: any) => {
                    const isExpanded = expandedPages.has(pageData.page_url)
                    return (
                      <div
                        key={pageData.page_url}
                        className="border border-gray-200 rounded-lg overflow-hidden"
                      >
                        {/* Page Header - Collapsible */}
                        <button
                          onClick={() => togglePageExpand(pageData.page_url)}
                          className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between text-left"
                        >
                          <div className="flex items-center space-x-3">
                            {isExpanded ? (
                              <ChevronDownIcon className="h-5 w-5 text-gray-500" />
                            ) : (
                              <ChevronRightIcon className="h-5 w-5 text-gray-500" />
                            )}
                            <GlobeAltIcon className="h-5 w-5 text-indigo-500" />
                            <div>
                              <p className="text-sm font-medium text-gray-900 truncate max-w-lg">
                                {pageData.page_url}
                              </p>
                              <p className="text-xs text-gray-500">
                                {pageData.findings_count} finding(s)
                              </p>
                            </div>
                          </div>
                          <div className="flex space-x-2">
                            {pageData.critical_count > 0 && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">
                                {pageData.critical_count} Critical
                              </span>
                            )}
                            {pageData.high_count > 0 && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-700">
                                {pageData.high_count} High
                              </span>
                            )}
                            {pageData.medium_count > 0 && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-700">
                                {pageData.medium_count} Medium
                              </span>
                            )}
                            {pageData.low_count > 0 && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                                {pageData.low_count} Low
                              </span>
                            )}
                          </div>
                        </button>

                        {/* Findings List - Expandable */}
                        {isExpanded && (
                          <div className="p-4 space-y-3 bg-white">
                            {/* Sort findings by severity: critical > high > medium > low > info */}
                            {[...pageData.findings].sort((a: any, b: any) => {
                              const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
                              return (severityOrder[a.severity] ?? 5) - (severityOrder[b.severity] ?? 5)
                            }).map((finding: any) => {
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
                                      className={`h-5 w-5 ${config.color} mt-0.5 flex-shrink-0`}
                                      aria-hidden="true"
                                    />
                                    <div className="ml-3 flex-1">
                                      <div className="flex items-start justify-between">
                                        <h4 className="text-sm font-medium text-gray-900">
                                          {finding.title}
                                        </h4>
                                        <span
                                          className={`ml-4 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${config.bg} ${config.color} flex-shrink-0`}
                                        >
                                          {finding.severity}
                                        </span>
                                      </div>
                                      {finding.description && (
                                        <p className="mt-1 text-sm text-gray-600">
                                          {finding.description}
                                        </p>
                                      )}
                                      {/* Detailed Finding Information */}
                                      <FindingDetail finding={finding} />
                                    </div>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </div>
                        )
                      })}

                        {/* Bottom Pagination Footer */}
                        <div className="mt-6 pt-4 border-t border-gray-200 flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-gray-500">Show</span>
                              <select
                                value={pageSize}
                                onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                                className="border border-gray-300 rounded-md text-sm py-1 px-2 focus:ring-indigo-500 focus:border-indigo-500"
                              >
                                {PAGE_SIZE_OPTIONS.map(size => (
                                  <option key={size} value={size}>{size}</option>
                                ))}
                              </select>
                              <span className="text-sm text-gray-500">per page</span>
                            </div>
                            <div className="text-sm text-gray-600">
                              Showing {startIndex + 1} to {Math.min(endIndex, scan.findings_by_page.length)} of {scan.findings_by_page.length} pages
                            </div>
                          </div>
                          {totalPages > 1 && (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                disabled={currentPage === 1}
                                className="px-3 py-1 rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                              >
                                Prev
                              </button>
                              <span className="text-sm text-gray-600">
                                Page {currentPage} of {totalPages}
                              </span>
                              <button
                                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                disabled={currentPage === totalPages}
                                className="px-3 py-1 rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                              >
                                Next
                              </button>
                            </div>
                          )}
                        </div>
                      </>
                    )
                  })()}
                </div>
              ) : (
                <div className="text-center text-gray-500">No findings yet</div>
              )}
            </>
          )}

          {/* Findings by Section View */}
          {viewMode === 'section' && (
            <>
              {findingsLoading ? (
                <div className="text-center text-gray-500">Loading findings...</div>
              ) : groupedFindings && Array.isArray(groupedFindings) && groupedFindings.length > 0 ? (
                <div className="space-y-6">
                  {(() => {
                    const totalSectionPages = Math.ceil(groupedFindings.length / sectionPageSize)
                    const startIndex = (currentSectionPage - 1) * sectionPageSize
                    const endIndex = startIndex + sectionPageSize
                    const paginatedSections = groupedFindings.slice(startIndex, endIndex)

                    return (
                      <>
                        {/* Section List */}
                        {paginatedSections.map((sectionData: any) => (
                          <SectionFindings key={sectionData.section} sectionData={sectionData} />
                        ))}

                        {/* Bottom Pagination Footer */}
                        <div className="mt-6 pt-4 border-t border-gray-200 flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-gray-500">Show</span>
                              <select
                                value={sectionPageSize}
                                onChange={(e) => handleSectionPageSizeChange(Number(e.target.value))}
                                className="border border-gray-300 rounded-md text-sm py-1 px-2 focus:ring-indigo-500 focus:border-indigo-500"
                              >
                                {SECTION_PAGE_SIZE_OPTIONS.map(size => (
                                  <option key={size} value={size}>{size}</option>
                                ))}
                              </select>
                              <span className="text-sm text-gray-500">per page</span>
                            </div>
                            <div className="text-sm text-gray-600">
                              Showing {startIndex + 1} to {Math.min(endIndex, groupedFindings.length)} of {groupedFindings.length} sections
                            </div>
                          </div>
                          {totalSectionPages > 1 && (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => setCurrentSectionPage(p => Math.max(1, p - 1))}
                                disabled={currentSectionPage === 1}
                                className="px-3 py-1 rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                              >
                                Prev
                              </button>
                              <span className="text-sm text-gray-600">
                                Page {currentSectionPage} of {totalSectionPages}
                              </span>
                              <button
                                onClick={() => setCurrentSectionPage(p => Math.min(totalSectionPages, p + 1))}
                                disabled={currentSectionPage === totalSectionPages}
                                className="px-3 py-1 rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                              >
                                Next
                              </button>
                            </div>
                          )}
                        </div>
                      </>
                    )
                  })()}
                </div>
              ) : (
                <div className="text-center text-gray-500">No findings yet</div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
