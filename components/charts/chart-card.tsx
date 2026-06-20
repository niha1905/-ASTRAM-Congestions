import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface ChartCardProps {
  title: string
  subtitle?: string
  badge?: ReactNode
  children: ReactNode
  className?: string
}

export function ChartCard({ title, subtitle, badge, children, className }: ChartCardProps) {
  return (
    <div className={cn('glass rounded-xl p-4', className)}>
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          {subtitle ? <p className="text-xs text-muted-foreground">{subtitle}</p> : null}
        </div>
        {badge}
      </div>
      {children}
    </div>
  )
}
