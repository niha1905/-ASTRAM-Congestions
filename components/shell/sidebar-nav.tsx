'use client'

import { Radar } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { NAV_ITEMS } from '@/lib/nav'
import { cn } from '@/lib/utils'

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()

  return (
    <div className="flex h-full flex-col bg-sidebar">
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-primary/15 ring-1 ring-primary/30">
          <Radar className="h-5 w-5 text-primary" />
          <span className="absolute -right-0.5 -top-0.5 flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-success" />
          </span>
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold tracking-tight text-sidebar-foreground">
            ASTRAM
          </p>
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-primary">
            CongestionIQ
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
        {NAV_ITEMS.map((item) => {
          const active =
            item.href === '/' ? pathname === '/' : pathname.startsWith(item.href)
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                active
                  ? 'bg-sidebar-accent text-sidebar-foreground'
                  : 'text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground',
              )}
            >
              <span
                className={cn(
                  'flex h-7 w-7 items-center justify-center rounded-md transition-colors',
                  active
                    ? 'bg-primary/20 text-primary'
                    : 'text-muted-foreground group-hover:text-sidebar-foreground',
                )}
              >
                <Icon className="h-4 w-4" />
              </span>
              <span className="flex-1 truncate font-medium">{item.label}</span>
              {active ? <span className="h-1.5 w-1.5 rounded-full bg-primary" /> : null}
            </Link>
          )
        })}
      </nav>

      <div className="mx-3 mb-4 rounded-lg border border-sidebar-border bg-sidebar-accent/40 p-3">
        <div className="flex items-center gap-2">
          <span className="flex h-2 w-2 rounded-full bg-success" />
          <p className="text-xs font-medium text-sidebar-foreground">All systems nominal</p>
        </div>
        <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
          6 models operational · Bangalore grid synced
        </p>
      </div>
    </div>
  )
}
