import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Cog6ToothIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { scanConfigApi, ScanConfiguration } from '../lib/api'

function formatTime(pages: number): string {
  // Formula: timeout = (180 + pages × 30) × 1.2
  const timeoutSeconds = (180 + pages * 30) * 1.2
  const minutes = Math.floor(timeoutSeconds / 60)
  if (minutes < 60) {
    return `~${minutes} min`
  }
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  if (remainingMinutes === 0) {
    return `~${hours} hr`
  }
  return `~${hours} hr ${remainingMinutes} min`
}

interface SliderProps {
  label: string
  value: number
  min: number
  max: number
  onChange: (value: number) => void
  description: string
}

function PageSlider({ label, value, min, max, onChange, description }: SliderProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-medium text-gray-900">{label}</h3>
        <span className="text-sm text-gray-500">{description}</span>
      </div>

      <div className="mt-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Pages: {value}</span>
          <span className="text-sm text-gray-500">Estimated time: {formatTime(value)}</span>
        </div>

        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(parseInt(e.target.value, 10))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
        />

        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>{min}</span>
          <span>{max}</span>
        </div>
      </div>
    </div>
  )
}

export default function Settings() {
  const queryClient = useQueryClient()

  const [quickPages, setQuickPages] = useState(20)
  const [standardPages, setStandardPages] = useState(75)
  const [deepPages, setDeepPages] = useState(200)
  const [hasChanges, setHasChanges] = useState(false)

  const { data: config, isLoading } = useQuery({
    queryKey: ['scan-configuration'],
    queryFn: scanConfigApi.get,
  })

  // Update local state when config is loaded
  useEffect(() => {
    if (config) {
      setQuickPages(config.quick_pages)
      setStandardPages(config.standard_pages)
      setDeepPages(config.deep_pages)
      setHasChanges(false)
    }
  }, [config])

  const updateMutation = useMutation({
    mutationFn: scanConfigApi.update,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scan-configuration'] })
      toast.success('Scan configuration saved successfully')
      setHasChanges(false)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to save configuration')
    },
  })

  const handleSave = () => {
    updateMutation.mutate({
      quick_pages: quickPages,
      standard_pages: standardPages,
      deep_pages: deepPages,
    })
  }

  const handleReset = () => {
    if (config) {
      setQuickPages(config.quick_pages)
      setStandardPages(config.standard_pages)
      setDeepPages(config.deep_pages)
      setHasChanges(false)
    }
  }

  const handleQuickChange = (value: number) => {
    setQuickPages(value)
    setHasChanges(true)
  }

  const handleStandardChange = (value: number) => {
    setStandardPages(value)
    setHasChanges(true)
  }

  const handleDeepChange = (value: number) => {
    setDeepPages(value)
    setHasChanges(true)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Cog6ToothIcon className="h-8 w-8 text-gray-400" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Scan Configuration</h1>
            <p className="text-sm text-gray-500">
              Configure the number of pages scanned for each scan type
            </p>
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          These settings apply globally. When users start a scan, they select a scan type
          (Quick, Standard, or Deep), and the scan will crawl the configured number of pages.
        </p>
      </div>

      {/* Sliders */}
      <div className="space-y-4">
        <PageSlider
          label="Quick Scan"
          value={quickPages}
          min={config?.quick_min ?? 10}
          max={config?.quick_max ?? 50}
          onChange={handleQuickChange}
          description="Fast compliance check"
        />

        <PageSlider
          label="Standard Scan"
          value={standardPages}
          min={config?.standard_min ?? 50}
          max={config?.standard_max ?? 150}
          onChange={handleStandardChange}
          description="Balanced compliance audit"
        />

        <PageSlider
          label="Deep Scan"
          value={deepPages}
          min={config?.deep_min ?? 150}
          max={config?.deep_max ?? 500}
          onChange={handleDeepChange}
          description="Comprehensive analysis"
        />
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-end gap-3 pt-4 border-t">
        <button
          type="button"
          onClick={handleReset}
          disabled={!hasChanges}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Reset
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={!hasChanges || updateMutation.isPending}
          className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {updateMutation.isPending ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>
    </div>
  )
}
