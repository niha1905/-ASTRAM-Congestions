'use client'

import { useEffect, useId, useRef, useState } from 'react'
import type { Corridor, EmergencyRoute, EventLocation, Hotspot } from '@/lib/types'
import { RISK_HEX, riskHexFromScore } from '@/lib/ui'
import { MAP_DEFAULT_ZOOM, MAP_FLY_TO_ZOOM } from '@/lib/constants'
import {
  getMapplsAccessToken,
  isMapplsConfigured,
  latLngPath,
  loadMapplsSdk,
  removeMapplsLayer,
  type MapplsMap,
} from '@/lib/mappls-loader'

export interface MapLayers {
  corridors: boolean
  hotspots: boolean
  events: boolean
  heatmap: boolean
  routes?: boolean
}

interface MapplsMapProps {
  center: [number, number]
  corridors?: Corridor[]
  hotspots?: Hotspot[]
  events?: EventLocation[]
  route?: EmergencyRoute | null
  layers: MapLayers
  zoom?: number
  selectedEvent?: EventLocation | null
  onEventSelect?: (event: EventLocation | null) => void
  onMapplsError?: (hasError: boolean) => void
}

function getLocalityColor(name: string): string {
  const n = name.toLowerCase()
  if (n.includes('koramangala')) return '#8b5cf6'
  if (n.includes('indiranagar')) return '#06b6d4'
  if (n.includes('mg road') || n.includes('cbd')) return '#ef4444'
  if (n.includes('whitefield')) return '#f59e0b'
  if (n.includes('electronic city')) return '#10b981'
  if (n.includes('yelahanka')) return '#d946ef'
  if (n.includes('hebbal')) return '#3b82f6'
  if (n.includes('jayanagar')) return '#f43f5e'
  if (n.includes('rajajinagar')) return '#84cc16'
  return '#3b82f6'
}

function addPolyline(
  map: MapplsMap,
  coords: [number, number][],
  options: Record<string, unknown>,
): unknown | null {
  if (!window.mappls?.Polyline || coords.length < 2) return null
  try {
    return new window.mappls.Polyline({
      map,
      path: latLngPath(coords),
      strokeOpacity: 0.9,
      strokeWeight: 6,
      ...options,
    })
  } catch {
    return null
  }
}

function addMarker(
  map: MapplsMap,
  position: [number, number],
  options: Record<string, unknown>,
): unknown | null {
  if (!window.mappls?.Marker) return null
  try {
    return new window.mappls.Marker({
      map,
      position: { lat: position[0], lng: position[1] },
      ...options,
    })
  } catch {
    return null
  }
}

function addCircle(
  map: MapplsMap,
  position: [number, number],
  options: Record<string, unknown>,
): unknown | null {
  if (!window.mappls?.Circle) return null
  try {
    return new window.mappls.Circle({
      map,
      center: { lat: position[0], lng: position[1] },
      ...options,
    })
  } catch {
    return null
  }
}

