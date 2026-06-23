'use client'

import { Activity, GitBranch, History, FlaskConical, Ambulance, FileText } from 'lucide-react'
import { useEffect, useState } from 'react'
import { PageHeader } from '@/components/shared/page-header'
import { EventForm } from '@/components/event-analysis/event-form'
import { RecommendationTimeline } from '@/components/shared/recommendation-timeline'
import { ResultStat } from '@/components/shared/result-stat'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { RouteMap } from '@/components/map/route-map'
import { api } from '@/lib/api'
import { toast } from 'sonner'
import { riskHexFromScore } from '@/lib/ui'
import type { EmergencyRoute, EventInput } from '@/lib/types'

const TABS = ['Event Analysis', 'Event Replay'] as const

export default function OperationsSuitePage() {
  const [tab, setTab] = useState<typeof TABS[number]>('Event Analysis')

  return (
    <div className="space-y-5">
      <PageHeader title="Operations Suite" description="Unified workspace: analyze events, run scenarios, replay past operations and plan routing." icon={<Activity className="h-5 w-5" />} />

      <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
        <aside className="space-y-3">
          <div className="glass rounded-xl p-4">
            <nav className="flex flex-col space-y-2">
              {TABS.map((t) => (
                <button key={t} onClick={() => setTab(t)} className={`w-full text-left rounded-md px-3 py-2 text-sm font-medium ${tab === t ? 'bg-primary/10 text-primary' : 'hover:bg-muted/20'}`}>
                  {t}
                </button>
              ))}
            </nav>
          </div>
        </aside>

        <main className="space-y-5">
          {tab === 'Event Analysis' && <EventAnalysisSection />}
          {tab === 'Event Replay' && <EventReplaySection />}
        </main>
      </div>
    </div>
  )
}

