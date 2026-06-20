'use client'

import { Clock, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Input } from '@/components/ui/input'
import { ConnectionStatus } from './connection-status'
import { NotificationCenter } from './notification-center'
import { UI_STRINGS } from '@/components/constants'

export function TopHeader({ mobileNav }: { mobileNav?: React.ReactNode }) {
  const [now, setNow] = useState<string>('')

  useEffect(() => {
    const tick = () =>
      setNow(
        new Date().toLocaleTimeString('en-IN', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
        }),
      )
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-background/70 px-4 backdrop-blur-xl lg:px-6">
      {mobileNav}
      <div className="relative hidden max-w-md flex-1 md:block">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder={UI_STRINGS.searchPlaceholder}
          className="h-9 border-border/60 bg-muted/40 pl-9"
        />
      </div>
      <div className="flex flex-1 items-center justify-end gap-2 md:flex-none md:gap-3">
        <div className="hidden items-center gap-2 rounded-full bg-muted/50 px-3 py-1.5 font-mono text-xs text-muted-foreground lg:flex">
          <Clock className="h-3.5 w-3.5" />
          <span className="tabular-nums">{now}</span>
          <span className="text-muted-foreground/60">{UI_STRINGS.clockLabel}</span>
        </div>
        <ConnectionStatus />
        <NotificationCenter />
        <div className="flex items-center gap-2 rounded-full bg-muted/50 py-1 pl-1 pr-3">
          <Avatar className="h-7 w-7">
            <AvatarFallback className="bg-primary/20 text-xs font-semibold text-primary">
              OC
            </AvatarFallback>
          </Avatar>
          <div className="hidden leading-tight sm:block">
            <p className="text-xs font-medium">Ops Commander</p>
            <p className="text-[10px] text-muted-foreground">Control Room A</p>
          </div>
        </div>
      </div>
    </header>
  )
}
