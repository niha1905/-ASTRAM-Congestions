'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

export function ConnectionStatus() {
  const [state, setState] = useState<'checking' | 'live' | 'down'>('checking')

  useEffect(() => {
    let active = true
    api.health()
      .then((r) => {
        if (!active) return
        if (r.status === 'ok') setState('live')
        else setState('down')
      })
      .catch(() => {
        if (!active) return
        setState('down')
      })
    return () => {
      active = false
    }
  }, [])

  const config = {
    checking: { dot: 'bg-muted-foreground', label: 'Checking…', ring: 'ring-border' },
    live: { dot: 'bg-success', label: 'Live · Connected', ring: 'ring-success/30' },
    down: { dot: 'bg-destructive', label: 'Backend Unreachable', ring: 'ring-destructive/30' },
  }[state]

  return (
    <div
      className={cn(
        'hidden items-center gap-2 rounded-full bg-muted/50 px-3 py-1.5 text-xs font-medium ring-1 sm:flex',
        config.ring,
      )}
    >
      <span className="relative flex h-2 w-2">
        {state !== 'checking' ? (
          <span className={cn('absolute inline-flex h-full w-full animate-ping rounded-full opacity-60', config.dot)} />
        ) : null}
        <span className={cn('relative inline-flex h-2 w-2 rounded-full', config.dot)} />
      </span>
      {config.label}
    </div>
  )
}
