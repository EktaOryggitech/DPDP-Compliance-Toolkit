import { useState, useMemo, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  XMarkIcon,
  TrashIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { scansApi } from '../lib/api'

const PAGE_SIZE_OPTIONS = [5, 10, 20, 50, 100]
const DEFAULT_PAGE_SIZE = 5

interface Scan {
  id: string
  application_id: string
  application_name: string
  scan_type: 'quick' | 'standard' | 'deep'
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  status_message?: string
  started_at?: string
  completed_at?: string
  pages_scanned: number
  total_pages?: number
  current_url?: string
  progress_percentage: number
  findings_count: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  overall_score?: number
  duration_seconds?: number
  created_at: string
}

type SortField = 'application_name' | 'scan_type' | 'status' | 'pages_scanned' | 'findings_count' | 'overall_score' | 'created_at'
type SortOrder = 'asc' | 'desc'

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  queued: 'bg-yellow-100 text-yellow-800',
  running: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-800',
}

const statusOptions = ['all', 'pending', 'queued', 'running', 'completed', 'failed', 'cancelled']
const typeOptions = ['all', 'quick', 'standard', 'deep']

function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return '--:--'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins >= 60) {
    const hours = Math.floor(mins / 60)
    const remainingMins = mins % 60
    return `${hours}h ${remainingMins}m`
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function calculateElapsed(startedAt: string | undefined): number {
  if (!startedAt) return 0
  const start = new Date(startedAt).getTime()
  const now = Date.now()
  return Math.floor((now - start) / 1000)
}

function estimateRemaining(scan: Scan): number | null {
  if (!scan.started_at || scan.pages_scanned === 0 || !scan.total_pages) return null
  const elapsed = calculateElapsed(scan.started_at)
  const timePerPage = elapsed / scan.pages_scanned
  const remainingPages = scan.total_pages - scan.pages_scanned
  return Math.floor(timePerPage * remainingPages)
}

function ProgressBar({ percent }: { percent: number }) {
  return (
    <div className="w-full bg-gray-200 rounded-full h-2">
      <div
        className="bg-primary-600 h-2 rounded-full transition-all duration-300"
        style={{ width: `${percent}%` }}
      />
    </div>
  )
}

function SeverityBadges({ scan }: { scan: Scan }) {
  const badges = []
  if (scan.critical_count > 0) {
    badges.push(
      <span key="critical" className="px-1.5 py-0.5 text-xs rounded bg-red-100 text-red-700">
        C:{scan.critical_count}
      </span>
    )
  }
  if (scan.high_count > 0) {
    badges.push(
      <span key="high" className="px-1.5 py-0.5 text-xs rounded bg-orange-100 text-orange-700">
        H:{scan.high_count}
      </span>
    )
  }
  if (scan.medium_count > 0) {
    badges.push(
      <span key="medium" className="px-1.5 py-0.5 text-xs rounded bg-yellow-100 text-yellow-700">
        M:{scan.medium_count}
      </span>
    )
  }
  if (scan.low_count > 0) {
    badges.push(
      <span key="low" className="px-1.5 py-0.5 text-xs rounded bg-blue-100 text-blue-700">
        L:{scan.low_count}
      </span>
    )
  }

  if (badges.length === 0) {
    return <span className="text-gray-400 text-xs">-</span>
  }

  return <div className="flex gap-1 flex-wrap">{badges}</div>
}

function truncateUrl(url: string | undefined, maxLength: number = 40): string {
  if (!url) return '-'
  try {
    const parsed = new URL(url)
    const path = parsed.pathname + parsed.search
    if (path.length > maxLength) {
      return '...' + path.slice(-maxLength)
    }
    return path || '/'
  } catch {
    if (url.length > maxLength) {
      return '...' + url.slice(-maxLength)
    }
    return url
  }
}

// Column header with sort and inline filter
function FilterableHeader({
  label,
  field,
  currentSort,
  currentOrder,
  onSort,
  filterType,
  filterValue,
  onFilterChange,
  filterOptions,
  placeholder,
}: {
  label: string
  field: SortField
  currentSort: SortField
  currentOrder: SortOrder
  onSort: (field: SortField) => void
  filterType: 'text' | 'select' | 'number'
  filterValue: string
  onFilterChange: (value: string) => void
  filterOptions?: string[]
  placeholder?: string
}) {
  const isActive = currentSort === field
  const hasFilter = filterValue && filterValue !== 'all'

  return (
    <th className="px-4 py-2 text-left">
      <div className="space-y-1">
        {/* Sort button */}
        <button
          onClick={() => onSort(field)}
          className="flex items-center gap-1 text-xs font-medium text-gray-500 uppercase hover:text-gray-700"
        >
          {label}
          <span className="flex flex-col">
            <ChevronUpIcon
              className={`h-3 w-3 -mb-1 ${isActive && currentOrder === 'asc' ? 'text-primary-600' : 'text-gray-300'}`}
            />
            <ChevronDownIcon
              className={`h-3 w-3 ${isActive && currentOrder === 'desc' ? 'text-primary-600' : 'text-gray-300'}`}
            />
          </span>
        </button>
        {/* Filter input */}
        {filterType === 'select' && filterOptions ? (
          <select
            value={filterValue}
            onChange={(e) => onFilterChange(e.target.value)}
            className={`w-full text-xs border rounded px-1.5 py-1 focus:ring-primary-500 focus:border-primary-500 ${
              hasFilter ? 'border-primary-500 bg-primary-50' : 'border-gray-300'
            }`}
          >
            {filterOptions.map(opt => (
              <option key={opt} value={opt}>
                {opt === 'all' ? 'All' : opt.charAt(0).toUpperCase() + opt.slice(1)}
              </option>
            ))}
          </select>
        ) : filterType === 'number' ? (
          <input
            type="text"
            value={filterValue}
            onChange={(e) => onFilterChange(e.target.value)}
            placeholder={placeholder || ''}
            className={`w-full text-xs border rounded px-1.5 py-1 focus:ring-primary-500 focus:border-primary-500 ${
              hasFilter ? 'border-primary-500 bg-primary-50' : 'border-gray-300'
            }`}
          />
        ) : (
          <input
            type="text"
            value={filterValue}
            onChange={(e) => onFilterChange(e.target.value)}
            placeholder={placeholder || 'Filter...'}
            className={`w-full text-xs border rounded px-1.5 py-1 focus:ring-primary-500 focus:border-primary-500 ${
              hasFilter ? 'border-primary-500 bg-primary-50' : 'border-gray-300'
            }`}
          />
        )}
      </div>
    </th>
  )
}

// Simple header without filter (for columns that don't need filtering)
function SimpleHeader({ label }: { label: string }) {
  return (
    <th className="px-4 py-2 text-left">
      <div className="space-y-1">
        <span className="text-xs font-medium text-gray-500 uppercase">{label}</span>
        <div className="h-6"></div> {/* Spacer to align with filter inputs */}
      </div>
    </th>
  )
}

export default function Scans() {
  const queryClient = useQueryClient()
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [selectedScans, setSelectedScans] = useState<Set<string>>(new Set())

  // Column filters
  const [filters, setFilters] = useState({
    application_name: '',
    scan_type: 'all',
    date: '',
    status: 'all',
    pages: '',
    findings: '',
    score: '',
  })

  const updateFilter = (key: keyof typeof filters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const { data, isLoading } = useQuery({
    queryKey: ['scans'],
    queryFn: () => scansApi.list({ limit: 1000 }),
    refetchInterval: (query) => {
      const hasRunning = query.state.data?.items?.some(
        (scan: Scan) => scan.status === 'running' || scan.status === 'pending' || scan.status === 'queued'
      )
      return hasRunning ? 2000 : false
    },
  })

  // Filter, search, and sort data
  const processedData = useMemo(() => {
    if (!data?.items) return []

    let filtered = [...data.items]

    // Apply application name filter
    if (filters.application_name.trim()) {
      const query = filters.application_name.toLowerCase()
      filtered = filtered.filter((scan: Scan) =>
        scan.application_name?.toLowerCase().includes(query)
      )
    }

    // Apply status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter((scan: Scan) => scan.status === filters.status)
    }

    // Apply type filter
    if (filters.scan_type !== 'all') {
      filtered = filtered.filter((scan: Scan) => scan.scan_type === filters.scan_type)
    }

    // Apply date filter (searches in formatted date string)
    if (filters.date.trim()) {
      const query = filters.date.toLowerCase()
      filtered = filtered.filter((scan: Scan) => {
        const dateStr = new Date(scan.created_at).toLocaleString().toLowerCase()
        return dateStr.includes(query)
      })
    }

    // Apply pages filter (supports >, <, >=, <=, = or just number for >=)
    if (filters.pages.trim()) {
      const value = filters.pages.trim()
      const match = value.match(/^([<>=!]+)?\s*(\d+)$/)
      if (match) {
        const op = match[1] || '>='  // Default to >= if no operator
        const num = parseInt(match[2])
        filtered = filtered.filter((scan: Scan) => {
          const val = scan.pages_scanned ?? 0
          switch (op) {
            case '>': return val > num
            case '<': return val < num
            case '>=': return val >= num
            case '<=': return val <= num
            case '=': case '==': return val === num
            case '!=': return val !== num
            default: return val >= num
          }
        })
      }
    }

    // Apply findings filter (supports >, <, >=, <=, = or just number for >=)
    if (filters.findings.trim()) {
      const value = filters.findings.trim()
      const match = value.match(/^([<>=!]+)?\s*(\d+)$/)
      if (match) {
        const op = match[1] || '>='  // Default to >= if no operator
        const num = parseInt(match[2])
        filtered = filtered.filter((scan: Scan) => {
          const val = scan.findings_count ?? 0
          switch (op) {
            case '>': return val > num
            case '<': return val < num
            case '>=': return val >= num
            case '<=': return val <= num
            case '=': case '==': return val === num
            case '!=': return val !== num
            default: return val >= num
          }
        })
      }
    }

    // Apply score filter (supports >, <, >=, <=, = or just number for >=)
    if (filters.score.trim()) {
      const value = filters.score.trim()
      const match = value.match(/^([<>=!]+)?\s*(\d+)$/)
      if (match) {
        const op = match[1] || '>='  // Default to >= if no operator
        const num = parseInt(match[2])
        filtered = filtered.filter((scan: Scan) => {
          const val = scan.overall_score ?? -1
          // Skip scans without score if filtering
          if (val < 0) return false
          switch (op) {
            case '>': return val > num
            case '<': return val < num
            case '>=': return val >= num
            case '<=': return val <= num
            case '=': case '==': return val === num
            case '!=': return val !== num
            default: return val >= num
          }
        })
      }
    }

    // Apply sorting
    filtered.sort((a: Scan, b: Scan) => {
      let aVal: any = a[sortField]
      let bVal: any = b[sortField]

      if (aVal === null || aVal === undefined) aVal = sortOrder === 'asc' ? Infinity : -Infinity
      if (bVal === null || bVal === undefined) bVal = sortOrder === 'asc' ? Infinity : -Infinity

      if (typeof aVal === 'string') aVal = aVal.toLowerCase()
      if (typeof bVal === 'string') bVal = bVal.toLowerCase()

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1
      return 0
    })

    return filtered
  }, [data?.items, filters, sortField, sortOrder])

  // Paginate
  const totalPages = Math.ceil(processedData.length / pageSize)
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return processedData.slice(start, start + pageSize)
  }, [processedData, currentPage, pageSize])

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [filters, sortField, sortOrder])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize)
    setCurrentPage(1)
  }

  const clearFilters = () => {
    setFilters({
      application_name: '',
      scan_type: 'all',
      date: '',
      status: 'all',
      pages: '',
      findings: '',
      score: '',
    })
  }

  const hasActiveFilters = filters.application_name || filters.scan_type !== 'all' ||
    filters.date || filters.status !== 'all' || filters.pages || filters.findings || filters.score

  const cancelMutation = useMutation({
    mutationFn: scansApi.cancel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
      toast.success('Scan cancelled')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to cancel scan')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: scansApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
      toast.success('Scan deleted')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete scan')
    },
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: scansApi.bulkDelete,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
      setSelectedScans(new Set())
      toast.success(data.message || 'Selected scans deleted')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete scans')
    },
  })

  const deleteAllMutation = useMutation({
    mutationFn: scansApi.deleteAll,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
      setSelectedScans(new Set())
      toast.success(data.message || 'All scans deleted')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete all scans')
    },
  })

  // Selection handlers
  const toggleSelectAll = () => {
    if (selectedScans.size === paginatedData.length) {
      setSelectedScans(new Set())
    } else {
      setSelectedScans(new Set(paginatedData.map((scan: Scan) => scan.id)))
    }
  }

  const toggleSelectScan = (scanId: string) => {
    const newSelected = new Set(selectedScans)
    if (newSelected.has(scanId)) {
      newSelected.delete(scanId)
    } else {
      newSelected.add(scanId)
    }
    setSelectedScans(newSelected)
  }

  const handleBulkDelete = () => {
    if (selectedScans.size === 0) return
    if (confirm(`Delete ${selectedScans.size} selected scan(s) and their findings?`)) {
      bulkDeleteMutation.mutate(Array.from(selectedScans))
    }
  }

  const handleDeleteAll = () => {
    if (confirm('Delete ALL scans and their findings? This cannot be undone.')) {
      deleteAllMutation.mutate()
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Scans</h1>
          <p className="mt-1 text-sm text-gray-500">
            View all compliance scans and their results
          </p>
        </div>
        <div className="flex items-center gap-3">
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-sm text-primary-600 hover:text-primary-800 flex items-center gap-1"
            >
              <XMarkIcon className="h-4 w-4" />
              Clear filters
            </button>
          )}
          {selectedScans.size > 0 && (
            <button
              onClick={handleBulkDelete}
              disabled={bulkDeleteMutation.isPending}
              className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md disabled:opacity-50"
            >
              <TrashIcon className="h-4 w-4 mr-1" />
              Delete Selected ({selectedScans.size})
            </button>
          )}
          {processedData.length > 0 && (
            <button
              onClick={handleDeleteAll}
              disabled={deleteAllMutation.isPending}
              className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-red-600 border border-red-600 hover:bg-red-50 rounded-md disabled:opacity-50"
            >
              <TrashIcon className="h-4 w-4 mr-1" />
              Delete All
            </button>
          )}
        </div>
      </div>

      {/* Scans List */}
      <div className="bg-white shadow overflow-hidden rounded-lg">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left w-10">
                    <div className="space-y-1">
                      <input
                        type="checkbox"
                        checked={paginatedData.length > 0 && selectedScans.size === paginatedData.length}
                        onChange={toggleSelectAll}
                        className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                      />
                      <div className="h-6"></div>
                    </div>
                  </th>
                  <FilterableHeader
                    label="Application"
                    field="application_name"
                    currentSort={sortField}
                    currentOrder={sortOrder}
                    onSort={handleSort}
                    filterType="text"
                    filterValue={filters.application_name}
                    onFilterChange={(v) => updateFilter('application_name', v)}
                    placeholder="Search..."
                  />
                  <FilterableHeader
                    label="Type"
                    field="scan_type"
                    currentSort={sortField}
                    currentOrder={sortOrder}
                    onSort={handleSort}
                    filterType="select"
                    filterValue={filters.scan_type}
                    onFilterChange={(v) => updateFilter('scan_type', v)}
                    filterOptions={typeOptions}
                  />
                  <FilterableHeader
                    label="Date & Time"
                    field="created_at"
                    currentSort={sortField}
                    currentOrder={sortOrder}
                    onSort={handleSort}
                    filterType="text"
                    filterValue={filters.date}
                    onFilterChange={(v) => updateFilter('date', v)}
                    placeholder="Search..."
                  />
                  <FilterableHeader
                    label="Status"
                    field="status"
                    currentSort={sortField}
                    currentOrder={sortOrder}
                    onSort={handleSort}
                    filterType="select"
                    filterValue={filters.status}
                    onFilterChange={(v) => updateFilter('status', v)}
                    filterOptions={statusOptions}
                  />
                  <SimpleHeader label="Progress" />
                  <FilterableHeader
                    label="Pages"
                    field="pages_scanned"
                    currentSort={sortField}
                    currentOrder={sortOrder}
                    onSort={handleSort}
                    filterType="number"
                    filterValue={filters.pages}
                    onFilterChange={(v) => updateFilter('pages', v)}
                    placeholder="10 or >5"
                  />
                  <SimpleHeader label="Current Page" />
                  <FilterableHeader
                    label="Findings"
                    field="findings_count"
                    currentSort={sortField}
                    currentOrder={sortOrder}
                    onSort={handleSort}
                    filterType="number"
                    filterValue={filters.findings}
                    onFilterChange={(v) => updateFilter('findings', v)}
                    placeholder="0 or >5"
                  />
                  <SimpleHeader label="Time" />
                  <FilterableHeader
                    label="Score"
                    field="overall_score"
                    currentSort={sortField}
                    currentOrder={sortOrder}
                    onSort={handleSort}
                    filterType="number"
                    filterValue={filters.score}
                    onFilterChange={(v) => updateFilter('score', v)}
                    placeholder="80 or <60"
                  />
                  <th className="px-4 py-2 text-right">
                    <div className="space-y-1">
                      <span className="text-xs font-medium text-gray-500 uppercase">Actions</span>
                      <div className="h-6"></div>
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {paginatedData.length > 0 ? (
                  paginatedData.map((scan: Scan) => {
                    const isRunning = ['pending', 'queued', 'running'].includes(scan.status)
                    const elapsed = isRunning ? calculateElapsed(scan.started_at) : scan.duration_seconds
                    const remaining = isRunning ? estimateRemaining(scan) : null
                    const progress = scan.status === 'completed' ? 100 :
                      scan.status === 'running' && scan.total_pages
                        ? Math.min(Math.floor((scan.pages_scanned / scan.total_pages) * 100), 99)
                        : scan.progress_percentage || 0

                    return (
                      <tr key={scan.id} className={isRunning ? 'bg-blue-50/30' : ''}>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <input
                            type="checkbox"
                            checked={selectedScans.has(scan.id)}
                            onChange={() => toggleSelectScan(scan.id)}
                            className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                          />
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                          {scan.application_name}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500 capitalize">
                          {scan.scan_type}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                          {new Date(scan.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-col gap-1">
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                statusColors[scan.status] || 'bg-gray-100 text-gray-800'
                              }`}
                              title={scan.status_message || undefined}
                            >
                              {isRunning && (
                                <svg className="animate-spin -ml-0.5 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                              )}
                              {scan.status}
                            </span>
                            {scan.status === 'failed' && scan.status_message && (
                              <span className="text-xs text-red-600 max-w-[200px] truncate" title={scan.status_message}>
                                {scan.status_message}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="w-24">
                            <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                              <span>{progress}%</span>
                            </div>
                            <ProgressBar percent={progress} />
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                          {scan.pages_scanned}
                          {scan.total_pages ? ` / ${scan.total_pages}` : ''}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500 max-w-xs">
                          {isRunning ? (
                            <span className="text-blue-600 truncate block" title={scan.current_url}>
                              {truncateUrl(scan.current_url)}
                            </span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex flex-col gap-1">
                            <span className="text-sm font-medium text-gray-900">
                              {scan.findings_count}
                            </span>
                            <SeverityBadges scan={scan} />
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                          <div className="flex flex-col">
                            <span className="text-gray-900">{formatDuration(elapsed)}</span>
                            {remaining !== null && (
                              <span className="text-xs text-gray-500">
                                ~{formatDuration(remaining)} left
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {scan.overall_score !== undefined && scan.overall_score !== null ? (
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
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex items-center justify-end gap-2">
                            <Link
                              to={`/scans/${scan.id}`}
                              className="text-primary-600 hover:text-primary-900"
                            >
                              View
                            </Link>
                            {isRunning && (
                              <button
                                onClick={() => cancelMutation.mutate(scan.id)}
                                disabled={cancelMutation.isPending}
                                className="text-yellow-600 hover:text-yellow-900"
                                title="Cancel Scan"
                              >
                                <XMarkIcon className="h-5 w-5" />
                              </button>
                            )}
                            {['failed', 'cancelled', 'completed'].includes(scan.status) && (
                              <button
                                onClick={() => {
                                  if (confirm('Delete this scan and its findings?')) {
                                    deleteMutation.mutate(scan.id)
                                  }
                                }}
                                disabled={deleteMutation.isPending}
                                className="text-red-600 hover:text-red-900"
                                title="Delete Scan"
                              >
                                <TrashIcon className="h-5 w-5" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })
                ) : (
                  <tr>
                    <td colSpan={12} className="px-4 py-8 text-center text-gray-500">
                      {hasActiveFilters ? 'No scans match your filters.' : 'No scans yet. Start a scan from the Applications page.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {processedData.length > 0 && (
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
                Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, processedData.length)} of {processedData.length} scans
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
        )}
      </div>
    </div>
  )
}
