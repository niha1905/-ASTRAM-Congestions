import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ResultStatProps {
  label: string
  value: string | number
  unit?: string
  icon?: LucideIcon
  intent?: 'neutral' | 'success' | 'warning' | 'danger'
  meter?: number
}

const INTENT = {
  neutral: { text: 'text-foreground', bar: 'bg-primary', ring: 'text-primary bg-primary/15' },
  success: { text: 'text-success', bar: 'bg-success', ring: 'text-success bg-success/15' },
  warning: { text: 'text-warning', bar: 'bg-warning', ring: 'text-warning bg-warning/15' },
  danger: { text: 'text-destructive', bar: 'bg-destructive', ring: 'text-destructive bg-destructive/15' },
}

export function ResultStat({ label, value, unit, icon: Icon, intent = 'neutral', meter }: ResultStatProps) {
  const c = INTENT[intent]
  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        {Icon ? (
          <span className={cn('flex h-7 w-7 items-center justify-center rounded-lg', c.ring)}>
            <Icon className="h-3.5 w-3.5" />
          </span>
        ) : null}
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className={cn('text-2xl font-semibold tabular-nums tracking-tight', c.text)}>{value}</span>
        {unit ? <span className="text-xs text-muted-foreground">{unit}</span> : null}
      </div>
      {meter != null ? (
        <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div className={cn('h-full rounded-full transition-all duration-700', c.bar)} style={{ width: `${meter}%` }} />
        </div>
      ) : null}
    </div>
  )
}
