'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useClosurePrediction, useResourcePrediction } from '@/hooks/use-ml-predictions'
import { AlertTriangle, CheckCircle2, AlertCircle } from 'lucide-react'

/**
 * Example: Integrating ML predictions into Event Analysis page
 * This shows how to use ML hooks in existing components
 */
export function EventAnalysisWithML() {
  const [eventData, setEventData] = useState({
    event_type: 'unplanned',
    zone: 'Central Zone 2',
    corridor: 'CBD 2',
    priority: 'High',
    hour: 14,
    duration_min: 45,
  })

  const { data: closureData, loading: closureLoading, predict: predictClosure } = useClosurePrediction()
  const { data: resourcesData, loading: resourcesLoading, predict: predictResources } = useResourcePrediction()

  const handleAnalyze = async () => {
    // Get closure prediction first
    const closure = await predictClosure({
      event_type: eventData.event_type,
      zone: eventData.zone,
      corridor: eventData.corridor,
      priority: eventData.priority,
      hour: eventData.hour,
      duration_min: eventData.duration_min,
    })

    // Then get resource prediction
    await predictResources({
      event_type: eventData.event_type,
      priority: eventData.priority,
      zone: eventData.zone,
      corridor: eventData.corridor,
      hour: eventData.hour,
      closure_prob: closure?.closure_probability || 0,
    })
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Event Analysis with ML Predictions</CardTitle>
          <CardDescription>Real-time incident analysis and resource optimization</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Event Details */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">Event Type</p>
              <p className="font-semibold">{eventData.event_type}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Priority</p>
              <Badge variant={eventData.priority === 'High' ? 'destructive' : 'secondary'}>
                {eventData.priority}
              </Badge>
            </div>
            <div>
              <p className="text-sm text-gray-600">Zone</p>
              <p className="font-semibold">{eventData.zone}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Corridor</p>
              <p className="font-semibold">{eventData.corridor}</p>
            </div>
          </div>

          <Button
            onClick={handleAnalyze}
            disabled={closureLoading || resourcesLoading}
            className="w-full"
          >
            {closureLoading || resourcesLoading ? 'Analyzing...' : 'Run ML Analysis'}
          </Button>

          {/* Results Grid */}
          {(closureData || resourcesData) && (
            <div className="grid grid-cols-2 gap-4 pt-4 border-t">
              {/* Closure Prediction */}
              {closureData && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    {closureData.will_close ? (
                      <AlertTriangle className="h-5 w-5 text-red-600" />
                    ) : (
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    )}
                    <span className="font-semibold">Closure Risk</span>
                  </div>
                  <div className="text-2xl font-bold">{closureData.closure_probability}%</div>
                  <div className="w-full bg-gray-200 rounded h-2">
                    <div
                      className={`h-2 rounded ${
                        closureData.closure_probability >= 70
                          ? 'bg-red-600'
                          : closureData.closure_probability >= 50
                            ? 'bg-yellow-500'
                            : 'bg-green-500'
                      }`}
                      style={{ width: `${closureData.closure_probability}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Resource Needs */}
              {resourcesData && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-5 w-5 text-blue-600" />
                    <span className="font-semibold">Resources Needed</span>
                  </div>
                  <div className="flex gap-4">
                    <div>
                      <p className="text-xs text-gray-600">Officers</p>
                      <p className="text-xl font-bold text-blue-600">
                        {resourcesData.officers_needed}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600">Barricades</p>
                      <p className="text-xl font-bold text-orange-600">
                        {resourcesData.barricades_needed}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Usage Example */}
      <Card className="bg-blue-50">
        <CardHeader>
          <CardTitle className="text-sm">How to Use This Component</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-2">
          <p>1. Import the hooks: `useClosurePrediction`, `useResourcePrediction`</p>
          <p>2. Call `predict()` with incident parameters</p>
          <p>3. Access predictions from returned `data` object</p>
          <p>4. Use loading state to show progress</p>
          <p>5. Display results to users for decision making</p>
        </CardContent>
      </Card>
    </div>
  )
}

export default EventAnalysisWithML
