import { Badge } from '@/components/ui/badge'
import type { Recommendation } from '@/lib/types'
import { PRIORITY_STYLES } from '@/lib/ui'
import { cn } from '@/lib/utils'

export function RecommendationTimeline({ items }: { items: Recommendation[] }) {
  return (
    <ol className="relative space-y-4 border-l border-border pl-6">
      {items.map((rec) => (
        <li key={rec.id} className="relative">
          <span className="absolute -left-[27px] top-1 flex h-3.5 w-3.5 items-center justify-center rounded-full border-2 border-primary bg-background">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          </span>
          <div className="glass rounded-lg p-3.5">
            <div className="flex items-center justify-between gap-2">
              <Badge variant="outline" className={cn('capitalize', PRIORITY_STYLES[rec.priority])}>
                {rec.priority}
              </Badge>
              <span className="text-[11px] text-muted-foreground">{rec.category}</span>
            </div>
            <p className="mt-2 text-sm font-medium leading-snug">{rec.title}</p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{rec.detail}</p>
            <div className="mt-2.5 flex items-center gap-2">
              <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
                <div className="h-full rounded-full bg-primary" style={{ width: `${rec.confidence}%` }} />
              </div>
              <span className="font-mono text-[11px] text-muted-foreground">{rec.confidence}% confidence</span>
            </div>
          </div>
        </li>
      ))}
    </ol>
  )
}
