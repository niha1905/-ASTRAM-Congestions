'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useHotspotRiskPrediction } from '@/hooks/use-ml-predictions'
import { AlertCircle, TrendingUp, AlertTriangle } from 'lucide-react'

interface HotspotData {
  id: string
  name: string
  risk_score: number
}

interface HotspotGridProps {
  hotspots?: HotspotData[]
}

export function HotspotRiskGrid({ hotspots = [] }: HotspotGridProps) {
  const { data, predict } = useHotspotRiskPrediction()
  const [predictions, setPredictions] = useState<Record<string, any>>({})

  useEffect(() => {
    // Predict risk for all hotspots
    const hour = new Date().getHours()
    const weekday = new Date().getDay()

    hotspots.forEach(async (hotspot) => {
      try {
        const result = await predict({
          junction: hotspot.name,
          hour,
          weekday,
          event_type: 'unplanned',
        })
        setPredictions((prev) => ({
          ...prev,
          [hotspot.id]: result,
        }))
      } catch (error) {
        console.error(`Failed to predict risk for ${hotspot.name}:`, error)
      }
    })
  }, [hotspots, predict])

  const getRiskColor = (score: number) => {
    if (score >= 80) return 'bg-red-100 text-red-800 border-red-300'
    if (score >= 60) return 'bg-orange-100 text-orange-800 border-orange-300'
    if (score >= 40) return 'bg-yellow-100 text-yellow-800 border-yellow-300'
    return 'bg-green-100 text-green-800 border-green-300'
  }

  const getRiskIcon = (score: number) => {
    if (score >= 80) return <AlertTriangle className="h-4 w-4" />
    if (score >= 60) return <AlertCircle className="h-4 w-4" />
    return <TrendingUp className="h-4 w-4" />
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {hotspots.map((hotspot) => {
        const prediction = predictions[hotspot.id]
        const riskScore = prediction?.risk_score ?? hotspot.risk_score ?? 0
        const riskLevel = prediction?.risk_level ?? 'unknown'

        return (
          <Card key={hotspot.id} className={`border ${getRiskColor(riskScore)}`}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <CardTitle className="text-base">{hotspot.name}</CardTitle>
                {getRiskIcon(riskScore)}
              </div>
              <CardDescription>Risk Level: {riskLevel}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Risk Score</span>
                  <span className="text-xl font-bold">{riskScore.toFixed(1)}</span>
                </div>
                <div className="w-full bg-gray-300 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      riskScore >= 80
                        ? 'bg-red-600'
                        : riskScore >= 60
                          ? 'bg-orange-600'
                          : riskScore >= 40
                            ? 'bg-yellow-600'
                            : 'bg-green-600'
                    }`}
                    style={{ width: `${riskScore}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
