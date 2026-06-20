'use client'

import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { SeriesPoint } from '@/lib/types'

interface AnalyticsChartProps {
  data: SeriesPoint[]
  type?: 'area' | 'line'
  color?: string
  height?: number
  showForecast?: boolean
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-border bg-popover/95 px-3 py-2 text-xs shadow-xl backdrop-blur">
      <p className="mb-1 font-medium text-popover-foreground">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} className="flex items-center gap-2 text-muted-foreground">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color || p.stroke }} />
          <span className="capitalize">{p.dataKey}</span>
          <span className="ml-auto font-mono font-medium text-popover-foreground">{p.value}</span>
        </p>
      ))}
    </div>
  )
}

export function AnalyticsChart({
  data,
  type = 'area',
  color = '#3b82f6',
  height = 200,
  showForecast = false,
}: AnalyticsChartProps) {
  const id = `grad-${color.replace('#', '')}`
  return (
    <ResponsiveContainer width="100%" height={height}>
      {type === 'area' ? (
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" vertical={false} />
          <XAxis dataKey="t" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} width={36} />
          <Tooltip content={<ChartTooltip />} />
          <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2} fill={`url(#${id})`} />
          {showForecast ? (
            <Area
              type="monotone"
              dataKey="forecast"
              stroke="#22d3ee"
              strokeWidth={2}
              strokeDasharray="4 4"
              fill="none"
            />
          ) : null}
        </AreaChart>
      ) : (
        <LineChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" vertical={false} />
          <XAxis dataKey="t" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} width={36} />
          <Tooltip content={<ChartTooltip />} />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} dot={false} />
        </LineChart>
      )}
    </ResponsiveContainer>
  )
}
