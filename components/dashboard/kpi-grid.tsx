import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import type { KpiMetric } from '@/lib/types'
import { INTENT_TEXT } from '@/lib/ui'
import { cn } from '@/lib/utils'
import { SKELETON_LOADING_COUNT } from '@/lib/constants'

const ACCENT: Record<string, string> = {
  neutral: 'before:bg-primary',
  success: 'before:bg-success',
  warning: 'before:bg-warning',
  danger: 'before:bg-destructive',
}

export function KpiGrid({ kpis, loading }: { kpis: KpiMetric[]; loading?: boolean }) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: kpis.length || SKELETON_LOADING_COUNT }).map((_, i) => (
          <Skeleton key={i} className="h-[104px] rounded-xl" />
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
      {kpis.map((k) => {
        const TrendIcon = k.trend === 'up' ? ArrowUpRight : k.trend === 'down' ? ArrowDownRight : Minus
        const trendColor =
          k.intent === 'danger'
            ? 'text-destructive'
            : k.intent === 'warning'
              ? 'text-warning'
              : k.trend === 'down'
                ? 'text-success'
                : 'text-success'
        return (
          <div
            key={k.id}
            className={cn(
              'glass relative overflow-hidden rounded-xl p-4',
              "before:absolute before:left-0 before:top-0 before:h-full before:w-1 before:content-['']",
              ACCENT[k.intent],
            )}
          >
            <p className="truncate text-xs font-medium text-muted-foreground">{k.label}</p>
            <div className="mt-2 flex items-baseline gap-1">
              <span className={cn('text-2xl font-semibold tabular-nums tracking-tight', INTENT_TEXT[k.intent])}>
                {k.value.toLocaleString()}
              </span>
              {k.unit ? <span className="text-xs text-muted-foreground">{k.unit}</span> : null}
            </div>
            <div className={cn('mt-1.5 flex items-center gap-1 text-xs font-medium', trendColor)}>
              <TrendIcon className="h-3.5 w-3.5" />
              <span className="tabular-nums">{Math.abs(k.delta)}</span>
              <span className="text-muted-foreground/70">vs last hr</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
