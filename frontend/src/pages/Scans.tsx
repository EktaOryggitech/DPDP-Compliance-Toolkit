import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { XMarkIcon, TrashIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { scansApi } from '../lib/api'

interface Scan {
  id: string
  application_id: string
  application_name: string
  scan_type: 'manual' | 'scheduled'
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  started_at?: string
  completed_at?: string
  pages_scanned: number
  findings_count: number
  overall_score?: number
  created_at: string
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  running: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-800',
}

export default function Scans() {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['scans'],
    queryFn: () => scansApi.list({ limit: 50 }),
    // Auto-refresh every 3 seconds if there are running scans
    refetchInterval: (query) => {
      const hasRunning = query.state.data?.items?.some(
        (scan: Scan) => scan.status === 'running' || scan.status === 'pending'
      )
      return hasRunning ? 3000 : false
    },
  })

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Scans</h1>
        <p className="mt-1 text-sm text-gray-500">
          View all compliance scans and their results
        </p>
      </div>

      {/* Scans List */}
      <div className="bg-white shadow overflow-hidden rounded-lg">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : data?.items?.length > 0 ? (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Application
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Pages
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Findings
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Started
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.items.map((scan: Scan) => (
                <tr key={scan.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {scan.application_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">
                    {scan.scan_type}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        statusColors[scan.status] || 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {(scan.status === 'running' || scan.status === 'pending') && (
                        <svg className="animate-spin -ml-0.5 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      )}
                      {scan.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {scan.pages_scanned}
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
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {scan.started_at
                      ? new Date(scan.started_at).toLocaleString()
                      : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    <Link
                      to={`/scans/${scan.id}`}
                      className="text-primary-600 hover:text-primary-900"
                    >
                      View
                    </Link>
                    {['pending', 'running', 'queued'].includes(scan.status) && (
                      <button
                        onClick={() => cancelMutation.mutate(scan.id)}
                        disabled={cancelMutation.isPending}
                        className="text-yellow-600 hover:text-yellow-900"
                        title="Cancel Scan"
                      >
                        <XMarkIcon className="h-5 w-5 inline" />
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
                        <TrashIcon className="h-5 w-5 inline" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-8 text-center text-gray-500">
            No scans yet. Start a scan from the Applications page.
          </div>
        )}
      </div>
    </div>
  )
}
