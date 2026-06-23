'use client'

import { Layers, Loader2, Maximize2, Navigation, Radio, Route, Zap, Sparkles, X, ExternalLink, Shuffle, AlertCircle } from 'lucide-react'
import dynamic from 'next/dynamic'
import { useState } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'
import type { Corridor, EmergencyRoute, EventLocation, Hotspot } from '@/lib/types'
import { isMapplsConfigured } from '@/lib/mappls-loader'
import { cn } from '@/lib/utils'
import type { MapLayers } from './mappls-map'

const MapplsMap = dynamic(() => import('./mappls-map'), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-card">
      <div className="flex flex-col items-center gap-2 text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <span className="text-xs">Loading Mappls traffic grid…</span>
      </div>
    </div>
  ),
})

const LeafletMap = dynamic(() => import('./leaflet-map'), {
  ssr: false,
})
interface MapPanelProps {
  center: [number, number]
  corridors?: Corridor[]
  hotspots?: Hotspot[]
  events?: EventLocation[]
  route?: EmergencyRoute | null
  loading?: boolean
  height?: string
  title?: string
  defaultLayers?: Partial<MapLayers>
  zoom?: number
  selectedEvent?: EventLocation | null
  onEventSelect?: (event: EventLocation | null) => void
}

const LAYER_META = [
  { key: 'corridors', label: 'Corridors', icon: Route },
  { key: 'hotspots', label: 'Hotspots', icon: Zap },
  { key: 'events', label: 'Events', icon: Navigation },
  { key: 'heatmap', label: 'Event Heatmap', icon: Sparkles },
] as const

const LEGEND = [
  { label: 'Severe', color: '#ef4444' },
  { label: 'High', color: '#f59e0b' },
  { label: 'Moderate', color: '#3b82f6' },
  { label: 'Low', color: '#10b981' },
]