export default function MapplsMap({
  center,
  corridors = [],
  hotspots = [],
  events = [],
  route = null,
  layers,
  zoom = MAP_DEFAULT_ZOOM,
  selectedEvent = null,
  onEventSelect,
  onMapplsError,
}: MapplsMapProps) {
  const mapId = useId().replace(/:/g, '')
  const mapRef = useRef<MapplsMap | null>(null)
  const overlayRef = useRef<unknown[]>([])
  const [ready, setReady] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isMapplsConfigured()) {
      onMapplsError?.(true)
      return
    }

    let cancelled = false

    loadMapplsSdk()
      .then(() => {
        if (cancelled || !window.mappls?.Map) {
          setError('Mappls SDK not properly initialized')
          onMapplsError?.(true)
          return
        }
        const container = document.getElementById(mapId)
        if (!container) {
          setError('Map container not found')
          onMapplsError?.(true)
          return
        }
        const map = new window.mappls.Map(mapId, {
          center: { lat: center[0], lng: center[1] },
          zoom,
          zoomControl: true,
          location: false,
        })
        mapRef.current = map
        setReady(true)
        setError(null)
        onMapplsError?.(false)
      })
      .catch((err) => {
        if (!cancelled) {
          const errorMsg = err instanceof Error ? err.message : 'Failed to load Mappls map'
          setError(errorMsg)
          onMapplsError?.(true)
        }
      })

    return () => {
      cancelled = true
      overlayRef.current.forEach((layer) => removeMapplsLayer(mapRef.current, layer))
      overlayRef.current = []
      mapRef.current?.remove?.()
      mapRef.current = null
      setReady(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapId])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return

    if (selectedEvent?.position) {
      const plan = selectedEvent.traffic_plan
      if (plan?.path && Array.isArray(plan.path) && plan.path.length >= 2) {
        const allPoints = [
          ...(plan.path as [number, number][]),
          ...(Array.isArray(plan.diversion_path) ? (plan.diversion_path as [number, number][]) : []),
        ]
        const lats = allPoints.map((p) => p[0])
        const lngs = allPoints.map((p) => p[1])
        map.fitbounds?.(
          {
            sw: { lat: Math.min(...lats), lng: Math.min(...lngs) },
            ne: { lat: Math.max(...lats), lng: Math.max(...lngs) },
          },
          { padding: 60 },
        )
      } else {
        map.setCenter?.({ lat: selectedEvent.position[0], lng: selectedEvent.position[1] })
        map.setZoom?.(MAP_FLY_TO_ZOOM)
      }
    }
  }, [selectedEvent, ready])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready || !window.mappls) return

    overlayRef.current.forEach((layer) => removeMapplsLayer(map, layer))
    overlayRef.current = []

    const push = (layer: unknown | null) => {
      if (layer) overlayRef.current.push(layer)
    }

    if (layers.corridors) {
      corridors.forEach((c) => {
        if (!c?.path || c.path.length < 2) return
        push(
          addPolyline(map, c.path as [number, number][], {
            strokeColor: riskHexFromScore(c.congestion),
            strokeWeight: 6,
            popupHtml: `${c.name} · ${c.congestion}% load`,
          }),
        )
      })
    }

    if (layers.hotspots) {
      hotspots.forEach((h) => {
        if (!h?.position) return
        const color = RISK_HEX[h.level]
        push(
          addCircle(map, h.position as [number, number], {
            radius: 180,
            strokeColor: color,
            strokeWeight: 2,
            fillColor: color,
            fillOpacity: 0.25,
            popupHtml: `${h.name} · risk ${h.risk}%`,
          }),
        )
      })
    }

    if (layers.events) {
      events.forEach((e) => {
        // prefer news-geocoded position and normalize shapes {lat, lon} -> [lat, lon]
        let pos: any = e.position ?? null
        if ((!pos || (Array.isArray(pos) && pos.length < 2)) && e.news && (e.news.position || e.news.lat || e.news.lon)) {
          const np = e.news.position || (e.news.lat ? { lat: e.news.lat, lon: e.news.lon } : null)
          if (np && typeof np === 'object' && 'lat' in np && 'lon' in np) {
            pos = [np.lat, np.lon]
          }
        }
        if (pos && !Array.isArray(pos) && typeof pos === 'object' && 'lat' in pos && 'lon' in pos) {
          pos = [pos.lat, pos.lon]
        }
        if (!pos) return
        const score = (e.predictions?.impact?.impact_score as number) ?? e.impact_score ?? 0
        const color = riskHexFromScore(score)
        const isSelected = selectedEvent && selectedEvent.id === e.id
        const border = isSelected ? '3px solid #fff' : `0 0 0 6px ${color}33`
        push(
          addMarker(map, pos as [number, number], {
            html: `<div style="display:flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:8px;background:${color};box-shadow:${border};color:#000;font-size:11px;font-weight:700;cursor:pointer">E</div>`,
            popupHtml: `${e.name} · ${e.attendance?.toLocaleString?.() ?? e.attendance ?? ''}`,
            draggable: false,
            clickable: true,
            callback: () => onEventSelect?.(e),
          }),
        )
      })
    }

    if (layers.heatmap) {
      events.forEach((e) => {
        // normalize position shape
        let pos: any = e.position ?? null
        if ((!pos || (Array.isArray(pos) && pos.length < 2)) && e.news && (e.news.position || e.news.lat || e.news.lon)) {
          const np = e.news.position || (e.news.lat ? { lat: e.news.lat, lon: e.news.lon } : null)
          if (np && typeof np === 'object' && 'lat' in np && 'lon' in np) {
            pos = [np.lat, np.lon]
          }
        }
        if (pos && !Array.isArray(pos) && typeof pos === 'object' && 'lat' in pos && 'lon' in pos) {
          pos = [pos.lat, pos.lon]
        }
        if (!pos) return
        const color = getLocalityColor(e.name || e.news?.title || '')
        push(
          addCircle(map, pos as [number, number], {
            radius: 450,
            strokeColor: color,
            strokeWeight: 0,
            fillColor: color,
            fillOpacity: 0.12,
          }),
        )
      })
    }

    if (selectedEvent?.traffic_plan) {
      const plan = selectedEvent.traffic_plan
      const routeSource = plan.source === 'mappls' ? ' · via Mappls' : ''

      if (plan.path && Array.isArray(plan.path) && plan.path.length >= 2) {
        push(
          addPolyline(map, plan.path as [number, number][], {
            strokeColor: '#ef4444',
            strokeWeight: 6,
            strokeOpacity: 0.95,
            popupHtml: `Affected: ${plan.affected || 'Congested Area'}${routeSource}`,
          }),
        )
        push(
          addMarker(map, plan.path[0] as [number, number], {
            html: `<div style="display:flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:#ef4444;border:2px solid #fff;color:#fff;font-size:12px;font-weight:700">!</div>`,
          }),
        )
      }

      if (plan.diversion_path && Array.isArray(plan.diversion_path) && plan.diversion_path.length >= 2) {
        push(
          addPolyline(map, plan.diversion_path as [number, number][], {
            strokeColor: '#10b981',
            strokeWeight: 6,
            strokeOpacity: 0.95,
            popupHtml: `Divert to: ${plan.divert_to || 'Detour Path'}${routeSource}`,
          }),
        )
        push(
          addMarker(map, plan.diversion_path[0] as [number, number], {
            html: `<div style="display:flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:#10b981;border:2px solid #fff;color:#fff;font-size:12px;font-weight:700">→</div>`,
          }),
        )
      }
    }

    if ((layers.routes ?? true) && route && route.path.length >= 2) {
      push(
        addPolyline(map, route.path as [number, number][], {
          strokeColor: '#22d3ee',
          strokeWeight: 6,
          strokeOpacity: 0.95,
          popupHtml: 'Primary Route',
          fitbounds: true,
        }),
      )

      const altPath = (route as EmergencyRoute & { alternativePath?: [number, number][] }).alternativePath
      if (altPath && altPath.length >= 2) {
        push(
          addPolyline(map, altPath, {
            strokeColor: '#a855f7',
            strokeWeight: 5,
            strokeOpacity: 0.75,
            popupHtml: 'Alternative Route (Detour)',
          }),
        )
      }

      push(
        addCircle(map, route.path[0] as [number, number], {
          radius: 40,
          strokeColor: '#0ea5e9',
          strokeWeight: 3,
          fillColor: '#ffffff',
          fillOpacity: 1,
          popupHtml: `Start: ${route.source}`,
        }),
      )
      push(
        addCircle(map, route.path[route.path.length - 1] as [number, number], {
          radius: 40,
          strokeColor: '#14b8a6',
          strokeWeight: 3,
          fillColor: '#ffffff',
          fillOpacity: 1,
          popupHtml: `End: ${route.destination}`,
        }),
      )

      ;(route.signals ?? []).forEach((s) => {
        if (!s?.position) return
        push(
          addCircle(map, s.position as [number, number], {
            radius: 35,
            strokeColor: '#10b981',
            strokeWeight: 2,
            fillColor: '#10b981',
            fillOpacity: 0.9,
            popupHtml: `${s.name} · ${s.action}`,
          }),
        )
      })
      ;(route.bottlenecks ?? []).forEach((b) => {
        if (!b?.position) return
        push(
          addCircle(map, b.position as [number, number], {
            radius: 45,
            strokeColor: '#ef4444',
            strokeWeight: 2,
            fillColor: '#ef4444',
            fillOpacity: 0.6,
            popupHtml: `Bottleneck · ${b.name}`,
          }),
        )
      })
    }
  }, [corridors, hotspots, events, route, layers, selectedEvent, ready, onEventSelect])

  if (!isMapplsConfigured()) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-card text-xs text-muted-foreground">
        Set NEXT_PUBLIC_MAPPLS_REST_API_KEY to your static Mappls REST key from the Mappls Console.
      </div>
    )
  }

  return (
    <div className="relative h-full w-full">
      <div id={mapId} className="mappls-container h-full w-full" aria-label="Traffic intelligence map" />
      {!ready && !error ? (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-card/40 text-xs text-muted-foreground">
          Loading Mappls map…
        </div>
      ) : null}
      {error ? (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-destructive/10 text-xs text-destructive">
          <div className="text-center">
            <div className="mb-1 font-semibold">Mappls map unavailable</div>
            <div className="text-[10px]">{error}</div>
          </div>
        </div>
      ) : null}
      <div className="pointer-events-none absolute bottom-2 left-2 z-[500] rounded bg-background/70 px-2 py-1 text-[10px] text-muted-foreground backdrop-blur-sm">
        © Mappls
      </div>
    </div>
  )
}

export { getMapplsAccessToken, isMapplsConfigured }
