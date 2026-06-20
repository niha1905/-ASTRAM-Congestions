"use client"

import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { cn, stripHtml, extractFirstLink } from '@/lib/utils'
import { NEWS_DEFAULT_LIMIT, SKELETON_LOADING_COUNT } from '@/lib/constants'

export default function NewsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<any[]>([])
  const [selected, setSelected] = useState<number>(0)
  const [todayOnly, setTodayOnly] = useState(false)

  useEffect(() => {
    let active = true
    if (!open) return
    setLoading(true)
    api.fetchNews(undefined, NEWS_DEFAULT_LIMIT)
      .then((res: any) => {
        if (!active) return
        setItems(res || [])
        setSelected(0)
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [open])

  // compute items to display based on todayOnly toggle
  const displayedItems = todayOnly
    ? items.filter((it) => {
        const pub = it.news?.published || it.published
        if (!pub) return false
        const d = Date.parse(pub)
        if (isNaN(d)) return false
        return d >= (Date.now() - 24 * 60 * 60 * 1000)
      })
    : items

  // reset selected if out of range when displayedItems change
  useEffect(() => {
    if (selected >= displayedItems.length) setSelected(0)
  }, [displayedItems, selected])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl max-h-[85vh] overflow-y-auto bg-card border border-border/80 text-foreground">
        <DialogHeader>
          <div className="flex items-start gap-3 w-full">
            <div className="flex-1">
              <DialogTitle className="text-foreground">Latest Event Alerts — This Week</DialogTitle>
              <DialogDescription className="text-muted-foreground">Web-scraped news (past 7 days) with inferred impact and recommended actions.</DialogDescription>
            </div>
            <div className="flex items-center gap-2">
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
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-3">
          <div className="col-span-1 space-y-2 max-h-[60vh] overflow-y-auto pr-1">
            {loading ? (
              Array.from({ length: SKELETON_LOADING_COUNT }).map((_, i) => (
                <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
              ))
            ) : displayedItems.length === 0 ? (
              <div className="rounded-lg border border-muted/30 bg-muted/5 p-4 text-sm text-muted-foreground">No recent news items found for this selection.</div>
            ) : (
              displayedItems.map((it: any, idx: number) => (
                <div key={idx} onClick={() => setSelected(idx)} className={cn(
                  'rounded-lg p-3 cursor-pointer border border-border/30 hover:border-primary/50 bg-card/10',
                  selected === idx ? 'border-primary bg-primary/8 scale-[1.01]' : ''
                )}>
                  <div className="flex items-center justify-between">
                    <div className="text-xs text-muted-foreground">{it.news?.source || it.source || 'Google News'}</div>
                    <div className="text-[11px] text-muted-foreground">{it.news?.published ? new Date(it.news.published).toLocaleString() : ''}</div>
                  </div>
                  <div className="mt-1 text-sm font-semibold text-foreground line-clamp-2">{it.news?.title || it.title}</div>
                  {it.news?.summary && <div className="mt-1 text-xs text-muted-foreground line-clamp-2">{it.news.summary}</div>}
                </div>
              ))
            )}
          </div>

          <div className="md:col-span-2 space-y-3">
            {displayedItems[selected] ? (
              <div className="space-y-3">
                <h3 className="text-lg font-semibold text-foreground">{displayedItems[selected].news?.title || displayedItems[selected].title}</h3>
                <div className="text-xs text-muted-foreground">Source: {displayedItems[selected].news?.source || displayedItems[selected].source || 'Google News'}</div>
                <div className="rounded-xl glass p-4">
                  <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider mb-2">Predicted ML Metrics</h4>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    <div className="rounded-lg border border-border/60 bg-card/40 p-3">
                      <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Closure Probability</span>
                      <div className="text-xl font-bold text-destructive mt-1">{displayedItems[selected].predictions?.closure?.closure_probability ?? '—'}%</div>
                      <div className="text-[9px] text-muted-foreground">Estimated</div>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-card/40 p-3">
                      <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Impact Score</span>
                      <div className="text-xl font-bold text-warning mt-1">{displayedItems[selected].predictions?.impact?.impact_score ?? '—'}</div>
                      <div className="text-[9px] text-muted-foreground">Model Estimate</div>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-card/40 p-3">
                      <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Recommended Officers</span>
                      <div className="text-xl font-bold text-success mt-1">{displayedItems[selected].predictions?.resources?.officers_needed ?? '—'}</div>
                      <div className="text-[9px] text-muted-foreground">Resource Est.</div>
                    </div>
                  </div>

                  {displayedItems[selected].pre_measures && displayedItems[selected].pre_measures.length > 0 && (
                    <div className="mt-4">
                      <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Recommended Actions</h5>
                      <div className="space-y-2">
                        {displayedItems[selected].pre_measures.map((r: string, i: number) => (
                          <div key={i} className="rounded-lg border border-border/40 bg-card/25 p-2.5 text-xs">{r}</div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mt-4 text-sm text-muted-foreground">{stripHtml(displayedItems[selected].news?.summary || displayedItems[selected].summary)}</div>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button variant="outline" className="flex-1" onClick={() => onOpenChange(false)}>Close</Button>
                  <Button className="flex-1" onClick={() => {
                    const src = displayedItems[selected].news?.link || displayedItems[selected].link || extractFirstLink(displayedItems[selected].news?.summary) || extractFirstLink(displayedItems[selected].summary)
                    if (src) window.open(src, '_blank')
                  }}>Open Source</Button>
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-muted/30 bg-muted/5 p-4 text-sm text-muted-foreground">Select a news item to view details.</div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
