import type {
  AiModel,
  AnalysisResult,
  CascadeResult,
  EmergencyRoute,
  EventInput,
  OperationsBrief,
  ScenarioResult,
} from './types'
import { NEWS_DEFAULT_LIMIT, REQUEST_TIMEOUT_MS } from './constants'

const DEFAULT_API_BASE_URL = process.env.NODE_ENV !== 'production' ? 'http://localhost:5000/api' : ''

export function getBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL
}

function normalizeBaseUrl(base: string): string {
  const trimmed = base.trim().replace(/\/+$|\s+$/g, '')
  if (!trimmed) return ''
  return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`
}

async function realFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const base = normalizeBaseUrl(getBaseUrl())
  if (!base) {
    throw new Error(
      'API base URL is not configured. Set NEXT_PUBLIC_API_BASE_URL or run the local backend on http://localhost:5000/api.'
    )
  }

  const url = `${base}${path}`
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    const res = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`Request failed: ${res.status} ${res.statusText}${text ? ` — ${text}` : ''}`)
    }

    return (await res.json()) as T
  } catch (error: unknown) {
    const name = (error as any)?.name ?? ''
    if (name === 'AbortError') {
      throw new Error(
        `Request to ${path} timed out after ${REQUEST_TIMEOUT_MS / 1000} seconds. Confirm the backend is running at ${base}.`
      )
    }

    const message = error instanceof Error ? error.message : String(error)
    if (message.includes('Failed to fetch')) {
      throw new Error(
        `Network error while requesting ${path}. Confirm the backend is running at ${base} and that CORS allows requests from this app.`
      )
    }

    throw error
  } finally {
    clearTimeout(timeout)
  }
}



export const api = {
  async health(): Promise<{ status: string }> {
    try {
      const r = await realFetch<{ status: string }>('/health')
      return { status: r.status ?? 'ok' }
    } catch {
      return { status: 'unreachable' }
    }
  },

  dashboard(): Promise<any> {
    return realFetch<any>('/dashboard', { method: 'GET' })
  },

  analyzeDashboard(events: any[]): Promise<any> {
    return realFetch<any>('/dashboard', { method: 'POST', body: JSON.stringify({ events }) })
  },

  analyzeEvent(input: EventInput): Promise<AnalysisResult> {
    return realFetch('/analyze_event', { method: 'POST', body: JSON.stringify(input) })
  },

  simulateScenario(baseEvent: string, scenario: string): Promise<ScenarioResult> {
    return realFetch('/simulate_scenario', {
      method: 'POST',
      body: JSON.stringify({ baseEvent, scenario }),
    })
  },

  emergencyRoute(source: string, destination: string): Promise<EmergencyRoute> {
    return realFetch('/emergency_route', {
      method: 'POST',
      body: JSON.stringify({ source, destination }),
    })
  },

  cascadeSpread(): Promise<CascadeResult> {
    return realFetch('/cascade_spread', { method: 'POST', body: JSON.stringify({}) })
  },

  eventReplay(): Promise<any[]> {
    return realFetch<any[]>('/event_replay', { method: 'GET' })
  },

  models(): Promise<AiModel[]> {
    return realFetch<AiModel[]>('/models', { method: 'GET' })
  },

  operationsBrief(event: string, region: string, timeWindow: string): Promise<OperationsBrief> {
    return realFetch('/operations_brief', {
      method: 'POST',
      body: JSON.stringify({ event, region, timeWindow }),
    })
  },

  /**
   * Fetch recent news items about Bangalore events.
   * Tries backend `/news/events` first; if backend unreachable,
   * falls back to fetching Google News RSS directly from the browser.
   */
  async fetchNews(query = 'bangalore event traffic', limit = NEWS_DEFAULT_LIMIT): Promise<any[]> {
    // try backend first
    try {
      const r = await realFetch<any>('/news/events', { method: 'GET' })
      return (r && r.items) || []
    } catch (err) {
      // backend unreachable — try client-side RSS fetch as fallback
    }

    try {
      const rss = `https://news.google.com/rss/search?q=${encodeURIComponent(query)}&hl=en-IN&gl=IN&ceid=IN:en`
      const res = await fetch(rss, { method: 'GET' })
      if (!res.ok) return []
      const text = await res.text()
      const parser = new DOMParser()
      const doc = parser.parseFromString(text, 'application/xml')
      const all = Array.from(doc.querySelectorAll('item')).map((it) => ({
        title: it.querySelector('title')?.textContent || '',
        link: it.querySelector('link')?.textContent || '',
        summary: it.querySelector('description')?.textContent || '',
        published: it.querySelector('pubDate')?.textContent || null,
      }))
      const oneWeekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000
      const KEYWORDS = [
        // planned events / gatherings
        'concert', 'match', 'festival', 'marathon', 'parade', 'rally', 'protest', 'conference', 'exhibition', 'fair', 'ceremony', 'procession', 'march', 'event', 'program', 'function', 'public event', 'gathering', 'meeting', 'sports', 'tournament', 'vip', 'motorcade', 'state visit',
        // unplanned incidents / traffic-impacting
        'fire', 'accident', 'collision', 'stampede', 'riot', 'closure', 'blocked', 'road closed', 'traffic', 'diversion', 'roadblock', 'strike', 'demonstration', 'evacuation', 'collapse', 'sinkhole', 'flood', 'landslide', 'utility work', 'roadworks', 'construction', 'maintenance', 'cancellation', 'rescheduled'
      ]
      const LOCATION_KEYWORDS = ['bangalore', 'bengaluru', 'bengalooru', 'blr', 'karnataka']

      // Strict: require both keyword + Bangalore mention
      let recent = all.filter((it) => {
        if (!it.published) return false
        const d = Date.parse(it.published)
        if (isNaN(d) || d < oneWeekAgo) return false
        const text = (it.title + ' ' + (it.summary || '')).toLowerCase()
        const hasKeyword = KEYWORDS.some((k) => text.includes(k))
        const hasLocation = LOCATION_KEYWORDS.some((lk) => text.includes(lk))
        return hasKeyword && hasLocation
      }).slice(0, limit)

      // Relax: if nothing found, allow keyword-only recent items
      if (recent.length === 0) {
        recent = all.filter((it) => {
          if (!it.published) return false
          const d = Date.parse(it.published)
          if (isNaN(d) || d < oneWeekAgo) return false
          const text = (it.title + ' ' + (it.summary || '')).toLowerCase()
          return KEYWORDS.some((k) => text.includes(k))
        }).slice(0, limit)
      }

      // Final fallback: return most recent items from the last week
      if (recent.length === 0) {
        recent = all.filter((it) => {
          if (!it.published) return false
          const d = Date.parse(it.published)
          return !isNaN(d) && d >= oneWeekAgo
        }).slice(0, limit)
      }

      return recent
    } catch (e) {
      return []
    }
  },
}
