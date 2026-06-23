import { getBaseUrl } from './api'

const MAPPLS_SDK_KEY = process.env.NEXT_PUBLIC_MAPPLS_REST_API_KEY?.trim() ?? ''
const MAPPLS_SDK_LAYER = process.env.NEXT_PUBLIC_MAPPLS_SDK_LAYER?.trim() || 'vector'
const MAPPLS_SDK_SCRIPT_BASE = 'https://apis.mappls.com/advancedmaps/api'

let loadPromise: Promise<void> | null = null
let resolvedSdkKey: string | null = null
let configFetchPromise: Promise<string | null> | null = null

declare global {
  interface Window {
    mappls?: {
      Map: new (id: string, options: Record<string, unknown>) => MapplsMap
      Marker: new (options: Record<string, unknown>) => unknown
      Polyline: new (options: Record<string, unknown>) => unknown
      Circle: new (options: Record<string, unknown>) => unknown
      remove: (options: { map: MapplsMap; layer: unknown }) => void
    }
  }
}

export interface MapplsMap {
  remove?: () => void
  setCenter?: (center: { lat: number; lng: number }) => void
  setZoom?: (zoom: number) => void
  fitbounds?: (bounds: { sw: { lat: number; lng: number }; ne: { lat: number; lng: number } }, options?: Record<string, unknown>) => void
}

function normalizeApiBase(base: string): string {
  const trimmed = base.replace(/\/+$|\s+$/g, '')
  if (!trimmed) return ''
  return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`
}

async function fetchBackendBearerToken(): Promise<string | null> {
  const base = normalizeApiBase(getBaseUrl())
  if (!base) return null

  try {
    const res = await fetch(`${base}/mappls/config`, { method: 'GET' })
    if (!res.ok) return null
    const data = (await res.json()) as { access_token?: string | null }
    return data.access_token?.trim() || null
  } catch {
    return null
  }
}

export async function resolveMapplsSdkKey(): Promise<string> {
  if (resolvedSdkKey) return resolvedSdkKey

  // advancedmaps SDK URL requires OAuth bearer token in path (static keys return 401)
  if (getBaseUrl()) {
    if (!configFetchPromise) {
      configFetchPromise = fetchBackendBearerToken()
    }
    const bearer = await configFetchPromise
    if (bearer) {
      resolvedSdkKey = bearer
      return bearer
    }
  }

  if (MAPPLS_SDK_KEY) {
    resolvedSdkKey = MAPPLS_SDK_KEY
    return resolvedSdkKey
  }

  throw new Error(
    'Mappls bearer token unavailable. Set MAPPLS_CLIENT_ID/MAPPLS_CLIENT_SECRET and run the backend, or set NEXT_PUBLIC_MAPPLS_REST_API_KEY.',
  )
}

export function getMapplsAccessToken(): string {
  return resolvedSdkKey ?? MAPPLS_SDK_KEY
}

export function isMapplsConfigured(): boolean {
  return Boolean(MAPPLS_SDK_KEY || getBaseUrl())
}

export function buildMapplsSdkScriptUrl(sdkKey: string, layer = MAPPLS_SDK_LAYER): string {
  return `${MAPPLS_SDK_SCRIPT_BASE}/${encodeURIComponent(sdkKey)}/map_sdk?v=3.0&layer=${encodeURIComponent(layer)}`
}

function appendMapplsScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[data-mappls-sdk="true"][src="${src}"]`)
    if (existing) {
      if (window.mappls?.Map) {
        resolve()
        return
      }
      existing.addEventListener('load', () => {
        if (window.mappls?.Map) resolve()
        else reject(new Error('Mappls SDK loaded but window.mappls.Map is undefined'))
      })
      existing.addEventListener('error', () => reject(new Error('Failed to load Mappls SDK')))
      return
    }

    const timeout = setTimeout(() => {
      reject(new Error('Mappls SDK loading timed out (30s)'))
    }, 30000)

    const script = document.createElement('script')
    script.dataset.mapplsSdk = 'true'
    script.src = src
    script.async = true
    script.onload = () => {
      clearTimeout(timeout)
      if (window.mappls?.Map) {
        resolve()
      } else {
        reject(new Error('Mappls SDK loaded but window.mappls.Map is undefined'))
      }
    }
    script.onerror = () => {
      clearTimeout(timeout)
      reject(new Error('Failed to load Mappls SDK'))
    }
    document.head.appendChild(script)
  })
}

export function loadMapplsSdk(): Promise<void> {
  if (typeof window === 'undefined') {
    return Promise.resolve()
  }

  if (window.mappls?.Map) {
    return Promise.resolve()
  }

  if (loadPromise) {
    return loadPromise
  }

  loadPromise = resolveMapplsSdkKey()
    .then(async (bearerToken) => {
      const layers = Array.from(new Set([MAPPLS_SDK_LAYER, 'raster', 'vector']))
      let lastError: Error | null = null

      for (const layer of layers) {
        try {
          await appendMapplsScript(buildMapplsSdkScriptUrl(bearerToken, layer))
          return
        } catch (error) {
          lastError = error instanceof Error ? error : new Error(String(error))
          document.querySelectorAll('script[data-mappls-sdk="true"]').forEach((node) => node.remove())
        }
      }

      throw lastError ?? new Error('Failed to load Mappls SDK')
    })
    .catch((error) => {
      loadPromise = null
      throw error
    })

  return loadPromise
}

export function latLngPath(coords: [number, number][]): { lat: number; lng: number }[] {
  return coords.map(([lat, lng]) => ({ lat, lng }))
}

export function removeMapplsLayer(map: MapplsMap | null, layer: unknown) {
  if (!map || !layer || !window.mappls?.remove) return
  try {
    window.mappls.remove({ map, layer })
  } catch {
    /* ignore stale layer removal */
  }
}