function EventAnalysisSection() {
  const [result, setResult] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)

  const analyze = async (input: EventInput) => {
    setLoading(true)
    try {
      const res = await api.analyzeEvent(input)
      setResult(res)
      toast.success('Analysis complete', { description: `${input.eventName} · Impact ${res.impactScore}/100` })
    } catch (err) {
      console.error(err)
      toast.error('Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <div className="lg:sticky lg:top-20 lg:self-start">
        <EventForm onAnalyze={analyze} loading={loading} />
      </div>

      <div className="space-y-5">
        {loading ? (
          <LoadingResults />
        ) : result ? (
          <Results result={result} />
        ) : (
          <EmptyState />
        )}
      </div>
    </div>
  )
}

function LoadingResults() {
  return (
    <>
      <Skeleton className="h-6 w-40" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {Array.from({ length: 9 }).map((_, i) => <Skeleton key={i} className="h-[104px] rounded-xl" />)}
      </div>
      <Skeleton className="h-40 rounded-xl" />
    </>
  )
}

function Results({ result }: { result: any }) {
  const danger = (v: number): 'danger' | 'warning' | 'neutral' | 'success' => (v >= 80 ? 'danger' : v >= 60 ? 'warning' : v >= 40 ? 'neutral' : 'success')
  return (
    <>
      <div>
        <h2 className="mb-3 text-sm font-semibold">Analysis Results</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <ResultStat label="Incident Volume" value={result.incidentVolume} intent={danger(result.hotspotRisk)} meter={Math.min(100, result.incidentVolume * 2)} />
          <ResultStat label="Hotspot Risk" value={result.hotspotRisk} unit="%" intent={danger(result.hotspotRisk)} meter={result.hotspotRisk} />
          <ResultStat label="Incident Duration" value={result.incidentDurationMin} unit="min" intent="warning" />
        </div>
      </div>

      <div className="glass rounded-xl p-5">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">Recommendations</h3>
        <RecommendationTimeline items={result.recommendations ?? []} />
      </div>
    </>
  )
}

function EmptyState() {
  return (
    <div className="glass flex min-h-[420px] flex-col items-center justify-center rounded-xl p-10 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 text-primary">
        <Activity className="h-7 w-7" />
      </div>
      <p className="mt-4 text-base font-medium">Run an event analysis</p>
      <p className="mt-1 max-w-sm text-sm leading-relaxed text-muted-foreground">Configure the event parameters on the left and click Analyze Event to generate predictions and operational recommendations.</p>
    </div>
  )
}

function EventReplaySection() {
  const [events, setEvents] = useState<any[] | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    api.eventReplay()
      .then((res) => { if (active) { setEvents(res); setSelectedId(res[0]?.id ?? null) } })
      .catch((err) => console.error('Event replay load failed:', err))
    return () => { active = false }
  }, [])

  const selected = events?.find((e) => e.id === selectedId) ?? null

  return (
    <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
      <div className="space-y-3">
        {!events ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />) : events.map((e) => (
          <button key={e.id} onClick={() => setSelectedId(e.id)} className={`glass w-full rounded-xl p-4 text-left transition-colors ${selectedId === e.id ? 'ring-1 ring-primary/50' : 'hover:bg-muted/30'}`}>
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium leading-snug">{e.name}</p>
              <span className="shrink-0 rounded-md px-2 py-0.5 text-xs font-semibold tabular-nums" style={{ background: `${riskHexFromScore(e.impactScore)}22`, color: riskHexFromScore(e.impactScore) }}>{e.impactScore}</span>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">{e.type}</span>
              <span className="flex items-center gap-1">{e.zone}</span>
              <span className="flex items-center gap-1">{e.date}</span>
            </div>
          </button>
        ))}
      </div>

      <div>
        {!selected ? <Skeleton className="h-96 rounded-xl" /> : (
          <div className="space-y-4">
            <div className="glass rounded-xl p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">{selected.name}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">{selected.zone} Zone · {selected.date}</p>
                </div>
                <div className="flex gap-2">
                  <span className="shrink-0 rounded-md px-2 py-0.5 text-xs font-semibold tabular-nums">{selected.duration}</span>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-3">
                <span className="text-xs text-muted-foreground">Impact Score</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full" style={{ width: `${selected.impactScore}%`, background: riskHexFromScore(selected.impactScore) }} />
                </div>
                <span className="font-mono text-sm font-semibold tabular-nums" style={{ color: riskHexFromScore(selected.impactScore) }}>{selected.impactScore}/100</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ScenarioSimulatorSection() {
  const BASE_EVENTS = ['Stadium Concert', 'Tech Expo', 'City Marathon']
  const SCENARIOS = ['Heavy Rain', 'VIP Movement', 'Metro Failure']
  const [baseEvent, setBaseEvent] = useState(BASE_EVENTS[0])
  const [scenario, setScenario] = useState(SCENARIOS[0])
  const [loading, setLoading] = useState(false)

  const run = async () => {
    setLoading(true)
    try {
      await api.simulateScenario(baseEvent, scenario)
      toast.success('Simulation complete')
    } catch {
      toast.error('Simulation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <div className="glass rounded-xl p-5">
        <h2 className="mb-4 text-sm font-semibold">Configure Scenario</h2>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Baseline Event</Label>
            <Select value={baseEvent} onValueChange={(val) => val && setBaseEvent(val)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{BASE_EVENTS.map((e) => <SelectItem key={e} value={e}>{e}</SelectItem>)}</SelectContent></Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">What-If Condition</Label>
            <Select value={scenario} onValueChange={(val) => val && setScenario(val)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{SCENARIOS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select>
          </div>
          <div className="flex gap-2 pt-1">
            <Button onClick={run} disabled={loading} className="flex-1">{loading ? 'Simulating…' : 'Run Simulation'}</Button>
          </div>
        </div>
      </div>

      <div>
        <div className="glass rounded-xl p-5">
          <h3 className="mb-3 text-sm font-semibold">Simulator Output</h3>
          <p className="text-sm text-muted-foreground">Run a simulation to compare projected impact before and after the disruption.</p>
        </div>
      </div>
    </div>
  )
}

function EmergencyRoutingSection() {
  const [source, setSource] = useState('Stadium Gate 3')
  const [destination, setDestination] = useState('Victoria Hospital')
  const [route, setRoute] = useState<EmergencyRoute | null>(null)
  const [loading, setLoading] = useState(false)

  const compute = async () => {
    if (!source.trim() || !destination.trim()) { toast.error('Enter source and destination'); return }
    setLoading(true)
    try {
      const res = await api.emergencyRoute(source, destination)
      setRoute(res)
      toast.success('Green corridor computed', { description: `ETA ${res.etaMinutes} min` })
    } catch {
      toast.error('Routing failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <div className="lg:sticky lg:top-20 lg:self-start space-y-4">
        <div className="glass rounded-xl p-5">
          <h2 className="mb-4 text-sm font-semibold">Route Request</h2>
          <div className="space-y-4">
            <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">Source</Label><Input value={source} onChange={(e) => setSource(e.target.value)} /></div>
            <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">Destination</Label><Input value={destination} onChange={(e) => setDestination(e.target.value)} /></div>
            <Button onClick={compute} disabled={loading} className="w-full">{loading ? 'Computing…' : 'Compute Green Corridor'}</Button>
          </div>
        </div>
      </div>

      <div>
        {loading ? <Skeleton className="h-[420px] rounded-xl" /> : route ? (
          <div className="space-y-4">
            <div className="glass rounded-xl p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold">{route.source} → {route.destination}</h2>
                  <p className="text-xs text-muted-foreground">ETA {route.etaMinutes} min · {route.distanceKm} km</p>
                </div>
                <div className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                  {route.status === 'ready' ? 'Green corridor ready' : route.status}
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-border/60 bg-background p-0 shadow-sm">
              <RouteMap route={route} />
            </div>
          </div>
        ) : (
          <div className="glass min-h-[420px] rounded-xl p-10 text-center">Enter a source and destination to compute a green corridor.</div>
        )}
      </div>
    </div>
  )
}

function OperationsBriefSection() {
  const [event, setEvent] = useState('City Marathon 2026')
  const [region, setRegion] = useState('Central Bangalore')
  const [timeWindow, setTimeWindow] = useState('06:00 – 12:00')
  const [brief, setBrief] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)

  const generate = async () => {
    setLoading(true)
    try {
      const res = await api.operationsBrief(event, region, timeWindow)
      setBrief(res)
      toast.success('Operations brief generated')
    } catch {
      toast.error('Generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="glass rounded-xl p-5">
        <div className="grid gap-4 md:grid-cols-[1fr_1fr_1fr_auto] md:items-end">
          <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">Event</Label><Input value={event} onChange={(e) => setEvent(e.target.value)} /></div>
          <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">Region</Label><Input value={region} onChange={(e) => setRegion(e.target.value)} /></div>
          <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">Time Window</Label><Input value={timeWindow} onChange={(e) => setTimeWindow(e.target.value)} /></div>
          <Button onClick={generate} disabled={loading}>{loading ? 'Generating…' : 'Generate Brief'}</Button>
        </div>
      </div>

      {loading ? <Skeleton className="h-32 rounded-xl" /> : brief ? (
        <div className="space-y-4">
          <div className="glass rounded-xl p-6">
            <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">{brief.event}</h2><span className="text-xs text-muted-foreground">Generated</span></div>
            <p className="mt-1 text-sm text-muted-foreground">{brief.region} · {brief.timeWindow}</p>
            <div className="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-4"><p className="text-sm leading-relaxed">{brief.executiveSummary}</p></div>
          </div>
        </div>
      ) : (
        <div className="glass min-h-[200px] rounded-xl p-6 text-center">Generate an operations brief from the controls above.</div>
      )}
    </div>
  )
}

function CascadeStudioSection() {
  const [data, setData] = useState<any | null>(null)
  useEffect(() => { let active = true; api.cascadeSpread().then((r) => active && setData(r)).catch(() => {}); return () => { active = false } }, [])
  if (!data) return <Skeleton className="h-[460px] rounded-xl" />
  return (
    <div>
      <div className="glass rounded-xl p-5">
        <h3 className="text-sm font-semibold">Cascade Studio</h3>
        <p className="text-xs text-muted-foreground">Simulate congestion spread — visualized in the cascade graph view.</p>
      </div>
    </div>
  )
}
