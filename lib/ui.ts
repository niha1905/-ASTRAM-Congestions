import type { Priority, RiskLevel } from './types'

export const PRIORITY_STYLES: Record<Priority, string> = {
  critical: 'bg-destructive/15 text-destructive border-destructive/30',
  high: 'bg-warning/15 text-warning border-warning/30',
  medium: 'bg-primary/15 text-primary border-primary/30',
  low: 'bg-muted text-muted-foreground border-border',
}

export const RISK_STYLES: Record<RiskLevel, string> = {
  severe: 'bg-destructive/15 text-destructive border-destructive/30',
  high: 'bg-warning/15 text-warning border-warning/30',
  moderate: 'bg-primary/15 text-primary border-primary/30',
  low: 'bg-success/15 text-success border-success/30',
}

export const RISK_HEX: Record<RiskLevel, string> = {
  severe: '#ef4444',
  high: '#f59e0b',
  moderate: '#3b82f6',
  low: '#10b981',
}

export function riskHexFromScore(score: number): string {
  if (score >= 80) return '#ef4444'
  if (score >= 60) return '#f59e0b'
  if (score >= 40) return '#3b82f6'
  return '#10b981'
}

export function riskLevelFromScore(score: number): RiskLevel {
  if (score >= 80) return 'severe'
  if (score >= 60) return 'high'
  if (score >= 40) return 'moderate'
  return 'low'
}

export const INTENT_TEXT: Record<string, string> = {
  neutral: 'text-foreground',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-destructive',
}
