import { useState, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PlusIcon, TrashIcon, PlayIcon, KeyIcon, BoltIcon, AdjustmentsHorizontalIcon, MagnifyingGlassCircleIcon, PencilSquareIcon, ChevronLeftIcon, ChevronRightIcon, ChevronUpIcon, ChevronDownIcon, XMarkIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { applicationsApi, scansApi } from '../lib/api'
import { useAuthStore } from '../stores/authStore'

const PAGE_SIZE_OPTIONS = [5, 10, 20, 50, 100]
const DEFAULT_PAGE_SIZE = 5

type ScanType = 'quick' | 'standard' | 'deep'
type SortField = 'name' | 'type' | 'url' | 'last_scan_at' | 'is_active'
type SortOrder = 'asc' | 'desc'

const typeOptions = ['all', 'web', 'windows']
const statusOptions = ['all', 'active', 'inactive']

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
  filterType: 'text' | 'select'
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

// Simple header without filter
function SimpleHeader({ label }: { label: string }) {
  return (
    <th className="px-4 py-2 text-left">
      <div className="space-y-1">
        <span className="text-xs font-medium text-gray-500 uppercase">{label}</span>
        <div className="h-6"></div>
      </div>
    </th>
  )
}

const scanTypeConfig = {
  quick: {
    icon: BoltIcon,
    title: 'Quick Scan',
    description: 'All checks on ~20 pages',
    maxPages: 20,
    features: ['All DPDP Sections', 'Screenshot Evidence', 'Dark Patterns'],
    time: '2-5 minutes',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
  },
  standard: {
    icon: AdjustmentsHorizontalIcon,
    title: 'Standard Scan',
    description: 'All checks on ~75 pages',
    maxPages: 75,
    features: ['All DPDP Sections', 'Screenshot Evidence', 'Dark Patterns'],
    time: '5-15 minutes',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  deep: {
    icon: MagnifyingGlassCircleIcon,
    title: 'Deep Scan',
    description: 'All checks on ~200 pages',
    maxPages: 200,
    features: ['All DPDP Sections', 'Screenshot Evidence', 'Dark Patterns'],
    time: '15-60 minutes',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
  },
}

interface AuthConfig {
  auth_type: 'none' | 'credentials' | 'basic'
  login_url?: string
  username_field?: string
  password_field?: string
  credentials?: {
    username: string
    password: string
  }
  submit_selector?: string
}

interface Application {
  id: string
  name: string
  url?: string
  type: 'web' | 'windows'
  description?: string
  is_active: boolean
  last_scan_at?: string
  created_at: string
  auth_config?: AuthConfig
}

export default function Applications() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editingApp, setEditingApp] = useState<Application | null>(null)
  const [showAuthConfig, setShowAuthConfig] = useState(false)
  const [isScanModalOpen, setIsScanModalOpen] = useState(false)
  const [selectedAppForScan, setSelectedAppForScan] = useState<Application | null>(null)
  const [selectedScanType, setSelectedScanType] = useState<ScanType>('standard')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [sortField, setSortField] = useState<SortField>('name')
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')

  // Column filters
  const [filters, setFilters] = useState({
    name: '',
    type: 'all',
    url: '',
    status: 'all',
  })

  const updateFilter = (key: keyof typeof filters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const clearFilters = () => {
    setFilters({ name: '', type: 'all', url: '', status: 'all' })
  }

  const hasActiveFilters = filters.name || filters.type !== 'all' || filters.url || filters.status !== 'all'
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    type: 'web' as 'web' | 'windows',
    description: '',
    auth_config: {
      auth_type: 'none' as 'none' | 'credentials' | 'basic',
      login_url: '',
      username_field: '#username, input[name="username"], input[name="email"], input[type="email"]',
      password_field: '#password, input[name="password"], input[type="password"]',
      submit_selector: 'button[type="submit"], input[type="submit"]',
      credentials: {
        username: '',
        password: '',
      },
    },
  })

  const { data, isLoading } = useQuery({
    queryKey: ['applications'],
    queryFn: () => applicationsApi.list(),
  })

  // Handle sort change
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }

  // Filter, sort, and paginate applications
  const filteredApps = useMemo(() => {
    if (!data?.items) return []

    let apps = [...data.items]

    // Apply name filter
    if (filters.name.trim()) {
      const query = filters.name.toLowerCase()
      apps = apps.filter((app: Application) =>
        app.name.toLowerCase().includes(query) ||
        app.description?.toLowerCase().includes(query)
      )
    }

    // Apply URL filter
    if (filters.url.trim()) {
      const query = filters.url.toLowerCase()
      apps = apps.filter((app: Application) =>
        app.url?.toLowerCase().includes(query)
      )
    }

    // Apply type filter
    if (filters.type !== 'all') {
      apps = apps.filter((app: Application) => app.type === filters.type)
    }

    // Apply status filter
    if (filters.status !== 'all') {
      apps = apps.filter((app: Application) =>
        filters.status === 'active' ? app.is_active : !app.is_active
      )
    }

    // Apply sorting
    apps.sort((a: Application, b: Application) => {
      let comparison = 0
      switch (sortField) {
        case 'name':
          comparison = a.name.localeCompare(b.name)
          break
        case 'type':
          comparison = a.type.localeCompare(b.type)
          break
        case 'url':
          comparison = (a.url || '').localeCompare(b.url || '')
          break
        case 'last_scan_at':
          const dateA = a.last_scan_at ? new Date(a.last_scan_at).getTime() : 0
          const dateB = b.last_scan_at ? new Date(b.last_scan_at).getTime() : 0
          comparison = dateA - dateB
          break
        case 'is_active':
          comparison = (a.is_active ? 1 : 0) - (b.is_active ? 1 : 0)
          break
        default:
          comparison = 0
      }
      return sortOrder === 'asc' ? comparison : -comparison
    })

    return apps
  }, [data?.items, filters, sortField, sortOrder])

  const totalPages = Math.ceil(filteredApps.length / pageSize)
  const paginatedApps = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return filteredApps.slice(start, start + pageSize)
  }, [filteredApps, currentPage, pageSize])

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize)
    setCurrentPage(1) // Reset to first page when changing page size
  }

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [filters, sortField, sortOrder])

  // Query for running scans to disable edit/delete buttons
  const { data: runningScansData } = useQuery({
    queryKey: ['scans', 'running'],
    queryFn: () => scansApi.list({ status: 'running' }),
    refetchInterval: 5000, // Refresh every 5 seconds to check scan status
  })

  // Get set of application IDs with running scans
  const appsWithRunningScans = new Set(
    runningScansData?.items?.map((scan: any) => scan.application_id) || []
  )

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => {
      // Only include auth_config if authentication is enabled
      const authConfig = data.auth_config.auth_type !== 'none' ? {
        auth_type: data.auth_config.auth_type,
        login_url: data.auth_config.login_url,
        username_field: data.auth_config.username_field,
        password_field: data.auth_config.password_field,
        credentials: {
          username: data.auth_config.credentials.username,
          password: data.auth_config.credentials.password,
        },
      } : null
      return applicationsApi.create({
        name: data.name,
        url: data.url,
        type: data.type,
        description: data.description,
        organization_id: user?.organization_id || '',
        auth_config: authConfig,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      setIsModalOpen(false)
      resetFormData()
      toast.success('Application created successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create application')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: typeof formData }) => {
      // Only include auth_config if authentication is enabled
      const authConfig = data.auth_config.auth_type !== 'none' ? {
        auth_type: data.auth_config.auth_type,
        login_url: data.auth_config.login_url,
        username_field: data.auth_config.username_field,
        password_field: data.auth_config.password_field,
        credentials: {
          username: data.auth_config.credentials.username,
          password: data.auth_config.credentials.password,
        },
      } : null
      return applicationsApi.update(id, {
        name: data.name,
        url: data.url,
        description: data.description,
        auth_config: authConfig,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      setIsEditModalOpen(false)
      setEditingApp(null)
      resetFormData()
      toast.success('Application updated successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update application')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: applicationsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      toast.success('Application deleted')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete application')
    },
  })

  const scanMutation = useMutation({
    mutationFn: ({ appId, scanType }: { appId: string; scanType: ScanType }) =>
      scansApi.create({
        application_id: appId,
        scan_type: scanType,
        config_overrides: {
          max_pages: scanTypeConfig[scanType].maxPages,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
      setIsScanModalOpen(false)
      setSelectedAppForScan(null)
      toast.success(`${scanTypeConfig[selectedScanType].title} started successfully`)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to start scan')
    },
  })

  const resetFormData = () => {
    setFormData({
      name: '',
      url: '',
      type: 'web',
      description: '',
      auth_config: {
        auth_type: 'none',
        login_url: '',
        username_field: '#username, input[name="username"], input[name="email"], input[type="email"]',
        password_field: '#password, input[name="password"], input[type="password"]',
        submit_selector: 'button[type="submit"], input[type="submit"]',
        credentials: {
          username: '',
          password: '',
        },
      },
    })
    setShowAuthConfig(false)
  }

  const handleStartScan = (app: Application) => {
    setSelectedAppForScan(app)
    setSelectedScanType('standard')
    setIsScanModalOpen(true)
  }

  const handleEditApp = (app: Application) => {
    setEditingApp(app)
    // Pre-populate form with existing data
    const authConfig = app.auth_config || {
      auth_type: 'none',
      login_url: '',
      username_field: '#username, input[name="username"], input[name="email"], input[type="email"]',
      password_field: '#password, input[name="password"], input[type="password"]',
      submit_selector: 'button[type="submit"], input[type="submit"]',
      credentials: { username: '', password: '' },
    }
    setFormData({
      name: app.name,
      url: app.url || '',
      type: app.type,
      description: app.description || '',
      auth_config: {
        auth_type: authConfig.auth_type || 'none',
        login_url: authConfig.login_url || '',
        username_field: authConfig.username_field || '#username, input[name="username"], input[name="email"], input[type="email"]',
        password_field: authConfig.password_field || '#password, input[name="password"], input[type="password"]',
        submit_selector: authConfig.submit_selector || 'button[type="submit"], input[type="submit"]',
        credentials: {
          username: authConfig.credentials?.username || '',
          password: authConfig.credentials?.password || '',
        },
      },
    })
    setShowAuthConfig(authConfig.auth_type !== 'none')
    setIsEditModalOpen(true)
  }

  const handleUpdateSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingApp) {
      updateMutation.mutate({ id: editingApp.id, data: formData })
    }
  }

  const confirmStartScan = () => {
    if (selectedAppForScan) {
      scanMutation.mutate({ appId: selectedAppForScan.id, scanType: selectedScanType })
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Applications</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage web and Windows applications for compliance scanning
          </p>
        </div>
        <div className="flex items-center gap-4">
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-sm text-primary-600 hover:text-primary-800 flex items-center gap-1"
            >
              <XMarkIcon className="h-4 w-4" />
              Clear filters
            </button>
          )}
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700"
          >
            <PlusIcon className="-ml-1 mr-2 h-5 w-5" />
            Add Application
          </button>
        </div>
      </div>

      {/* Applications List */}
      <div className="bg-white shadow overflow-hidden rounded-lg">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : paginatedApps.length > 0 ? (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <FilterableHeader
                  label="Name"
                  field="name"
                  currentSort={sortField}
                  currentOrder={sortOrder}
                  onSort={handleSort}
                  filterType="text"
                  filterValue={filters.name}
                  onFilterChange={(v) => updateFilter('name', v)}
                  placeholder="Search..."
                />
                <FilterableHeader
                  label="Type"
                  field="type"
                  currentSort={sortField}
                  currentOrder={sortOrder}
                  onSort={handleSort}
                  filterType="select"
                  filterValue={filters.type}
                  onFilterChange={(v) => updateFilter('type', v)}
                  filterOptions={typeOptions}
                />
                <FilterableHeader
                  label="URL / Path"
                  field="url"
                  currentSort={sortField}
                  currentOrder={sortOrder}
                  onSort={handleSort}
                  filterType="text"
                  filterValue={filters.url}
                  onFilterChange={(v) => updateFilter('url', v)}
                  placeholder="Search..."
                />
                <SimpleHeader label="Last Scan" />
                <FilterableHeader
                  label="Status"
                  field="is_active"
                  currentSort={sortField}
                  currentOrder={sortOrder}
                  onSort={handleSort}
                  filterType="select"
                  filterValue={filters.status}
                  onFilterChange={(v) => updateFilter('status', v)}
                  filterOptions={statusOptions}
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
              {paginatedApps.map((app: Application) => (
                <tr key={app.id}>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{app.name}</div>
                    {app.description && (
                      <div className="text-sm text-gray-500">{app.description}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        app.type === 'web'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-purple-100 text-purple-800'
                      }`}
                    >
                      {app.type === 'web' ? 'Web' : 'Windows'}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                    {app.url || '-'}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                    {app.last_scan_at
                      ? new Date(app.last_scan_at).toLocaleDateString()
                      : 'Never'}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {appsWithRunningScans.has(app.id) ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 animate-pulse">
                        <svg className="animate-spin -ml-0.5 mr-1.5 h-3 w-3 text-blue-600" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Scanning...
                      </span>
                    ) : (
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          app.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {app.is_active ? 'Active' : 'Inactive'}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                    {/* Edit Button - Disabled when scan is running */}
                    <button
                      onClick={() => handleEditApp(app)}
                      disabled={appsWithRunningScans.has(app.id)}
                      className={`mr-3 ${
                        appsWithRunningScans.has(app.id)
                          ? 'text-gray-300 cursor-not-allowed'
                          : 'text-blue-600 hover:text-blue-900'
                      }`}
                      title={appsWithRunningScans.has(app.id) ? 'Cannot edit while scan is running' : 'Edit Application'}
                    >
                      <PencilSquareIcon className="h-5 w-5" />
                    </button>
                    {/* Start Scan Button */}
                    <button
                      onClick={() => handleStartScan(app)}
                      disabled={scanMutation.isPending || appsWithRunningScans.has(app.id)}
                      className={`mr-3 ${
                        appsWithRunningScans.has(app.id)
                          ? 'text-gray-300 cursor-not-allowed'
                          : 'text-primary-600 hover:text-primary-900'
                      }`}
                      title={appsWithRunningScans.has(app.id) ? 'Scan already running' : 'Start Scan'}
                    >
                      <PlayIcon className="h-5 w-5" />
                    </button>
                    {/* Delete Button - Disabled when scan is running */}
                    <button
                      onClick={() => {
                        if (confirm('Are you sure you want to delete this application?')) {
                          deleteMutation.mutate(app.id)
                        }
                      }}
                      disabled={appsWithRunningScans.has(app.id)}
                      className={`${
                        appsWithRunningScans.has(app.id)
                          ? 'text-gray-300 cursor-not-allowed'
                          : 'text-red-600 hover:text-red-900'
                      }`}
                      title={appsWithRunningScans.has(app.id) ? 'Cannot delete while scan is running' : 'Delete'}
                    >
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-8 text-center text-gray-500">
            {hasActiveFilters
              ? 'No applications matching your filters.'
              : 'No applications yet. Click "Add Application" to get started.'}
          </div>
        )}

        {/* Pagination */}
        {filteredApps.length > 0 && (
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
                Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, filteredApps.length)} of {filteredApps.length} applications
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

      {/* Add Application Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div
              className="fixed inset-0 bg-gray-500 bg-opacity-75"
              onClick={() => setIsModalOpen(false)}
            />
            <div className="relative bg-white rounded-lg max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Add New Application
              </h3>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Name
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Type
                  </label>
                  <select
                    value={formData.type}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        type: e.target.value as 'web' | 'windows',
                      })
                    }
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                  >
                    <option value="web">Web Application</option>
                    <option value="windows">Windows Application</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    {formData.type === 'web' ? 'URL' : 'Executable Path'}
                  </label>
                  <input
                    type={formData.type === 'web' ? 'url' : 'text'}
                    value={formData.url}
                    onChange={(e) =>
                      setFormData({ ...formData, url: e.target.value })
                    }
                    placeholder={
                      formData.type === 'web'
                        ? 'https://example.com'
                        : 'C:\\Program Files\\App\\app.exe'
                    }
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) =>
                      setFormData({ ...formData, description: e.target.value })
                    }
                    rows={2}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                  />
                </div>

                {/* Authentication Configuration */}
                {formData.type === 'web' && (
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-3">
                      <label className="flex items-center text-sm font-medium text-gray-700">
                        <KeyIcon className="h-4 w-4 mr-2" />
                        Login Required
                      </label>
                      <button
                        type="button"
                        onClick={() => {
                          setShowAuthConfig(!showAuthConfig)
                          if (!showAuthConfig) {
                            setFormData({
                              ...formData,
                              auth_config: { ...formData.auth_config, auth_type: 'credentials' },
                            })
                          } else {
                            setFormData({
                              ...formData,
                              auth_config: { ...formData.auth_config, auth_type: 'none' },
                            })
                          }
                        }}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          showAuthConfig ? 'bg-primary-600' : 'bg-gray-200'
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            showAuthConfig ? 'translate-x-6' : 'translate-x-1'
                          }`}
                        />
                      </button>
                    </div>

                    {showAuthConfig && (
                      <div className="space-y-3 bg-gray-50 p-3 rounded-md">
                        {/* DPDP Compliance Notice */}
                        <div className="bg-blue-50 border border-blue-200 rounded-md p-3 text-xs text-blue-800">
                          <p className="font-medium mb-1">Data Protection Notice (DPDP Compliant)</p>
                          <ul className="list-disc list-inside space-y-0.5 text-blue-700">
                            <li>Credentials are stored securely and encrypted at rest</li>
                            <li>Used solely for automated compliance scanning</li>
                            <li>You can delete this application to remove stored credentials</li>
                            <li>No credentials are shared with third parties</li>
                          </ul>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700">
                            Authentication Type
                          </label>
                          <select
                            value={formData.auth_config.auth_type}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                auth_config: {
                                  ...formData.auth_config,
                                  auth_type: e.target.value as 'credentials' | 'basic',
                                },
                              })
                            }
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                          >
                            <option value="credentials">Form Login</option>
                            <option value="basic">HTTP Basic Auth</option>
                          </select>
                        </div>

                        {formData.auth_config.auth_type === 'credentials' && (
                          <>
                            <div>
                              <label className="block text-sm font-medium text-gray-700">
                                Login Page URL
                              </label>
                              <input
                                type="url"
                                value={formData.auth_config.login_url}
                                onChange={(e) =>
                                  setFormData({
                                    ...formData,
                                    auth_config: {
                                      ...formData.auth_config,
                                      login_url: e.target.value,
                                    },
                                  })
                                }
                                placeholder="http://localhost:4200/login"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                              />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                              <div>
                                <label className="block text-sm font-medium text-gray-700">
                                  Username
                                </label>
                                <input
                                  type="text"
                                  value={formData.auth_config.credentials.username}
                                  onChange={(e) =>
                                    setFormData({
                                      ...formData,
                                      auth_config: {
                                        ...formData.auth_config,
                                        credentials: {
                                          ...formData.auth_config.credentials,
                                          username: e.target.value,
                                        },
                                      },
                                    })
                                  }
                                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                />
                              </div>
                              <div>
                                <label className="block text-sm font-medium text-gray-700">
                                  Password
                                </label>
                                <input
                                  type="password"
                                  value={formData.auth_config.credentials.password}
                                  onChange={(e) =>
                                    setFormData({
                                      ...formData,
                                      auth_config: {
                                        ...formData.auth_config,
                                        credentials: {
                                          ...formData.auth_config.credentials,
                                          password: e.target.value,
                                        },
                                      },
                                    })
                                  }
                                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                />
                              </div>
                            </div>
                            <details className="text-sm">
                              <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
                                Advanced: CSS Selectors (auto-detected by default)
                              </summary>
                              <div className="mt-2 space-y-2">
                                <div>
                                  <label className="block text-xs text-gray-500">
                                    Username Field Selector
                                  </label>
                                  <input
                                    type="text"
                                    value={formData.auth_config.username_field}
                                    onChange={(e) =>
                                      setFormData({
                                        ...formData,
                                        auth_config: {
                                          ...formData.auth_config,
                                          username_field: e.target.value,
                                        },
                                      })
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-xs"
                                  />
                                </div>
                                <div>
                                  <label className="block text-xs text-gray-500">
                                    Password Field Selector
                                  </label>
                                  <input
                                    type="text"
                                    value={formData.auth_config.password_field}
                                    onChange={(e) =>
                                      setFormData({
                                        ...formData,
                                        auth_config: {
                                          ...formData.auth_config,
                                          password_field: e.target.value,
                                        },
                                      })
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-xs"
                                  />
                                </div>
                                <div>
                                  <label className="block text-xs text-gray-500">
                                    Submit Button Selector
                                  </label>
                                  <input
                                    type="text"
                                    value={formData.auth_config.submit_selector}
                                    onChange={(e) =>
                                      setFormData({
                                        ...formData,
                                        auth_config: {
                                          ...formData.auth_config,
                                          submit_selector: e.target.value,
                                        },
                                      })
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-xs"
                                  />
                                </div>
                              </div>
                            </details>
                          </>
                        )}

                        {formData.auth_config.auth_type === 'basic' && (
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-sm font-medium text-gray-700">
                                Username
                              </label>
                              <input
                                type="text"
                                value={formData.auth_config.credentials.username}
                                onChange={(e) =>
                                  setFormData({
                                    ...formData,
                                    auth_config: {
                                      ...formData.auth_config,
                                      credentials: {
                                        ...formData.auth_config.credentials,
                                        username: e.target.value,
                                      },
                                    },
                                  })
                                }
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-700">
                                Password
                              </label>
                              <input
                                type="password"
                                value={formData.auth_config.credentials.password}
                                onChange={(e) =>
                                  setFormData({
                                    ...formData,
                                    auth_config: {
                                      ...formData.auth_config,
                                      credentials: {
                                        ...formData.auth_config.credentials,
                                        password: e.target.value,
                                      },
                                    },
                                  })
                                }
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                              />
                            </div>
                          </div>
                        )}

                        {/* Consent checkbox */}
                        <div className="flex items-start mt-3">
                          <input
                            type="checkbox"
                            id="auth-consent"
                            required={showAuthConfig}
                            className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500 mt-0.5"
                          />
                          <label htmlFor="auth-consent" className="ml-2 text-xs text-gray-600">
                            I consent to storing these credentials for automated scanning purposes as described above.
                          </label>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div className="flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={createMutation.isPending}
                    className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50"
                  >
                    {createMutation.isPending ? 'Creating...' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Edit Application Modal */}
      {isEditModalOpen && editingApp && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div
              className="fixed inset-0 bg-gray-500 bg-opacity-75"
              onClick={() => {
                setIsEditModalOpen(false)
                setEditingApp(null)
                resetFormData()
              }}
            />
            <div className="relative bg-white rounded-lg max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Edit Application
              </h3>
              <form onSubmit={handleUpdateSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Name
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Type
                  </label>
                  <select
                    value={formData.type}
                    disabled
                    className="mt-1 block w-full rounded-md border-gray-300 bg-gray-100 shadow-sm sm:text-sm cursor-not-allowed"
                  >
                    <option value="web">Web Application</option>
                    <option value="windows">Windows Application</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-500">Type cannot be changed after creation</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    {formData.type === 'web' ? 'URL' : 'Executable Path'}
                  </label>
                  <input
                    type={formData.type === 'web' ? 'url' : 'text'}
                    value={formData.url}
                    onChange={(e) =>
                      setFormData({ ...formData, url: e.target.value })
                    }
                    placeholder={
                      formData.type === 'web'
                        ? 'https://example.com'
                        : 'C:\\Program Files\\App\\app.exe'
                    }
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) =>
                      setFormData({ ...formData, description: e.target.value })
                    }
                    rows={2}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                  />
                </div>

                {/* Authentication Configuration for Edit */}
                {formData.type === 'web' && (
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-3">
                      <label className="flex items-center text-sm font-medium text-gray-700">
                        <KeyIcon className="h-4 w-4 mr-2" />
                        Login Required
                      </label>
                      <button
                        type="button"
                        onClick={() => {
                          setShowAuthConfig(!showAuthConfig)
                          if (!showAuthConfig) {
                            setFormData({
                              ...formData,
                              auth_config: { ...formData.auth_config, auth_type: 'credentials' },
                            })
                          } else {
                            setFormData({
                              ...formData,
                              auth_config: { ...formData.auth_config, auth_type: 'none' },
                            })
                          }
                        }}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          showAuthConfig ? 'bg-primary-600' : 'bg-gray-200'
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            showAuthConfig ? 'translate-x-6' : 'translate-x-1'
                          }`}
                        />
                      </button>
                    </div>

                    {showAuthConfig && (
                      <div className="space-y-3 bg-gray-50 p-3 rounded-md">
                        <div>
                          <label className="block text-sm font-medium text-gray-700">
                            Authentication Type
                          </label>
                          <select
                            value={formData.auth_config.auth_type}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                auth_config: {
                                  ...formData.auth_config,
                                  auth_type: e.target.value as 'credentials' | 'basic',
                                },
                              })
                            }
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                          >
                            <option value="credentials">Form Login</option>
                            <option value="basic">HTTP Basic Auth</option>
                          </select>
                        </div>

                        {formData.auth_config.auth_type === 'credentials' && (
                          <>
                            <div>
                              <label className="block text-sm font-medium text-gray-700">
                                Login Page URL
                              </label>
                              <input
                                type="url"
                                value={formData.auth_config.login_url}
                                onChange={(e) =>
                                  setFormData({
                                    ...formData,
                                    auth_config: {
                                      ...formData.auth_config,
                                      login_url: e.target.value,
                                    },
                                  })
                                }
                                placeholder="https://example.com/login"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                              />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                              <div>
                                <label className="block text-sm font-medium text-gray-700">
                                  Username
                                </label>
                                <input
                                  type="text"
                                  value={formData.auth_config.credentials.username}
                                  onChange={(e) =>
                                    setFormData({
                                      ...formData,
                                      auth_config: {
                                        ...formData.auth_config,
                                        credentials: {
                                          ...formData.auth_config.credentials,
                                          username: e.target.value,
                                        },
                                      },
                                    })
                                  }
                                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                />
                              </div>
                              <div>
                                <label className="block text-sm font-medium text-gray-700">
                                  Password
                                </label>
                                <input
                                  type="password"
                                  value={formData.auth_config.credentials.password}
                                  onChange={(e) =>
                                    setFormData({
                                      ...formData,
                                      auth_config: {
                                        ...formData.auth_config,
                                        credentials: {
                                          ...formData.auth_config.credentials,
                                          password: e.target.value,
                                        },
                                      },
                                    })
                                  }
                                  placeholder="Leave blank to keep existing"
                                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                />
                              </div>
                            </div>
                          </>
                        )}

                        {formData.auth_config.auth_type === 'basic' && (
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-sm font-medium text-gray-700">
                                Username
                              </label>
                              <input
                                type="text"
                                value={formData.auth_config.credentials.username}
                                onChange={(e) =>
                                  setFormData({
                                    ...formData,
                                    auth_config: {
                                      ...formData.auth_config,
                                      credentials: {
                                        ...formData.auth_config.credentials,
                                        username: e.target.value,
                                      },
                                    },
                                  })
                                }
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-700">
                                Password
                              </label>
                              <input
                                type="password"
                                value={formData.auth_config.credentials.password}
                                onChange={(e) =>
                                  setFormData({
                                    ...formData,
                                    auth_config: {
                                      ...formData.auth_config,
                                      credentials: {
                                        ...formData.auth_config.credentials,
                                        password: e.target.value,
                                      },
                                    },
                                  })
                                }
                                placeholder="Leave blank to keep existing"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <div className="flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setIsEditModalOpen(false)
                      setEditingApp(null)
                      resetFormData()
                    }}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={updateMutation.isPending}
                    className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50"
                  >
                    {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Scan Type Selection Modal */}
      {isScanModalOpen && selectedAppForScan && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div
              className="fixed inset-0 bg-gray-500 bg-opacity-75"
              onClick={() => setIsScanModalOpen(false)}
            />
            <div className="relative bg-white rounded-lg max-w-2xl w-full p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Start Compliance Scan
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Scanning: <span className="font-medium text-gray-900">{selectedAppForScan.name}</span>
                {selectedAppForScan.url && (
                  <span className="text-gray-400 ml-2">({selectedAppForScan.url})</span>
                )}
              </p>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Select Scan Type
                </label>
                <div className="grid grid-cols-3 gap-4">
                  {(Object.keys(scanTypeConfig) as ScanType[]).map((type) => {
                    const config = scanTypeConfig[type]
                    const Icon = config.icon
                    const isSelected = selectedScanType === type

                    return (
                      <button
                        key={type}
                        type="button"
                        onClick={() => setSelectedScanType(type)}
                        className={`relative p-4 rounded-lg border-2 text-left transition-all ${
                          isSelected
                            ? `${config.borderColor} ${config.bgColor} ring-2 ring-offset-2 ring-${type === 'quick' ? 'yellow' : type === 'standard' ? 'blue' : 'purple'}-500`
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center mb-2">
                          <Icon className={`h-6 w-6 ${config.color}`} />
                          <span className={`ml-2 font-medium ${isSelected ? config.color : 'text-gray-900'}`}>
                            {config.title}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mb-2">{config.description}</p>
                        <p className="text-xs text-gray-400">Est. time: {config.time}</p>
                        {isSelected && (
                          <div className="absolute top-2 right-2">
                            <svg className={`h-5 w-5 ${config.color}`} fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                          </div>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* DPDP Compliance Checks */}
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <h4 className="text-sm font-medium text-gray-900 mb-2">
                  DPDP Compliance Checks Included:
                </h4>
                <p className="text-xs text-gray-500 mb-2">All scan types run the same checks - only page count differs.</p>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { section: 'Section 5', name: 'Privacy Notice', included: true },
                    { section: 'Section 6', name: 'Consent Mechanism', included: true },
                    { section: 'Section 6(6)', name: 'Consent Withdrawal', included: true },
                    { section: 'Section 8', name: 'Data Retention', included: true },
                    { section: 'Section 9', name: 'Children Data Protection', included: true },
                    { section: 'Section 10', name: 'SDF Obligations', included: true },
                    { section: 'Section 11-12', name: 'Data Principal Rights', included: true },
                    { section: 'Section 13', name: 'Grievance Mechanism', included: true },
                    { section: 'Section 18', name: 'Dark Patterns', included: true },
                  ].map((check) => (
                    <div
                      key={check.section}
                      className={`flex items-center text-xs ${check.included ? 'text-gray-700' : 'text-gray-400'}`}
                    >
                      {check.included ? (
                        <svg className="h-4 w-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg className="h-4 w-4 text-gray-300 mr-2" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      )}
                      <span className="font-medium">{check.section}:</span>
                      <span className="ml-1">{check.name}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Technologies Used */}
              <div className="text-xs text-gray-500 mb-4">
                <span className="font-medium">Technologies:</span> Playwright, BeautifulSoup, Pattern Matching
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setIsScanModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirmStartScan}
                  disabled={scanMutation.isPending}
                  className={`px-4 py-2 text-sm font-medium text-white border border-transparent rounded-md disabled:opacity-50 ${
                    selectedScanType === 'quick'
                      ? 'bg-yellow-600 hover:bg-yellow-700'
                      : selectedScanType === 'standard'
                      ? 'bg-blue-600 hover:bg-blue-700'
                      : 'bg-purple-600 hover:bg-purple-700'
                  }`}
                >
                  {scanMutation.isPending ? 'Starting...' : `Start ${scanTypeConfig[selectedScanType].title}`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
