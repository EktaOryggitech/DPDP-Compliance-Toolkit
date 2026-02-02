import { useEffect, useRef, useState, useCallback } from 'react'

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1'

export interface ScanProgressData {
  scan_id: string
  status: string
  percent: number
  pages_scanned: number
  total_pages: number
  current_url: string | null
  message: string
  findings_count: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  elapsed_seconds: number
  estimated_remaining_seconds: number | null
  timestamp: string
}

export interface ScanFinding {
  id: string
  title: string
  severity: string
  status: string
  dpdp_section: string
  description: string
  remediation: string
  url: string
}

export interface ScanCompletedData {
  scan_id: string
  status: string
  summary: {
    pages_scanned: number
    findings_count: number
    overall_score: number
    critical: number
    high: number
    medium: number
    low: number
  }
}

interface UseScanWebSocketOptions {
  onProgress?: (data: ScanProgressData) => void
  onFinding?: (finding: ScanFinding) => void
  onCompleted?: (data: ScanCompletedData) => void
  onError?: (error: string) => void
  onConnected?: () => void
  onDisconnected?: () => void
}

export function useScanWebSocket(scanId: string | null, options: UseScanWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [progress, setProgress] = useState<ScanProgressData | null>(null)
  const [findings, setFindings] = useState<ScanFinding[]>([])
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Use refs for callbacks to avoid reconnecting on every render
  const optionsRef = useRef(options)
  optionsRef.current = options

  const connect = useCallback(() => {
    if (!scanId) return

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close()
    }

    const ws = new WebSocket(`${WS_BASE_URL}/scans/ws/${scanId}`)

    ws.onopen = () => {
      setIsConnected(true)
      setError(null)
      optionsRef.current.onConnected?.()

      // Start ping interval to keep connection alive
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 30000)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        switch (data.type) {
          case 'connected':
            // Initial connection confirmation
            break

          case 'progress':
            const progressData: ScanProgressData = {
              scan_id: data.scan_id,
              status: data.status,
              percent: data.percent,
              pages_scanned: data.pages_scanned,
              total_pages: data.total_pages || 0,
              current_url: data.current_url,
              message: data.message,
              findings_count: data.findings_count,
              critical_count: data.critical_count || 0,
              high_count: data.high_count || 0,
              medium_count: data.medium_count || 0,
              low_count: data.low_count || 0,
              elapsed_seconds: data.elapsed_seconds || 0,
              estimated_remaining_seconds: data.estimated_remaining_seconds,
              timestamp: data.timestamp,
            }
            setProgress(progressData)
            optionsRef.current.onProgress?.(progressData)
            break

          case 'finding':
            const finding: ScanFinding = {
              id: data.finding.id,
              title: data.finding.title,
              severity: data.finding.severity,
              status: data.finding.status,
              dpdp_section: data.finding.dpdp_section,
              description: data.finding.description,
              remediation: data.finding.remediation,
              url: data.finding.url,
            }
            setFindings((prev) => [finding, ...prev])
            optionsRef.current.onFinding?.(finding)
            break

          case 'completed':
            optionsRef.current.onCompleted?.(data as ScanCompletedData)
            break

          case 'error':
            setError(data.error)
            optionsRef.current.onError?.(data.error)
            break

          case 'pong':
            // Ping response, connection is alive
            break

          default:
            console.log('Unknown WebSocket message type:', data.type)
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      optionsRef.current.onDisconnected?.()

      // Clear ping interval
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
      }

      // Attempt to reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        if (scanId) {
          connect()
        }
      }, 3000)
    }

    ws.onerror = (event) => {
      console.error('WebSocket error:', event)
      setError('WebSocket connection error')
    }

    wsRef.current = ws
  }, [scanId]) // Only depend on scanId, not options

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  const clearFindings = useCallback(() => {
    setFindings([])
  }, [])

  useEffect(() => {
    if (scanId) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [scanId, connect, disconnect])

  return {
    isConnected,
    progress,
    findings,
    error,
    disconnect,
    clearFindings,
  }
}
