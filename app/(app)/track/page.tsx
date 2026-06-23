'use client'

import { useEffect, useState } from 'react'
import { MapPanel } from '@/components/map/map-panel'
import { Switch } from '@/components/ui/switch'
import { api, getBaseUrl } from '@/lib/api'
import { toast } from 'sonner'
import type { EmergencyRoute } from '@/lib/types'
import { MAP_DEFAULT_CENTER } from '@/lib/constants'

export default function TrackPage() {
  const [event, setEvent] = useState<any | null>(null)
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null)
  const [altRoute, setAltRoute] = useState<EmergencyRoute | null>(null)
  const [routeLoading, setRouteLoading] = useState(false)
  const [analysis, setAnalysis] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [liveUpdatesEnabled, setLiveUpdatesEnabled] = useState(true)

  useEffect(() => {
    let active = true
    async function load() {
      try {
        setLoading(true)
        let selected: any = null
        try {
          const stored = typeof window !== 'undefined' ? sessionStorage.getItem('selectedNews') : null
          if (stored) selected = JSON.parse(stored)
        } catch {
          selected = null
        }

        setEvent(selected)
        setSelectedEvent(selected)

        if (selected) {
          const input = {
            eventName: selected?.title || selected?.news?.title || selected?.id || 'news',
            eventType: selected?.inferred?.event_type || 'news',
            zone: selected?.news?.location || 'Bangalore',
            corridor: '',
            attendance: Number(selected?.attendance) || 0,
            weather: 'clear',
            priority: (selected?.priority as any) || 'medium',
            date: new Date().toISOString().split('T')[0],
            time: new Date().toISOString().split('T')[1].split('.')[0],
          }
          try {
            const a = await api.analyzeEvent(input)
            if (!active) return
            setAnalysis(a)
          } catch {
            // ignore
          }
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => {
      active = false
    }
  }, [])

  // Live updates: try WebSocket first, fallback to polling
  useEffect(() => {
    if (!liveUpdatesEnabled) return

    let active = true
    let ws: WebSocket | null = null
    let pollId: number | null = null

    function handleUpdate(data: any) {
      if (!active) return
      // If the server sends full event object or updates, merge into state
      try {
        const updated = data?.event || data
        if (updated && event && (updated.id === event.id || !event.id)) {
          setEvent((prev: any) => ({ ...(prev || {}), ...updated }))
          setSelectedEvent((prev: any) => (prev && updated.id === prev.id ? { ...(prev || {}), ...updated } : prev))
        }
        if (data?.analysis) setAnalysis(data.analysis)
      } catch {
        // ignore
      }
    }

    // Attempt WebSocket connection if base URL configured
    try {
      const base = getBaseUrl()
      if (base) {
        try {
          const u = new URL(base)
          const protocol = u.protocol === 'https:' ? 'wss:' : 'ws:'
          const host = u.host
          const wsUrl = `${protocol}//${host}/ws/track`
          ws = new WebSocket(wsUrl)
          ws.onopen = () => {
            // subscribe to specific event if available
            if (event?.id) ws?.send(JSON.stringify({ type: 'subscribe', id: event.id }))
          }
          ws.onmessage = (m) => {
            try {
              const data = JSON.parse(m.data)
              handleUpdate(data)
            } catch {
              /* ignore parse errors */
            }
          }
          ws.onclose = () => {
            ws = null
          }
          ws.onerror = () => {
            try {
              ws?.close()
            } catch {}
            ws = null
          }
        } catch {
          ws = null
        }
      }
    } catch {
      ws = null
    }

    // Polling fallback (only if WS not available)
    const startPolling = () => {
      pollId = window.setInterval(async () => {
        try {
          // eventReplay may return an array of updates
          const updates = await api.eventReplay()
          if (!active) return
          if (Array.isArray(updates)) {
            updates.forEach((u) => handleUpdate(u))
          } else {
            handleUpdate(updates)
          }
        } catch {
          // ignore polling errors
        }
      }, 5000)
    }

    // If ws is not established after short timeout, start polling
    const wsWait = setTimeout(() => {
      if (!ws) startPolling()
    }, 800)

    return () => {
      active = false
      try {
        if (ws) ws.close()
      } catch {}
      if (pollId) clearInterval(pollId)
      clearTimeout(wsWait)
    }
  }, [event?.id, liveUpdatesEnabled])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">Track — Live Monitor</h1>
        <div className="flex items-center gap-2 rounded-lg bg-card/40 px-3 py-1.5 border border-border/50">
          <span className="text-xs text-muted-foreground font-medium">Live Updates</span>
          <Switch
            checked={liveUpdatesEnabled}
            onCheckedChange={setLiveUpdatesEnabled}
          />
        </div>
      </div>

      {loading && <div className="text-sm text-muted-foreground">Loading tracking data…</div>}

      {!event && !loading && <div className="text-sm text-muted-foreground">No event selected for tracking.</div>}

      {event && (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="md:col-span-2">
            <div className="glass rounded-xl p-4">
              <h2 className="font-semibold">Event</h2>
              <div className="mt-2 text-sm">
                <div className="font-semibold">{event.title || event.news?.title || event.name}</div>
                <div className="text-xs text-muted-foreground">Source: {event.source || event.news?.source || 'Unknown'}</div>
                <div className="mt-2 text-sm">Estimated people: <strong>{event.attendance ?? event.predictions?.attendance ?? '—'}</strong></div>
              </div>

              <div className="mt-4">
                <h3 className="font-semibold">Model Predictions</h3>
                {analysis ? (
                  <div className="mt-2 text-sm space-y-4">
                    <div className="grid gap-2 sm:grid-cols-2">
                      <div><strong>Impact Score:</strong> {analysis.impactScore ?? '—'}</div>
                      <div><strong>Incident Volume:</strong> {analysis.incidentVolume ?? '—'}</div>
                      <div><strong>Hotspot Risk:</strong> {analysis.hotspotRisk ?? '—'}%</div>
                      <div><strong>Road Closure Probability:</strong> {analysis.roadClosureProbability ?? '—'}%</div>
                      <div><strong>Officers Required:</strong> {analysis.officersRequired ?? '—'}</div>
                      <div><strong>Barricades Required:</strong> {analysis.barricadesRequired ?? '—'}</div>
                      <div><strong>Parking Overflow Risk:</strong> {analysis.parkingOverflowRisk ?? '—'}%</div>
                      <div><strong>Cascade Risk:</strong> {analysis.cascadeRisk ?? '—'}%</div>
                      <div className="sm:col-span-2"><strong>Incident Duration:</strong> {analysis.incidentDurationMin != null ? `${analysis.incidentDurationMin} minutes` : '—'}</div>
                    </div>

                    {analysis.confidence && Object.keys(analysis.confidence).length > 0 && (
                      <div>
                        <div className="font-semibold">Confidence</div>
                        <div className="grid gap-2 sm:grid-cols-2 mt-2">
                          {Object.entries(analysis.confidence).map(([key, value]) => (
                            <div key={key}>
                              <strong>{key.charAt(0).toUpperCase() + key.slice(1)}:</strong>{' '}
                              {value != null ? `${value}%` : '—'}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {analysis.recommendations && analysis.recommendations.length > 0 && (
                      <div>
                        <div className="font-semibold">Recommendations</div>
                        <ul className="mt-2 list-disc list-inside text-muted-foreground">
                          {analysis.recommendations.map((rec: any, idx: number) => (
                            <li key={idx}>{typeof rec === 'string' ? rec : rec.title || rec.detail || JSON.stringify(rec)}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {analysis.modelOutputs && (
                      <div>
                        <div className="font-semibold">Model Outputs</div>
                        <pre className="mt-2 overflow-x-auto rounded-md bg-slate-950/5 p-3 text-xs text-muted-foreground">
                          {JSON.stringify(analysis.modelOutputs, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="mt-2 text-sm text-muted-foreground">No model predictions available.</div>
                )}
              </div>
            </div>
          </div>

          <div>
            <div className="glass rounded-xl p-4 h-full">
              <h3 className="font-semibold">Map</h3>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h4 className="text-sm font-medium">Traffic Map</h4>
                <button
                  type="button"
                  disabled={!event || routeLoading}
                  onClick={async () => {
                    if (!event) return
                    const source = event.news?.location || event.name || 'Bangalore'
                    const destination = event.traffic_plan?.divert_to || 'Victoria Hospital'
                    setRouteLoading(true)
                    try {
                      const res = await api.emergencyRoute(source, destination)
                      setAltRoute(res)
                      toast.success('Alternate route recomputed', { description: `ETA ${res.etaMinutes} min` })
                    } catch {
                      toast.error('Failed to recompute alternate route')
                    } finally {
                      setRouteLoading(false)
                    }
                  }}
                  className="rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:bg-slate-400"
                >
                  {routeLoading ? 'Recomputing…' : 'Recompute alternate path'}
                </button>
              </div>
              <div className="mt-3 h-[360px]">
                <MapPanel
                  center={event?.position || MAP_DEFAULT_CENTER}
                  events={event ? [{ ...event, id: event.id ?? 'selected', position: event.position ?? MAP_DEFAULT_CENTER }] : []}
                  selectedEvent={selectedEvent || event}
                  onEventSelect={setSelectedEvent}
                  route={altRoute}
                  loading={false}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
