'use client'

import { AlertTriangle, Bell, CheckCircle2, Info, Siren } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

interface Notif {
  id: string
  title: string
  body: string
  time: string
  kind: 'critical' | 'warning' | 'info' | 'success'
  unread: boolean
}

// Notifications are populated at runtime (e.g. via WebSocket or API).
// No static seed data — all values must come from live sources.

const ICONS = {
  critical: Siren,
  warning: AlertTriangle,
  info: Info,
  success: CheckCircle2,
}

const TONES = {
  critical: 'text-destructive bg-destructive/15',
  warning: 'text-warning bg-warning/15',
  info: 'text-primary bg-primary/15',
  success: 'text-success bg-success/15',
}

export function NotificationCenter() {
  const [items, setItems] = useState<Notif[]>([])
  const unread = items.filter((i) => i.unread).length

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
            <Bell className="h-4.5 w-4.5" />
            {unread > 0 ? (
              <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold text-destructive-foreground">
                {unread}
              </span>
            ) : null}
          </Button>
        }
      />
      <DropdownMenuContent align="end" className="w-[360px] p-0">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold">Notification Center</p>
            <Badge variant="secondary" className="h-5 px-1.5 text-[10px]">
              {unread} new
            </Badge>
          </div>
          <button
            type="button"
            onClick={() => setItems((prev) => prev.map((i) => ({ ...i, unread: false })))}
            className="text-xs text-primary hover:underline"
          >
            Mark all read
          </button>
        </div>
        <ScrollArea className="h-[340px]">
          <div className="divide-y divide-border">
            {items.map((n) => {
              const Icon = ICONS[n.kind]
              return (
                <div
                  key={n.id}
                  className={cn(
                    'flex gap-3 px-4 py-3 transition-colors hover:bg-muted/50',
                    n.unread && 'bg-muted/30',
                  )}
                >
                  <span className={cn('mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg', TONES[n.kind])}>
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium leading-snug">{n.title}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{n.body}</p>
                    <p className="mt-1 text-[11px] text-muted-foreground/70">{n.time}</p>
                  </div>
                  {n.unread ? <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary" /> : null}
                </div>
              )
            })}
          </div>
        </ScrollArea>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
