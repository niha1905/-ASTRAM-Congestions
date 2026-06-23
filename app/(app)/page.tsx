'use client'

import { Radar, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
// replaced static charts with live news feed when backend unavailable
import { AiInsights } from '@/components/dashboard/ai-insights'
import { KpiGrid } from '@/components/dashboard/kpi-grid'
import { MapPanel } from '@/components/map/map-panel'
import { PageHeader } from '@/components/shared/page-header'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'
import type { Corridor, EventLocation, Hotspot, KpiMetric, Recommendation, SeriesPoint } from '@/lib/types'
import { cn, stripHtml, extractFirstLink } from '@/lib/utils'
import { MAP_DEFAULT_CENTER, SKELETON_LOADING_COUNT, NEWS_DEFAULT_LIMIT } from '@/lib/constants'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  // DialogTrigger,
} from '@/components/ui/dialog'
import NewsDialog from '@/components/news/news-dialog'
import { EventForm } from '@/components/event-analysis/event-form'
import { Plus } from 'lucide-react'

interface DashboardData {
  kpis: KpiMetric[]
  recommendations: Recommendation[]
  series: {
    incidentForecast: SeriesPoint[]
    congestionTrend: SeriesPoint[]
    impactTrend: SeriesPoint[]
    parkingProbability: SeriesPoint[]
  }
  map: { center: [number, number]; corridors: Corridor[]; hotspots: Hotspot[]; events: EventLocation[] }
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedEvent, setSelectedEvent] = useState<EventLocation | null>(null)

  const [analysisOpen, setAnalysisOpen] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<any | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [newsOpen, setNewsOpen] = useState(false)
  const [todayOnly, setTodayOnly] = useState(false)

  const handleAnalyze = async (input: any) => {
    try {
      setAnalysisLoading(true)
      const res = await api.analyzeEvent(input)
      setAnalysisResult(res)
    } catch (e: any) {
      console.error(e)
    } finally {
      setAnalysisLoading(false)
    }
  }

  const runAnalysisForEvent = async (ev: EventLocation) => {
    // prepare EventInput from the news/event object
    const published = ev.news?.published || (ev as any).published || ev.news?.linkPublished || new Date().toISOString()
    const dateObj = new Date(published)
    const input = {
      eventName: ev.name || ev.news?.title || 'news',
      eventType: ev.type || ev.inferred?.event_type || ev.news?.event_type || 'news',
      zone: ev.news?.location || ev.name || 'Bangalore',
      corridor: '',
      attendance: ev.attendance || ev.predictions?.attendance || 0,
      weather: '',
      priority: (ev.priority as any) || 'medium',
      date: isNaN(dateObj.getTime()) ? new Date().toISOString().split('T')[0] : dateObj.toISOString().split('T')[0],
      time: isNaN(dateObj.getTime()) ? '12:00' : dateObj.toISOString().split('T')[1].slice(0,5),
    }

    setAnalysisOpen(true)
    setAnalysisResult(null)
    await handleAnalyze(input)
  }

  useEffect(() => {
    let active = true
    api.dashboard()
      .then(async (d) => {
        if (!active) return
        const dash = d as DashboardData
        // fetch live news and merge as map events when available
        try {
          const newsItems: any[] = await api.fetchNews()
          const normalizeTitle = (value: string) => value.trim().toLowerCase()
          const newsByTitle = new Map(
            (newsItems || []).map((n) => [
              normalizeTitle(n.news?.title || n.title || ''),
              n,
            ]),
          )

          dash.map = dash.map || { center: MAP_DEFAULT_CENTER, corridors: [], hotspots: [], events: [] }
          dash.map.events = (dash.map.events || []).map((event) => {
            const match = newsByTitle.get(normalizeTitle(event.name || ''))
            if (!match) return event
            return {
              ...event,
              sentiment: match.sentiment ?? event.sentiment,
              pre_measures: match.pre_measures ?? event.pre_measures,
              predictions: match.predictions ?? event.predictions,
              news: match.news ?? event.news,
              traffic_plan: match.traffic_plan ?? event.traffic_plan,
              position: match.position
                ? ([match.position.lat, match.position.lon] as [number, number])
                : event.position,
            }
          })
        } catch (e) {
          // ignore news fetch errors
        }

        if (!active) return
        setData(dash)
      })
      .catch((err) => {
        if (!active) return
        console.error('Dashboard load failed:', err)
        setError(err?.message ?? 'Unable to load dashboard data.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  return (
    <div className="space-y-5">
      <PageHeader
        title="Operations Dashboard"
        description="Real-time congestion intelligence across the Bangalore corridor network — predictions, hotspots, and AI-driven operational actions."
        icon={<Radar className="h-5 w-5" />}
        actions={
            <div className="flex items-center gap-3">
              <Button size="sm" className="gap-1.5 bg-secondary/10 hover:bg-secondary/12 text-primary font-semibold" onClick={() => setNewsOpen(true)}>
                View News
              </Button>
              <Button size="sm" className="gap-1.5 bg-primary hover:bg-primary/95 text-primary-foreground font-semibold" onClick={() => setAnalysisOpen(true)}>
                <Plus className="h-4 w-4" /> Analyze Event
              </Button>
              <Dialog open={analysisOpen} onOpenChange={(open) => {
                setAnalysisOpen(open)
                if (!open) setAnalysisResult(null)
              }}>
              <DialogContent className="sm:max-w-md md:max-w-2xl max-h-[85vh] overflow-y-auto bg-card border border-border/80 text-foreground">
                <DialogHeader>
                  <DialogTitle className="text-foreground">Quick Event Analyzer</DialogTitle>
                  <DialogDescription className="text-muted-foreground">
                    Run LightGBM / RandomForest models on custom event parameters to determine traffic impact.
                  </DialogDescription>
                </DialogHeader>

                {!analysisResult ? (
                  <EventForm onAnalyze={handleAnalyze} loading={analysisLoading} />
                ) : (
                  <div className="space-y-4 pt-2">
                    <div className="glass rounded-xl p-4 space-y-3">
                      <h3 className="font-semibold text-sm text-foreground">Predicted ML Metrics</h3>
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                        <div className="rounded-lg border border-border/60 bg-card/40 p-3">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Incident Volume</span>
                          <div className="text-xl font-bold text-primary mt-1">{analysisResult.incidentVolume}</div>
                          <div className="text-[9px] text-muted-foreground">LightGBM Forecast</div>
                        </div>
                        <div className="rounded-lg border border-border/60 bg-card/40 p-3">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Hotspot Risk</span>
                          <div className="text-xl font-bold text-warning mt-1">{analysisResult.hotspotRisk}%</div>
                          <div className="text-[9px] text-muted-foreground">LightGBM Risk Index</div>
                        </div>
                        <div className="rounded-lg border border-border/60 bg-card/40 p-3">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Closure Probability</span>
                          <div className="text-xl font-bold text-destructive mt-1">{analysisResult.roadClosureProbability}%</div>
                          <div className="text-[9px] text-muted-foreground">RandomForest Class</div>
                        </div>
                        <div className="rounded-lg border border-border/60 bg-card/40 p-3">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Officers Required</span>
                          <div className="text-xl font-bold text-success mt-1">{analysisResult.officersRequired}</div>
                          <div className="text-[9px] text-muted-foreground">GradientBoosting Est</div>
                        </div>
                        <div className="rounded-lg border border-border/60 bg-card/40 p-3">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Barricades Required</span>
                          <div className="text-xl font-bold text-foreground mt-1">{analysisResult.barricadesRequired}</div>
                          <div className="text-[9px] text-muted-foreground">GradientBoosting Est</div>
                        </div>
                        <div className="rounded-lg border border-border/60 bg-card/40 p-3">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Parking Overflow</span>
                          <div className="text-xl font-bold text-cyan-400 mt-1">{analysisResult.parkingOverflowRisk}%</div>
                          <div className="text-[9px] text-muted-foreground">LightGBM Risk</div>
                        </div>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2 mt-3 pt-3 border-t border-border/40">
                        <div>
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Estimated Duration</span>
                          <div className="text-sm font-semibold mt-0.5 text-foreground">{analysisResult.incidentDurationMin} minutes</div>
                        </div>
                        <div>
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Cascade Risk (T+60)</span>
                          <div className="text-sm font-semibold mt-0.5 text-foreground">{analysisResult.cascadeRisk}%</div>
                        </div>
                      </div>
                    </div>

                    {analysisResult.recommendations && analysisResult.recommendations.length > 0 && (
                      <div className="glass rounded-xl p-4">
                        <h4 className="font-semibold text-xs text-muted-foreground uppercase tracking-wider mb-2">AI-Driven Recommendations</h4>
                        <div className="space-y-2">
                          {analysisResult.recommendations.map((rec: any, idx: number) => (
                            <div key={idx} className="rounded-lg border border-border/40 bg-card/25 p-2.5 text-xs">
                              <div className="flex justify-between items-center gap-2">
                                <span className="font-semibold text-foreground">{rec.title}</span>
                                <span className="text-[10px] text-muted-foreground uppercase">{rec.category}</span>
                              </div>
                              <p className="mt-1 text-[11px] text-muted-foreground leading-relaxed">{rec.detail}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="flex gap-2 pt-2">
                      <Button variant="outline" className="flex-1" onClick={() => setAnalysisResult(null)}>
                        Analyze Another
                      </Button>
                      <Button className="flex-1" onClick={() => setAnalysisOpen(false)}>
                        Close
                      </Button>
                    </div>
                  </div>
                )}
              </DialogContent>
            </Dialog>
              <NewsDialog open={newsOpen} onOpenChange={(v) => setNewsOpen(v)} />
            <Badge variant="outline" className="gap-1.5 border-success/30 bg-success/10 text-success">
              <span className="h-2 w-2 rounded-full bg-success" />
              Operational
            </Badge>
          </div>
        }
      />

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <strong>Dashboard fetch failed:</strong> {error}
        </div>
      ) : null}

      <KpiGrid kpis={data?.kpis ?? []} loading={loading} />

      <div className="grid gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <MapPanel
            center={data?.map.center ?? MAP_DEFAULT_CENTER}
            corridors={data?.map.corridors}
            hotspots={data?.map.hotspots}
            events={data?.map.events}
            loading={loading}
            selectedEvent={selectedEvent}
            onEventSelect={setSelectedEvent}
          />
        </div>
        <div className="min-h-[520px] xl:col-span-1">
          <AiInsights recommendations={data?.recommendations ?? []} loading={loading} />
        </div>
      </div>

      <div>
        <div className="mb-3 flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold">Live News — Event Alerts</h2>
          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              onClick={() => setTodayOnly((s) => !s)}
              className={cn(
                'text-xs px-2 py-1 rounded-md border transition',
                todayOnly ? 'bg-primary text-primary-foreground border-primary' : 'bg-card/5 text-muted-foreground border-border/30'
              )}
            >
              {todayOnly ? 'Today' : 'This Week'}
            </button>
          </div>
        </div>
        <LiveNewsFeed
          loading={loading}
          events={data?.map.events ?? []}
          selectedEvent={selectedEvent}
          onEventSelect={setSelectedEvent}
          todayOnly={todayOnly}
          onRunAnalysis={runAnalysisForEvent}
        />
      </div>
    </div>
  )
}


function LiveNewsFeed({
  loading,
  events = [],
  selectedEvent,
  onEventSelect,
  todayOnly,
  onRunAnalysis,
}: {
  loading: boolean
  events: EventLocation[]
  selectedEvent: EventLocation | null
  onEventSelect: (event: EventLocation | null) => void
  todayOnly?: boolean
  onRunAnalysis?: (ev: EventLocation) => void
}) {
  const router = useRouter()
  const newsEvents = events.filter((e) => e.news || (e.id && String(e.id).startsWith('news')))
  const filteredNews = (newsEvents || []).filter((e) => {
    if (!todayOnly) return true
    const published = e.news?.published || (e as any).published || e.news?.linkPublished
    if (!published) return false
    const d = Date.parse(published)
    if (isNaN(d)) return false
    return d >= (Date.now() - 24 * 60 * 60 * 1000)
  })

  if (loading) {
    return (
      <div className="grid gap-3 md:grid-cols-2">
        {Array.from({ length: SKELETON_LOADING_COUNT }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-muted animate-pulse" />
        ))}
      </div>
    )
  }

  if (filteredNews.length === 0) {
    return (
      <div className="rounded-lg border border-muted/30 bg-muted/5 p-4 text-sm text-muted-foreground">
        No recent event alerts found.
      </div>
    )
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {filteredNews.map((e) => {
        const isSelected = selectedEvent?.id === e.id
        const sentiment = e.sentiment || 'neutral'
        return (
          <div
            key={e.id}
            onClick={() => {
              onEventSelect(e)
              // trigger analysis for this news item when handler provided
              try {
                onRunAnalysis && onRunAnalysis(e)
              } catch (err) {
                console.error('analysis run failed:', err)
              }
              // keep selection client-side; no navigation now that standalone pages are removed
              window.scrollTo({ top: 0, behavior: 'smooth' })
            }}
            className={cn(
              "glass rounded-xl p-4 text-sm cursor-pointer hover:shadow-lg transition-all duration-200 border",
              isSelected
                ? "border-primary bg-primary/10 shadow-md scale-[1.01]"
                : "border-border/30 hover:border-primary/50"
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-primary">{e.news?.source || 'Alert'}</span>
                  <span
                    className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded-full font-semibold uppercase tracking-wider",
                      sentiment === 'positive'
                        ? "bg-success/20 text-success"
                        : sentiment === 'negative'
                        ? "bg-destructive/20 text-destructive animate-pulse"
                        : "bg-muted text-muted-foreground"
                    )}
                  >
                    {sentiment}
                  </span>
                </div>
                <div className="text-sm font-semibold text-foreground mt-1.5 leading-snug line-clamp-2">
                  {e.news?.title || e.name}
                </div>
                {e.news?.summary && (
                  <div className="mt-1 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                    {stripHtml(e.news.summary)}
                  </div>
                )}
                {(
                  (e.news && (e.news.link || extractFirstLink(e.news.summary))) || e.link
                ) && (
                  <div className="mt-2 text-xs">
                    <a href={e.news?.link || extractFirstLink(e.news?.summary) || e.link} target="_blank" rel="noreferrer" className="text-primary underline">Open source</a>
                  </div>
                )}
                {e.traffic_plan && (
                  <div className="mt-2.5 text-[11px] text-success/90 font-semibold flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-success" />
                    Bypass: {e.traffic_plan.divert_to}
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
