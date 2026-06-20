'use client'

import type { CascadeResult } from '@/lib/types'
import { riskHexFromScore } from '@/lib/ui'

export function CascadeGraph({ data, frame }: { data: CascadeResult; frame: string }) {
  const nodes = data?.nodes ?? []
  const edges = data?.edges ?? []
  const nodeById = Object.fromEntries(nodes.map((n) => [n.id, n]))

  return (
    <div className="relative w-full overflow-hidden rounded-xl border border-border/60 bg-[#0a0f1c]">
      <svg viewBox="0 0 100 100" className="h-[460px] w-full" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Congestion cascade network">
        {/* edges */}
        {edges.map((e, i) => {
          const a = nodeById[e.from]
          const b = nodeById[e.to]
          if (!a || !b) return null
          const riskA = a.risk?.[frame] ?? 0
          const riskB = b.risk?.[frame] ?? 0
          const risk = (riskA + riskB) / 2
          const ax = a.x ?? 0
          const ay = a.y ?? 0
          const bx = b.x ?? 0
          const by = b.y ?? 0
          return (
            <line
              key={i}
              x1={ax}
              y1={ay}
              x2={bx}
              y2={by}
              stroke={riskHexFromScore(risk)}
              strokeWidth={0.6}
              strokeOpacity={0.5}
              strokeDasharray="2 1.5"
            />
          )
        })}
        {/* nodes */}
        {nodes.map((n) => {
          const risk = n.risk?.[frame] ?? 0
          const color = riskHexFromScore(risk)
          const r = 2.4 + (risk / 100) * 2.6
          const nx = n.x ?? 0
          const ny = n.y ?? 0
          return (
            <g key={n.id}>
              <circle cx={nx} cy={ny} r={r + 2.5} fill={color} fillOpacity={0.18} />
              <circle cx={nx} cy={ny} r={r} fill={color} fillOpacity={0.95} />
              <text
                x={nx}
                y={ny - r - 1.5}
                textAnchor="middle"
                fill="#cbd5e1"
                fontSize={2.6}
                fontWeight={500}
              >
                {n.label}
              </text>
              <text x={nx} y={ny + 0.9} textAnchor="middle" fill="#0a0f1c" fontSize={2.4} fontWeight={700}>
                {risk}
              </text>
            </g>
          )
        })}
      </svg>

      <div className="absolute bottom-3 left-3 flex flex-wrap gap-3 rounded-lg bg-card/80 px-3 py-2 text-[11px] backdrop-blur">
        {[
          { c: '#ef4444', l: 'Severe' },
          { c: '#f59e0b', l: 'High' },
          { c: '#3b82f6', l: 'Moderate' },
          { c: '#10b981', l: 'Low' },
        ].map((x) => (
          <span key={x.l} className="flex items-center gap-1.5 text-muted-foreground">
            <span className="h-2 w-2 rounded-full" style={{ background: x.c }} /> {x.l}
          </span>
        ))}
      </div>
    </div>
  )
}
