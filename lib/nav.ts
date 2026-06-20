import { LayoutDashboard, BrainCircuit, FileText, type LucideIcon } from 'lucide-react'

export interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  description: string
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/', icon: LayoutDashboard, description: 'Operations overview' },
  { label: 'Operations Suite', href: '/operations-suite', icon: FileText, description: 'Analyze events, run scenarios, replay operations' },
]