export function MapPanel({
  center,
  corridors,
  hotspots,
  events,
  route,
  loading,
  height = 'h-[520px]',
  title = 'Live Traffic Intelligence Map',
  defaultLayers,
  zoom,
  selectedEvent = null,
  onEventSelect,
}: MapPanelProps) {
  const [layers, setLayers] = useState<MapLayers>({
    corridors: true,
    hotspots: true,
    events: true,
    heatmap: true,
    ...defaultLayers,
  })
  const [showControls, setShowControls] = useState(true)
  const [showLeafletFallback, setShowLeafletFallback] = useState(false)

  return (
    <div className={cn('glass relative overflow-hidden rounded-xl', height)}>
      {/* header */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-[500] flex items-start justify-between p-4">
        <div className="pointer-events-auto flex items-center gap-2 rounded-lg bg-background/70 px-3 py-2 backdrop-blur-md">
          <span className="flex h-2 w-2">
            <span className="absolute inline-flex h-2 w-2 animate-ping rounded-full bg-success opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
          </span>
          <span className="text-sm font-medium">{title}</span>
        </div>
        <button
          type="button"
          onClick={() => setShowControls((s) => !s)}
          className="pointer-events-auto flex items-center gap-1.5 rounded-lg bg-background/70 px-2.5 py-2 text-xs font-medium backdrop-blur-md transition-colors hover:bg-background/90"
        >
          <Layers className="h-3.5 w-3.5" />
          Layers
        </button>
      </div>

      {/* layer controls */}
      {showControls ? (
        <div className="absolute right-4 top-16 z-[500] w-52 rounded-lg border border-border bg-background/85 p-3 backdrop-blur-md">
          <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            <Maximize2 className="h-3 w-3" /> Layer Controls
          </p>
          <div className="space-y-2.5">
            {LAYER_META.map(({ key, label, icon: Icon }) => (
              <label key={key} className="flex cursor-pointer items-center justify-between gap-2 text-sm">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </span>
                <Switch
                  checked={layers[key]}
                  onCheckedChange={(v) => setLayers((prev) => ({ ...prev, [key]: v }))}
                />
              </label>
            ))}
          </div>
          <div className="mt-3 border-t border-border pt-2.5">
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Congestion
            </p>
            <div className="grid grid-cols-2 gap-1.5">
              {LEGEND.map((l) => (
                <span key={l.label} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                  <span className="h-2 w-2 rounded-full" style={{ background: l.color }} />
                  {l.label}
                </span>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      {/* floating details card for selected event */}
      {selectedEvent && (
        <div className="absolute left-4 top-16 z-[500] w-80 rounded-xl border border-border bg-background/90 p-4 backdrop-blur-md shadow-2xl transition-all animate-in slide-in-from-left duration-300 max-h-[calc(100%-80px)] overflow-y-auto pointer-events-auto">
          <div className="flex items-start justify-between gap-2 border-b border-border/50 pb-2">
            <div>
              <span className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider text-primary font-semibold">
                <Sparkles className="h-3 w-3" /> Live Event Brief
              </span>
              <h3 className="text-sm font-bold text-foreground leading-snug mt-0.5">{selectedEvent.name}</h3>
            </div>
            <button
              onClick={() => onEventSelect && onEventSelect(null)}
              className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors shrink-0"
              aria-label="Close details"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          
          <div className="mt-3 space-y-3">
            {/* Sentiment Info */}
            <div className="flex items-center justify-between text-xs border-b border-border/20 pb-2">
              <span className="text-muted-foreground">Incident Sentiment:</span>
              {getSentimentBadge(selectedEvent.sentiment || 'neutral')}
            </div>

            {/* News Source details */}
            {selectedEvent.news && (
              <div className="rounded-lg bg-card/60 p-2.5 text-xs border border-border/50">
                <p className="font-semibold text-muted-foreground uppercase text-[9px] tracking-wider">News Source & Context</p>
                {selectedEvent.news.source && (
                  <p className="mt-1 text-primary font-semibold">{selectedEvent.news.source}</p>
                )}
                {selectedEvent.news.summary && (
                  <p className="mt-1 text-muted-foreground leading-relaxed line-clamp-3 font-normal">{selectedEvent.news.summary}</p>
                )}
                {selectedEvent.news.link && (
                  <a
                    href={selectedEvent.news.link}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-flex items-center gap-1 text-primary hover:underline font-semibold"
                  >
                    <ExternalLink className="h-3 w-3" /> Read Article Source
                  </a>
                )}
              </div>
            )}

            {/* Traffic Diversion Info */}
            {selectedEvent.traffic_plan && (
              <div className="rounded-lg bg-success/5 p-2.5 text-xs border border-success/20">
                <p className="font-semibold text-success uppercase text-[9px] tracking-wider flex items-center gap-1">
                  <Shuffle className="h-3 w-3 text-success animate-pulse" /> Traffic Diversion Plan
                  {selectedEvent.traffic_plan.source?.startsWith('mappls') && (
                    <span className="ml-auto inline-flex items-center gap-0.5 rounded bg-blue-500/15 border border-blue-500/30 px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wider text-blue-400">
                      🗺️ Mappls Route
                    </span>
                  )}
                </p>
                <div className="mt-2 space-y-1.5">
                  <p className="text-muted-foreground">
                    Affected: <strong className="text-foreground">{selectedEvent.traffic_plan.affected || 'Road segment'}</strong>
                  </p>
                  <p className="text-muted-foreground">
                    Change Traffic to: <strong className="text-success font-semibold">{selectedEvent.traffic_plan.divert_to || 'Detour routes'}</strong>
                  </p>
                </div>
                <p className="mt-2 text-[10px] text-muted-foreground italic leading-normal">
                  {selectedEvent.traffic_plan.source?.startsWith('mappls')
                    ? '* Road-accurate route fetched from Mappls (MapmyIndia) Route API.'
                    : '* Approximate offset route (Mappls API unavailable).'}
                </p>
              </div>
            )}

            {/* Pre-measures Info */}
            {selectedEvent.pre_measures && selectedEvent.pre_measures.length > 0 && (
              <div className="space-y-1.5 border-t border-border/20 pt-2.5">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">AI Insight Pre-measures</p>
                <ul className="space-y-1 text-xs">
                  {selectedEvent.pre_measures.map((p: string, idx: number) => (
                    <li key={idx} className="flex items-start gap-2 text-muted-foreground">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                      <span className="leading-tight">{p}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {loading ? (
        <Skeleton className="h-full w-full" />
      ) : (
        <>
          {/* Mappls API Error Warning */}
          {showLeafletFallback ? (
            <div className="pointer-events-none absolute inset-x-0 bottom-4 z-[600] flex justify-center px-4">
              <Alert className="pointer-events-auto w-full max-w-md border-warning/50 bg-warning/10 text-warning shadow-lg">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="text-xs">
                  <strong>Mappls SDK unavailable.</strong> Showing Leaflet fallback map. Ensure MAPPLS_CLIENT_ID/MAPPLS_CLIENT_SECRET are valid and the backend is running.
                </AlertDescription>
              </Alert>
            </div>
          ) : null}
          {isMapplsConfigured() && !showLeafletFallback ? (
            <MapplsMap
              center={center}
              corridors={corridors}
              hotspots={hotspots}
              events={events}
              route={route}
              layers={layers}
              zoom={zoom}
              selectedEvent={selectedEvent}
              onEventSelect={onEventSelect}
              onMapplsError={setShowLeafletFallback}
            />
          ) : (
            <LeafletMap
              key="leaflet-fallback"
              center={center}
              corridors={corridors}
              hotspots={hotspots}
              events={events}
              route={route}
              layers={layers}
              zoom={zoom}
              selectedEvent={selectedEvent}
              onEventSelect={onEventSelect}
            />
          )}
        </>
      )}
    </div>
  )
}

function getSentimentBadge(sentiment: string) {
  switch (sentiment) {
    case 'positive':
      return (
        <span className="inline-flex items-center gap-1 rounded bg-success/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-success border border-success/30">
          Positive
        </span>
      )
    case 'negative':
      return (
        <span className="inline-flex items-center gap-1 rounded bg-destructive/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-destructive border border-destructive/30 animate-pulse">
          Negative
        </span>
      )
    default:
      return (
        <span className="inline-flex items-center gap-1 rounded bg-muted-foreground/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground border border-border">
          Neutral
        </span>
      )
  }
}
