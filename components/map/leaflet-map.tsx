'use client'

import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { useEffect, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import type { Corridor, EmergencyRoute, EventLocation, Hotspot } from '@/lib/types'
import { RISK_HEX, riskHexFromScore } from '@/lib/ui'
import { MAP_DEFAULT_ZOOM, MAP_FLY_TO_ZOOM } from '@/lib/constants'

export interface MapLayers {
  corridors: boolean
  hotspots: boolean
  events: boolean
  heatmap: boolean
  routes?: boolean
}

interface LeafletMapProps {
  center: [number, number]
  corridors?: Corridor[]
  hotspots?: Hotspot[]
  events?: EventLocation[]
  route?: EmergencyRoute | null
  layers: MapLayers
  zoom?: number
  selectedEvent?: EventLocation | null
  onEventSelect?: (event: EventLocation | null) => void
}

function getLocalityColor(name: string): string {
  const n = name.toLowerCase()
  if (n.includes('koramangala')) return '#8b5cf6' // Violet
  if (n.includes('indiranagar')) return '#06b6d4' // Cyan
  if (n.includes('mg road') || n.includes('cbd')) return '#ef4444' // Red
  if (n.includes('whitefield')) return '#f59e0b' // Amber
  if (n.includes('electronic city')) return '#10b981' // Emerald
  if (n.includes('yelahanka')) return '#d946ef' // Pink
  if (n.includes('hebbal')) return '#3b82f6' // Blue
  if (n.includes('jayanagar')) return '#f43f5e' // Rose
  if (n.includes('rajajinagar')) return '#84cc16' // Lime
  return '#3b82f6' // Fallback blue
}

export default function LeafletMap({
  center,
  corridors = [],
  hotspots = [],
  events = [],
  route = null,
  layers,
  zoom = MAP_DEFAULT_ZOOM,
  selectedEvent = null,
  onEventSelect,
}: LeafletMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const overlayRef = useRef<L.LayerGroup | null>(null)
  

  

  // init
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    
    let map: L.Map
    map = L.map(containerRef.current, {
      center,
      zoom,
      zoomControl: true,
      attributionControl: true,
    })
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap &copy; CARTO',
      maxZoom: 19,
    }).addTo(map)
    overlayRef.current = L.layerGroup().addTo(map)
    mapRef.current = map
    setTimeout(() => map.invalidateSize(), 200)

    return () => {
      map.remove()
      mapRef.current = null
      overlayRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Fly to selected event when it changes
  useEffect(() => {
    const map = mapRef.current
    if (!map || !selectedEvent) return

    // If there's a traffic plan with a valid path, fit the map to show the full route
    const plan = selectedEvent.traffic_plan
    if (plan?.path && Array.isArray(plan.path) && plan.path.length >= 2) {
      try {
        const allPoints = [
          ...(plan.path as [number, number][]),
          ...(Array.isArray(plan.diversion_path) ? (plan.diversion_path as [number, number][]) : [])
        ]
        const bounds = L.latLngBounds(allPoints)
        map.fitBounds(bounds.pad(0.25), { animate: true, duration: 1.5 })
        return
      } catch {
        // fall through to default fly-to
      }
    }

    // Fallback: fly to event position marker
    if (selectedEvent.position) {
      map.flyTo(selectedEvent.position, MAP_FLY_TO_ZOOM, { animate: true, duration: 1.5 })
    }
  }, [selectedEvent])

  // redraw overlays when data/layers change
  useEffect(() => {
    const map = mapRef.current
    const group = overlayRef.current
    if (!map || !group) return
    group.clearLayers()

    if (layers.corridors) {
      corridors.forEach((c) => {
        if (!c?.path || !Array.isArray(c.path) || c.path.length < 2) return
        try {
          L.polyline(c.path, {
            color: riskHexFromScore(c.congestion),
            weight: 6,
            opacity: 0.85,
            lineCap: 'round',
          })
            .bindTooltip(`${c.name} · ${c.congestion}% load`, { sticky: true })
            .addTo(group)
        } catch (err) {
          // ignore malformed corridor paths
        }
      })
    }

    if (layers.hotspots) {
      hotspots.forEach((h) => {
        if (!h?.position || !Array.isArray(h.position) || h.position.length < 2) return
        const color = RISK_HEX[h.level]
        try {
          L.circleMarker(h.position, {
            radius: 9,
            color,
            weight: 2,
            fillColor: color,
            fillOpacity: 0.35,
          })
            .bindTooltip(`${h.name} · risk ${h.risk}%`, { sticky: true })
            .addTo(group)
          L.circleMarker(h.position, { radius: 3, color, weight: 0, fillColor: color, fillOpacity: 1 }).addTo(group)
        } catch {
          // ignore malformed hotspot
        }
      })
    }

    if (layers.events) {
      events.forEach((e) => {
        if (!e?.position || !Array.isArray(e.position) || e.position.length < 2) return
        try {
          const score = (e.predictions?.impact?.impact_score as number) ?? e.impact_score ?? 0
          const color = riskHexFromScore(score)
          const isSelected = selectedEvent && selectedEvent.id === e.id
          
          // Draw marker with border indicating if selected
          const borderStyle = isSelected ? 'border: 3px solid #fff; box-shadow: 0 0 15px #fff;' : `box-shadow:0 0 0 6px ${color}33;`
          const iconHtml = `<div style="display:flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:8px;background:${color};${borderStyle}color:#fff;font-size:11px;font-weight:700;cursor:pointer">E</div>`
          const icon = L.divIcon({ className: '', html: iconHtml, iconSize: [30, 30], iconAnchor: [15, 15] })
          
          const marker = L.marker(e.position, { icon })
            .bindTooltip(`${e.name} · ${e.attendance?.toLocaleString?.() ?? e.attendance}`, { sticky: true })
            .addTo(group)

          marker.on('click', () => {
            if (onEventSelect) {
              onEventSelect(e)
            }
          })

          // popup with news + AI recommendations
          const news = e.news ?? e.predictions?.news ?? null
          const title = (news && (news.get ? news.get('title') : news.title)) || e.name
          const summary = (news && (news.get ? news.get('summary') : news.summary)) || ''
          const link = (news && (news.get ? news.get('link') : news.link)) || ''
          const sentiment = e.sentiment ?? 'neutral'
          const pre = Array.isArray(e.pre_measures) ? e.pre_measures : e.predictions?.pre_measures ?? []
          const impactText = `Impact: ${score}`
          const popupHtml = `<div style="max-width:240px"><strong>${title}</strong><div style="margin-top:6px;font-size:12px;color:#666">${summary}</div><div style="margin-top:8px;font-size:12px"><strong>Sentiment:</strong> ${sentiment}</div><div style="margin-top:6px;font-size:12px"><strong>${impactText}</strong></div>${pre.length?'<div style="margin-top:8px;font-size:12px"><strong>Pre-measures:</strong><ul>'+pre.map((p:any)=>`<li>${p}</li>`).join('')+'</ul></div>':''}${link?`<div style="margin-top:8px"><a href="${link}" target="_blank">Source</a></div>`:''}</div>`
          marker.bindPopup(popupHtml)
        } catch {
          // ignore malformed event
        }
      })
    }

    // Draw heatmap color-coded by Bangalore location
    if (layers.heatmap && events.length > 0) {
      events.forEach((e) => {
        if (!e?.position || !Array.isArray(e.position) || e.position.length < 2) return
        try {
          const locationName = e.name || e.news?.title || ''
          const color = getLocalityColor(locationName)
          const heatHtml = `<div class="heatmap-glow" style="width:120px;height:120px;border-radius:50%;background:radial-gradient(circle, ${color} 0%, transparent 70%);filter:blur(8px);pointer-events:none;opacity:0.35;"></div>`
          const heatIcon = L.divIcon({
            className: '',
            html: heatHtml,
            iconSize: [120, 120],
            iconAnchor: [60, 60],
          })
          L.marker(e.position, { icon: heatIcon, interactive: false }).addTo(group)
        } catch (err) {
          // ignore heatmap overlay draw errors
        }
      })
    }

    // Draw traffic plan for selected news event
    if (selectedEvent && selectedEvent.traffic_plan) {
      const plan = selectedEvent.traffic_plan
      
      // Draw affected route
      if (plan.path && Array.isArray(plan.path) && plan.path.length >= 2) {
        try {
          const routeSource = plan.source === 'mappls' ? ' · via Mappls' : ''
          L.polyline(plan.path, {
            color: '#ef4444',
            weight: 6,
            dashArray: '5, 8',
            opacity: 0.95,
            lineCap: 'round',
          })
            .bindTooltip(`🚧 Affected: ${plan.affected || 'Congested Area'}${routeSource}`, { sticky: true })
            .addTo(group)

          // Block marker
          const blockHtml = `<div style="display:flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:#ef4444;border:2px solid #fff;color:#fff;font-size:12px;font-weight:700;box-shadow:0 0 10px #ef4444">!</div>`
          const blockIcon = L.divIcon({ className: '', html: blockHtml, iconSize: [24, 24], iconAnchor: [12, 12] })
          L.marker(plan.path[0], { icon: blockIcon }).addTo(group)
        } catch (err) {
          // ignore path error
        }
      }

      // Draw diversion route
      if (plan.diversion_path && Array.isArray(plan.diversion_path) && plan.diversion_path.length >= 2) {
        try {
          const routeSource = plan.source === 'mappls' ? ' · via Mappls' : ''
          L.polyline(plan.diversion_path, {
            color: '#10b981',
            weight: 6,
            opacity: 0.95,
            lineCap: 'round',
            lineJoin: 'round',
            className: 'route-flow-animation',
          })
            .bindTooltip(`✅ Divert to: ${plan.divert_to || 'Detour Path'}${routeSource}`, { sticky: true })
            .addTo(group)

          // Detour/Arrow marker
          const detourHtml = `<div style="display:flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:#10b981;border:2px solid #fff;color:#fff;font-size:12px;font-weight:700;box-shadow:0 0 10px #10b981">→</div>`
          const detourIcon = L.divIcon({ className: '', html: detourHtml, iconSize: [24, 24], iconAnchor: [12, 12] })
          L.marker(plan.diversion_path[0], { icon: detourIcon }).addTo(group)
        } catch (err) {
          // ignore detour error
        }
      }
    }

    if ((layers.routes ?? true) && route && route.path.length >= 2) {
      const line = L.polyline(route.path, {
        color: '#22d3ee',
        weight: 6,
        opacity: 0.95,
        dashArray: '8,8',
        lineCap: 'round',
        lineJoin: 'round',
      })
        .bindTooltip('Primary Route', { sticky: true })
        .addTo(group)

      const altPath = (route as any)?.alternativePath
      if (altPath && Array.isArray(altPath) && altPath.length >= 2) {
        try {
          L.polyline(altPath, {
            color: '#a855f7',
            weight: 5,
            opacity: 0.75,
            dashArray: '4,8',
            lineCap: 'round',
            lineJoin: 'round',
          })
            .bindTooltip('Alternative Route (Detour)', { sticky: true })
            .addTo(group)
        } catch {
          // ignore malformed alt path
        }
      }

      const startMarker = L.circleMarker(route.path[0], {
        radius: 8,
        color: '#0ea5e9',
        weight: 3,
        fillColor: '#ffffff',
        fillOpacity: 1,
      })
        .bindTooltip(`Start: ${route.source}`, { sticky: true })
        .addTo(group)

      const endMarker = L.circleMarker(route.path[route.path.length - 1], {
        radius: 8,
        color: '#14b8a6',
        weight: 3,
        fillColor: '#ffffff',
        fillOpacity: 1,
      })
        .bindTooltip(`End: ${route.destination}`, { sticky: true })
        .addTo(group)

      ;(route.signals ?? []).forEach((s) => {
        if (!s?.position || !Array.isArray(s.position) || s.position.length < 2) return
        try {
          L.circleMarker(s.position, {
            radius: 6,
            color: '#10b981',
            weight: 2,
            fillColor: '#10b981',
            fillOpacity: 0.9,
          })
            .bindTooltip(`${s.name} · ${s.action}`, { sticky: true })
            .addTo(group)
        } catch {
          // ignore malformed signal
        }
      })
      ;(route.bottlenecks ?? []).forEach((b) => {
        if (!b?.position || !Array.isArray(b.position) || b.position.length < 2) return
        try {
          L.circleMarker(b.position, {
            radius: 7,
            color: '#ef4444',
            weight: 2,
            fillColor: '#ef4444',
            fillOpacity: 0.6,
          })
            .bindTooltip(`Bottleneck · ${b.name}`, { sticky: true })
            .addTo(group)
        } catch {
          // ignore malformed bottleneck
        }
      })
      try {
        map.fitBounds(line.getBounds().pad(0.25))
      } catch {
        /* noop */
      }
    }
  }, [corridors, hotspots, events, route, layers, selectedEvent])

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" aria-label="Traffic intelligence map" />
      
    </div>
  )
}
