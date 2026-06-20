'use client'

import { Check, Clock3, Sparkles, Zap } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { Recommendation, RecStatus } from '@/lib/types'
import { PRIORITY_STYLES } from '@/lib/ui'
import { cn } from '@/lib/utils'
import { SKELETON_LOADING_COUNT } from '@/lib/constants'

export function AiInsights({
  recommendations,
  loading,
}: {
  recommendations: Recommendation[]
  loading?: boolean
}) {
  const [statuses, setStatuses] = useState<Record<string, RecStatus>>({})

  const apply = (rec: Recommendation) => {
    setStatuses((prev) => ({ ...prev, [rec.id]: 'active' }))
    toast.success('Recommendation deployed', { description: rec.title })
  }

  return (
    <div className="glass flex h-full flex-col rounded-xl">
      <div className="flex items-center justify-between border-b border-border px-4 py-3.5">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <Sparkles className="h-4 w-4" />
          </span>
          <div>
            <p className="text-sm font-semibold">AI Insights</p>
            <p className="text-[11px] text-muted-foreground">MasterAgent recommendations</p>
          </div>
        </div>
        <Badge variant="secondary" className="gap-1 text-[10px]">
          <Zap className="h-3 w-3 text-primary" />
          Live
        </Badge>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {loading
          ? Array.from({ length: SKELETON_LOADING_COUNT }).map((_, i) => <Skeleton key={i} className="h-28 rounded-lg" />)
          : recommendations.map((rec) => {
              const status = statuses[rec.id] ?? rec.status
              return (
                <div key={rec.id} className="rounded-lg border border-border bg-card/50 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <Badge variant="outline" className={cn('shrink-0 capitalize', PRIORITY_STYLES[rec.priority])}>
                      {rec.priority}
                    </Badge>
                    <span className="text-[11px] text-muted-foreground">{rec.category}</span>
                  </div>
                  <p className="mt-2 text-sm font-medium leading-snug">{rec.title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{rec.detail}</p>
                  <div className="mt-3 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${rec.confidence}%` }} />
                      </div>
                      <span className="font-mono text-[11px] text-muted-foreground">{rec.confidence}%</span>
                    </div>
                    {status === 'active' ? (
                      <span className="flex items-center gap-1 text-xs font-medium text-success">
                        <Check className="h-3.5 w-3.5" /> Active
                      </span>
                    ) : status === 'completed' ? (
                      <span className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Check className="h-3.5 w-3.5" /> Done
                      </span>
                    ) : (
                      <Button size="sm" variant="secondary" className="h-7 gap-1 text-xs" onClick={() => apply(rec)}>
                        <Clock3 className="h-3 w-3" /> Deploy
                      </Button>
                    )}
                  </div>
                </div>
              )
            })}
      </div>
    </div>
  )
}
