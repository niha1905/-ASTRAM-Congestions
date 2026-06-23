/**
 * ML Predictions API Client
 * Handles all communication with Flask backend
 */

const configuredMLApiUrl = process.env.NEXT_PUBLIC_ML_API_URL?.trim()
const configuredApiUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim()
const DEFAULT_API_BASE_URL = process.env.NODE_ENV !== 'production' ? 'http://127.0.0.1:5000' : ''

function getConfiguredBaseUrl(): string {
  const candidate = configuredMLApiUrl || configuredApiUrl
  if (candidate && candidate.includes('127.0.0.1:8000')) {
    return DEFAULT_API_BASE_URL
  }
  return candidate || DEFAULT_API_BASE_URL
}

const API_BASE_URL = getConfiguredBaseUrl()

function normalizeBase(base: string) {
  const b = (base || '').trim().replace(/\/+$/g, '')
  if (!b) return ''
  // Ensure base points to host (no trailing /api)
  return b.endsWith('/api') ? b.slice(0, -4) : b
}

export interface PredictionResponse<T> {
  success?: boolean
  error?: string
  [key: string]: any
}

class MLApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = normalizeBase(baseUrl)
  }

  private async request<T = any>(
    endpoint: string,
    method: 'GET' | 'POST' = 'GET',
    body?: any
  ): Promise<T> {
    // Ensure requests are sent to the backend API prefix
    const apiPrefix = '/api'
    const path = endpoint.startsWith('/api') ? endpoint : `${apiPrefix}${endpoint}`
    const url = `${this.baseUrl}${path}`

    try {
      const options: RequestInit = {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
      }

      if (body) {
        options.body = JSON.stringify(body)
      }

      const response = await fetch(url, options)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error(`API call failed to ${url}:`, error)
      throw error
    }
  }

  // Health Endpoints
  async getHealth() {
    return this.request('/health')
  }

  async getModelsStatus() {
    return this.request('/health/models')
  }

  // Prediction Endpoints
  async predictIncidentVolume(params: {
    zone: string
    corridor: string
    event_type: string
    hour: number
    weekday: number
    month: number
  }) {
    return this.request('/v1/predictions/incident-volume', 'POST', params)
  }

  async predictClosure(params: {
    event_type: string
    zone: string
    corridor: string
    priority: string
    hour: number
    duration_min: number
  }) {
    return this.request('/v1/predictions/closure-probability', 'POST', params)
  }

  async predictResources(params: {
    event_type: string
    priority: string
    zone: string
    corridor: string
    hour: number
    closure_prob?: number
  }) {
    return this.request('/v1/predictions/resources', 'POST', params)
  }

  async predictHotspotRisk(params: {
    junction: string
    hour: number
    weekday: number
    event_type: string
  }) {
    return this.request('/v1/predictions/hotspot-risk', 'POST', params)
  }

  async predictScenario(params: {
    base_scenario: string
    perturbation: string
  }) {
    return this.request('/v1/predictions/scenario', 'POST', params)
  }

  async predictDuration(params: {
    event_cause?: string
    event_type?: string
    veh_type?: string
    vehicle_type?: string
    corridor: string
    hour: number
    priority: string
  }) {
    return this.request('/v1/predictions/duration', 'POST', params)
  }

  async predictImpactScore(params: {
    event_cause?: string
    event_type?: string
    corridor: string
    priority: string
    hour: number
    weekday: number
    closure_probability?: number
    closure_prob?: number
  }) {
    return this.request('/v1/predictions/impact-score', 'POST', params)
  }

  async predictCascade(params: {
    corridor: string
    event_cause?: string
    event_type?: string
    hour: number
  }) {
    return this.request('/v1/predictions/cascade', 'POST', params)
  }

  async predictParkingOverflow(params: {
    event_cause?: string
    event_type?: string
    corridor: string
    hour: number
    weekday: number
    closure_probability?: number
    closure_prob?: number
  }) {
    return this.request('/v1/predictions/parking-overflow', 'POST', params)
  }

  async predictGreenCorridor(params: {
    origin_corridor?: string
    destination_corridor?: string
    source?: string
    destination?: string
  }) {
    return this.request('/v1/predictions/green-corridor', 'POST', params)
  }

  // Batch Predictions
  async batchPredict(requests: Array<{
    type: string
    params: any
  }>) {
    return this.request('/v1/predictions/batch', 'POST', { requests })
  }

  // Convenience methods for common use cases
  async analyzeIncident(incident: {
    event_type: string
    zone: string
    corridor: string
    priority: string
    hour: number
    duration_min: number
  }) {
    const closure = await this.predictClosure({
      event_type: incident.event_type,
      zone: incident.zone,
      corridor: incident.corridor,
      priority: incident.priority,
      hour: incident.hour,
      duration_min: incident.duration_min,
    }) as PredictionResponse<any>

    const resources = await this.predictResources({
      event_type: incident.event_type,
      priority: incident.priority,
      zone: incident.zone,
      corridor: incident.corridor,
      hour: incident.hour,
      closure_prob: closure.closure_probability || 0,
    }) as PredictionResponse<any>

    return {
      closure,
      resources,
      timestamp: new Date().toISOString(),
    }
  }
}

export const mlApiClient = new MLApiClient()
