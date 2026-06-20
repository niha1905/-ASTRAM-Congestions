export type Priority = 'critical' | 'high' | 'medium' | 'low'
export type RiskLevel = 'severe' | 'high' | 'moderate' | 'low'
export type RecStatus = 'pending' | 'active' | 'completed'

export interface KpiMetric {
  id: string
  label: string
  value: number
  unit?: string
  delta: number
  trend: 'up' | 'down' | 'flat'
  intent: 'neutral' | 'success' | 'warning' | 'danger'
}

export interface Corridor {
  id: string
  name: string
  path: [number, number][]
  congestion: number // 0-100
  status: RiskLevel
}

export interface Hotspot {
  id: string
  name: string
  position: [number, number]
  risk: number // 0-100
  level: RiskLevel
}

export interface EventLocation {
  id: string
  name: string
  type: string
  position: [number, number]
  attendance: number
  priority: Priority
  // optional AI / news metadata
  predictions?: any
  news?: any
  sentiment?: 'positive' | 'negative' | 'neutral'
  impact_score?: number
  traffic_plan?: any
  pre_measures?: any
  inferred?: any
  link?: string
}

export interface EmergencyRoute {
  id: string
  source: string
  destination: string
  path: [number, number][]
  alternativePath?: [number, number][]
  etaMinutes: number
  distanceKm: number
  alternativeEtaMinutes?: number
  alternativeDistanceKm?: number
  signals: { name: string; position: [number, number]; action: string }[]
  bottlenecks: { name: string; position: [number, number] }[]
  status: 'ready' | 'active' | 'clearing'
}

export interface Recommendation {
  id: string
  title: string
  detail: string
  priority: Priority
  confidence: number // 0-100
  status: RecStatus
  category: string
}

export interface SeriesPoint {
  t: string
  value: number
  forecast?: number
}

export interface AnalysisResult {
  incidentVolume: number
  hotspotRisk: number
  incidentDurationMin: number
  roadClosureProbability: number
  impactScore: number
  officersRequired: number
  barricadesRequired: number
  parkingOverflowRisk: number
  cascadeRisk: number
  confidence: Record<string, number>
  recommendations: Recommendation[]
}

export interface ScenarioMetrics {
  impactScore: number
  congestion: number
  officersRequired: number
  incidentVolume: number
  delayMinutes: number
  parkingOverflow: number
}

export interface ScenarioResult {
  scenario: string
  before: ScenarioMetrics
  after: ScenarioMetrics
}

export interface CascadeNode {
  id: string
  label: string
  type: 'corridor' | 'intersection'
  x: number
  y: number
  risk: Record<string, number> // frame -> risk
}

export interface CascadeEdge {
  from: string
  to: string
}

export interface CascadeResult {
  frames: string[]
  nodes: CascadeNode[]
  edges: CascadeEdge[]
}

export interface ReplayEvent {
  id: string
  name: string
  type: string
  zone: string
  date: string
  impactScore: number
  duration: string
  decisions: { time: string; action: string; outcome: string }[]
}

export interface AiModel {
  id: string
  name: string
  purpose: string
  status: 'operational' | 'training' | 'degraded'
  lastUpdated: string
  accuracy: number
}

export interface OperationsBrief {
  event: string
  region: string
  timeWindow: string
  executiveSummary: string
  riskAssessment: string[]
  resourcePlan: { resource: string; quantity: string; location: string }[]
  emergencyPlan: string[]
  recommendations: string[]
  generatedAt: string
}

export interface EventInput {
  eventName: string
  eventType: string
  zone: string
  corridor: string
  attendance: number
  weather: string
  priority: Priority
  date: string
  time: string
}
