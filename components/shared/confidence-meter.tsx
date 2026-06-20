import { cn } from '@/lib/utils'

interface ConfidenceMeterProps {
  value: number
  label?: string
  className?: string
}

export function ConfidenceMeter({ value, label = 'Confidence', className }: ConfidenceMeterProps) {
  const color = value >= 85 ? 'bg-success' : value >= 70 ? 'bg-primary' : 'bg-warning'
  return (
    <div className={cn('space-y-1.5', className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono font-medium tabular-nums">{value}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn('h-full rounded-full transition-all duration-700', color)}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  )
}
