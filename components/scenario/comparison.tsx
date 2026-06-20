'use client'

import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ScenarioMetrics, ScenarioResult } from '@/lib/types'
import { cn } from '@/lib/utils'

const METRICS: { key: keyof ScenarioMetrics; label: string; unit?: string }[] = [
  { key: 'impactScore', label: 'Impact Score', unit: '/100' },
  { key: 'congestion', label: 'Congestion', unit: '%' },
  { key: 'officersRequired', label: 'Officers' },
  { key: 'incidentVolume', label: 'Incidents' },
  { key: 'delayMinutes', label: 'Avg Delay', unit: 'min' },
  { key: 'parkingOverflow', label: 'Parking Overflow', unit: '%' },
]

function MetricColumn({ title, metrics, tone }: { title: string; metrics: ScenarioMetrics; tone: 'before' | 'after' }) {
  return (
    <div className="glass rounded-xl p-4">
      <p className={cn('mb-3 text-xs font-semibold uppercase tracking-wider', tone === 'before' ? 'text-muted-foreground' : 'text-warning')}>
        {title}
      </p>
      <div className="space-y-2.5">
        {METRICS.map((m) => (
          <div key={m.key} className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{m.label}</span>
            <span className="font-mono font-medium tabular-nums">
              {metrics[m.key]}
              {m.unit ? <span className="text-xs text-muted-foreground">{m.unit}</span> : null}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function ScenarioComparison({ result }: { result: ScenarioResult }) {
  const chartData = METRICS.map((m) => ({
    name: m.label,
    Before: result.before[m.key],
    After: result.after[m.key],
  }))

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-2">
        <MetricColumn title="Before" metrics={result.before} tone="before" />
        <MetricColumn title={`After · ${result.scenario}`} metrics={result.after} tone="after" />
      </div>

      <div>
        <h3 className="mb-3 text-sm font-semibold">Difference</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {METRICS.map((m) => {
            const before = result.before[m.key]
            const after = result.after[m.key]
            const diff = after - before
            const pct = before ? Math.round((diff / before) * 100) : 0
            const worse = diff > 0
            const Icon = diff === 0 ? ArrowRight : worse ? ArrowUpRight : ArrowDownRight
            return (
              <div key={m.key} className="glass rounded-xl p-4">
                <p className="text-xs text-muted-foreground">{m.label}</p>
                <div className={cn('mt-1.5 flex items-center gap-1 text-lg font-semibold tabular-nums', worse ? 'text-destructive' : diff < 0 ? 'text-success' : 'text-foreground')}>
                  <Icon className="h-4 w-4" />
                  {diff > 0 ? '+' : ''}{diff}
                  {m.unit ? <span className="text-xs text-muted-foreground">{m.unit}</span> : null}
                </div>
                <p className={cn('mt-0.5 text-xs font-medium', worse ? 'text-destructive' : diff < 0 ? 'text-success' : 'text-muted-foreground')}>
                  {pct > 0 ? '+' : ''}{pct}% vs baseline
                </p>
              </div>
            )
          })}
        </div>
      </div>

      <div className="glass rounded-xl p-4">
        <h3 className="mb-3 text-sm font-semibold">Before vs After</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" vertical={false} />
            <XAxis dataKey="name" stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} interval={0} angle={-15} textAnchor="end" height={50} />
            <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} width={36} />
            <Tooltip
              cursor={{ fill: 'rgba(148,163,184,0.06)' }}
              contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }}
            />
            <Bar dataKey="Before" radius={[4, 4, 0, 0]} fill="#3b82f6">
              {chartData.map((_, i) => <Cell key={i} fill="#3b82f6" />)}
            </Bar>
            <Bar dataKey="After" radius={[4, 4, 0, 0]} fill="#ef4444">
              {chartData.map((_, i) => <Cell key={i} fill="#f59e0b" />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
