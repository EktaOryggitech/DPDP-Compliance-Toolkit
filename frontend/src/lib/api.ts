import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password })
    return response.data
  },

  register: async (data: {
    email: string
    password: string
    full_name: string
  }) => {
    const response = await api.post('/auth/register', data)
    return response.data
  },

  refreshToken: async () => {
    const response = await api.post('/auth/refresh')
    return response.data
  },

  heartbeat: async () => {
    const response = await api.post('/auth/heartbeat')
    return response.data
  },

  logout: async () => {
    const response = await api.post('/auth/logout')
    return response.data
  },

  getSessionConfig: async () => {
    const response = await api.get('/auth/session-config')
    return response.data
  },
}

// Applications API
export const applicationsApi = {
  list: async (params?: { skip?: number; limit?: number }) => {
    const response = await api.get('/applications', { params })
    return response.data
  },

  get: async (id: string) => {
    const response = await api.get(`/applications/${id}`)
    return response.data
  },

  create: async (data: {
    name: string
    url?: string
    type: 'web' | 'windows'
    description?: string
    organization_id: string
    auth_config?: {
      auth_type: string
      login_url?: string
      username_field?: string
      password_field?: string
      credentials?: {
        username: string
        password: string
      }
    } | null
  }) => {
    const response = await api.post('/applications', data)
    return response.data
  },

  update: async (id: string, data: Partial<{
    name: string
    url: string
    description: string
    is_active: boolean
    auth_config: {
      auth_type: string
      login_url?: string
      username_field?: string
      password_field?: string
      credentials?: {
        username: string
        password: string
      }
    } | null
  }>) => {
    const response = await api.put(`/applications/${id}`, data)
    return response.data
  },

  delete: async (id: string) => {
    const response = await api.delete(`/applications/${id}`)
    return response.data
  },
}

// Scans API
export const scansApi = {
  list: async (params?: {
    application_id?: string
    status?: string
    skip?: number
    limit?: number
  }) => {
    const response = await api.get('/scans', { params })
    return response.data
  },

  get: async (id: string) => {
    const response = await api.get(`/scans/${id}`)
    return response.data
  },

  create: async (data: {
    application_id: string
    scan_type?: 'quick' | 'standard' | 'deep'
    config_overrides?: {
      max_pages?: number
      timeout_seconds?: number
      capture_screenshots?: boolean
    }
  }) => {
    const response = await api.post('/scans', data)
    return response.data
  },

  cancel: async (id: string) => {
    const response = await api.post(`/scans/${id}/cancel`)
    return response.data
  },

  delete: async (id: string) => {
    const response = await api.delete(`/scans/${id}`)
    return response.data
  },

  bulkDelete: async (ids: string[]) => {
    const response = await api.post('/scans/bulk-delete', ids)
    return response.data
  },

  deleteAll: async () => {
    const response = await api.delete('/scans/all')
    return response.data
  },

  getSummary: async () => {
    const response = await api.get('/scans/summary/stats')
    return response.data
  },
}

// Findings API
export const findingsApi = {
  list: async (params: {
    scan_id: string
    severity?: string
    check_type?: string
    skip?: number
    limit?: number
  }) => {
    const response = await api.get('/findings', { params })
    return response.data
  },

  getGrouped: async (scanId: string) => {
    const response = await api.get(`/findings/by-scan/${scanId}/grouped`)
    return response.data
  },
}

// Schedules API
export const schedulesApi = {
  list: async (params?: { application_id?: string; is_active?: boolean }) => {
    const response = await api.get('/schedules', { params })
    return response.data
  },

  create: async (data: {
    application_id: string
    frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly'
    time_of_day: string
    day_of_week?: number
    day_of_month?: number
    timezone?: string
  }) => {
    const response = await api.post('/schedules', data)
    return response.data
  },

  update: async (id: string, data: Partial<{
    frequency: string
    time_of_day: string
    is_active: boolean
  }>) => {
    const response = await api.put(`/schedules/${id}`, data)
    return response.data
  },

  delete: async (id: string) => {
    const response = await api.delete(`/schedules/${id}`)
    return response.data
  },
}

// Reports API
export const reportsApi = {
  downloadPdf: async (scanId: string) => {
    const response = await api.get(`/reports/${scanId}/pdf`, {
      responseType: 'blob',
    })
    return response.data
  },

  downloadExcel: async (scanId: string) => {
    const response = await api.get(`/reports/${scanId}/excel`, {
      responseType: 'blob',
    })
    return response.data
  },
}

// Scan Configuration API
export interface ScanConfiguration {
  id: string
  quick_pages: number
  standard_pages: number
  deep_pages: number
  created_at: string
  updated_at: string
  quick_min: number
  quick_max: number
  standard_min: number
  standard_max: number
  deep_min: number
  deep_max: number
}

export const scanConfigApi = {
  get: async (): Promise<ScanConfiguration> => {
    const response = await api.get('/scan-configuration')
    return response.data
  },

  update: async (data: {
    quick_pages?: number
    standard_pages?: number
    deep_pages?: number
  }): Promise<ScanConfiguration> => {
    const response = await api.put('/scan-configuration', data)
    return response.data
  },
}

// Dashboard API
export interface DashboardStats {
  total_scans: number
  critical_findings: number
  compliant_apps: number
  pending_scans: number
}

export interface FindingsBySectionItem {
  name: string
  findings: number
}

export interface FindingsBySeverityItem {
  name: string
  value: number
}

export interface DashboardData {
  stats: DashboardStats
  findings_by_section: FindingsBySectionItem[]
  findings_by_severity: FindingsBySeverityItem[]
}

export const dashboardApi = {
  getData: async (): Promise<DashboardData> => {
    const response = await api.get('/dashboard')
    return response.data
  },
}
