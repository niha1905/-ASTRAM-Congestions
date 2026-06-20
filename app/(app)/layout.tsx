import type { ReactNode } from 'react'
import { MobileNav } from '@/components/shell/mobile-nav'
import { SidebarNav } from '@/components/shell/sidebar-nav'
import { TopHeader } from '@/components/shell/top-header'

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-sidebar-border lg:block">
        <SidebarNav />
      </aside>
      <div className="flex min-h-screen w-full flex-col lg:pl-64">
        <TopHeader mobileNav={<MobileNav />} />
        <main className="grid-glow flex-1 p-4 lg:p-6">{children}</main>
      </div>
    </div>
  )
}
