import { Fragment, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import {
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/solid'
import { useScanWebSocket, ScanFinding } from '../hooks/useScanWebSocket'

interface ScanProgressModalProps {
  isOpen: boolean
  onClose: () => void
  scanId: string
  applicationName: string
  scanType: string
  onCompleted?: () => void
}

function formatTime(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '--:--'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins >= 60) {
    const hours = Math.floor(mins / 60)
    const remainingMins = mins % 60
    return `${hours}h ${remainingMins}m`
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const severityColors: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
  info: 'bg-gray-100 text-gray-800 border-gray-200',
}

const severityIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  critical: ExclamationCircleIcon,
  high: ExclamationTriangleIcon,
  medium: ExclamationTriangleIcon,
  low: InformationCircleIcon,
  info: InformationCircleIcon,
}

function FindingItem({ finding }: { finding: ScanFinding }) {
  const Icon = severityIcons[finding.severity] || InformationCircleIcon
  const colorClass = severityColors[finding.severity] || severityColors.info

  return (
    <div className={`p-3 rounded-lg border ${colorClass} mb-2`}>
      <div className="flex items-start gap-2">
        <Icon className="h-5 w-5 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{finding.title}</span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-white/50">
              {finding.dpdp_section}
            </span>
          </div>
          <p className="text-xs mt-1 opacity-80 truncate">{finding.url}</p>
        </div>
      </div>
    </div>
  )
}

export default function ScanProgressModal({
  isOpen,
  onClose,
  scanId,
  applicationName,
  scanType,
  onCompleted,
}: ScanProgressModalProps) {
  const { isConnected, progress, findings, error } = useScanWebSocket(
    isOpen ? scanId : null,
    {
      onCompleted: () => {
        onCompleted?.()
      },
    }
  )

  // Close modal when scan completes
  useEffect(() => {
    if (progress?.status === 'completed' || progress?.status === 'failed' || progress?.status === 'cancelled') {
      // Give user a moment to see the final state
      const timeout = setTimeout(() => {
        onCompleted?.()
      }, 2000)
      return () => clearTimeout(timeout)
    }
  }, [progress?.status, onCompleted])

  const percent = progress?.percent || 0
  const pagesScanned = progress?.pages_scanned || 0
  const totalPages = progress?.total_pages || 0
  const currentUrl = progress?.current_url || ''
  const message = progress?.message || 'Initializing...'
  const elapsedSeconds = progress?.elapsed_seconds || 0
  const estimatedRemaining = progress?.estimated_remaining_seconds

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={() => {}}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white shadow-xl transition-all w-full max-w-2xl">
                {/* Header */}
                <div className="bg-primary-700 px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Dialog.Title className="text-lg font-semibold text-white">
                        Scanning: {applicationName}
                      </Dialog.Title>
                      <p className="text-sm text-primary-200 capitalize">{scanType} Scan</p>
                    </div>
                    <button
                      onClick={onClose}
                      className="text-primary-200 hover:text-white"
                    >
                      <XMarkIcon className="h-6 w-6" />
                    </button>
                  </div>
                </div>

                <div className="px-6 py-4">
                  {/* Connection Status */}
                  {!isConnected && (
                    <div className="mb-4 p-2 bg-yellow-50 text-yellow-800 text-sm rounded">
                      Connecting to scan updates...
                    </div>
                  )}

                  {error && (
                    <div className="mb-4 p-2 bg-red-50 text-red-800 text-sm rounded">
                      Error: {error}
                    </div>
                  )}

                  {/* Progress Bar */}
                  <div className="mb-6">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">Progress</span>
                      <span className="text-sm font-bold text-primary-600">{percent}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                      <div
                        className="bg-primary-600 h-4 rounded-full transition-all duration-500 flex items-center justify-center"
                        style={{ width: `${percent}%` }}
                      >
                        {percent > 10 && (
                          <span className="text-xs text-white font-medium">{percent}%</span>
                        )}
                      </div>
                    </div>
                    <p className="mt-2 text-sm text-gray-600">{message}</p>
                  </div>

                  {/* Stats Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-gray-50 rounded-lg p-3 text-center">
                      <p className="text-xs text-gray-500">Pages Scanned</p>
                      <p className="text-lg font-bold text-gray-900">
                        {pagesScanned} / {totalPages || '?'}
                      </p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3 text-center">
                      <p className="text-xs text-gray-500">Findings</p>
                      <p className="text-lg font-bold text-gray-900">
                        {progress?.findings_count || 0}
                      </p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3 text-center">
                      <p className="text-xs text-gray-500">Elapsed</p>
                      <p className="text-lg font-bold text-gray-900">
                        {formatTime(elapsedSeconds)}
                      </p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3 text-center">
                      <p className="text-xs text-gray-500">Est. Remaining</p>
                      <p className="text-lg font-bold text-gray-900">
                        {formatTime(estimatedRemaining)}
                      </p>
                    </div>
                  </div>

                  {/* Severity Breakdown */}
                  <div className="mb-6">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Findings by Severity</h4>
                    <div className="flex gap-2">
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        Critical: {progress?.critical_count || 0}
                      </span>
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                        High: {progress?.high_count || 0}
                      </span>
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        Medium: {progress?.medium_count || 0}
                      </span>
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        Low: {progress?.low_count || 0}
                      </span>
                    </div>
                  </div>

                  {/* Current URL */}
                  {currentUrl && (
                    <div className="mb-6">
                      <h4 className="text-sm font-medium text-gray-700 mb-1">Currently Scanning</h4>
                      <p className="text-xs text-gray-500 truncate bg-gray-50 p-2 rounded">
                        {currentUrl}
                      </p>
                    </div>
                  )}

                  {/* Live Findings */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      Live Findings ({findings.length})
                    </h4>
                    <div className="max-h-64 overflow-y-auto">
                      {findings.length === 0 ? (
                        <p className="text-sm text-gray-400 text-center py-4">
                          No findings yet...
                        </p>
                      ) : (
                        findings.slice(0, 20).map((finding, index) => (
                          <FindingItem key={finding.id || index} finding={finding} />
                        ))
                      )}
                      {findings.length > 20 && (
                        <p className="text-xs text-gray-500 text-center py-2">
                          + {findings.length - 20} more findings
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Footer */}
                <div className="bg-gray-50 px-6 py-3 flex justify-end">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Run in Background
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}
