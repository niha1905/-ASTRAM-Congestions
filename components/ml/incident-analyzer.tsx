'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { useIncidentAnalysis } from '@/hooks/use-ml-predictions'
import { AlertCircle, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react'

export function IncidentAnalyzer() {
  const { data, loading, error, analyze } = useIncidentAnalysis()
  const [formData, setFormData] = useState({
    event_type: 'unplanned',
    zone: 'Central Zone 2',
    corridor: 'CBD 2',
    priority: 'High',
    hour: 21,
    duration_min: 45,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await analyze({
      ...formData,
      hour: parseInt(formData.hour as unknown as string),
      duration_min: parseInt(formData.duration_min as unknown as string),
    })
  }

  return (
    <div className="grid gap-6">
      {/* Input Form */}
      <Card>
        <CardHeader>
          <CardTitle>Incident Analysis</CardTitle>
          <CardDescription>Predict closure probability and resource needs</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Event Type</Label>
                <Select
                  value={formData.event_type}
                  onValueChange={(value) =>
                    value && setFormData({ ...formData, event_type: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="planned">Planned</SelectItem>
                    <SelectItem value="unplanned">Unplanned</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Priority</Label>
                <Select
                  value={formData.priority}
                  onValueChange={(value) =>
                    value && setFormData({ ...formData, priority: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Low">Low</SelectItem>
                    <SelectItem value="High">High</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Zone</Label>
                <Input
                  value={formData.zone}
                  onChange={(e) => setFormData({ ...formData, zone: e.target.value })}
                  placeholder="e.g., Central Zone 2"
                />
              </div>

              <div className="space-y-2">
                <Label>Corridor</Label>
                <Input
                  value={formData.corridor}
                  onChange={(e) => setFormData({ ...formData, corridor: e.target.value })}
                  placeholder="e.g., CBD 2"
                />
              </div>

              <div className="space-y-2">
                <Label>Hour (0-23)</Label>
                <Input
                  type="number"
                  value={formData.hour}
                  onChange={(e) => setFormData({ ...formData, hour: parseInt(e.target.value) })}
                  min="0"
                  max="23"
                />
              </div>

              <div className="space-y-2">
                <Label>Duration (minutes)</Label>
                <Input
                  type="number"
                  value={formData.duration_min}
                  onChange={(e) =>
                    setFormData({ ...formData, duration_min: parseInt(e.target.value) })
                  }
                  min="0"
                />
              </div>
            </div>

            <Button type="submit" disabled={loading} className="w-full">
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Analyze Incident
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-800">Error</p>
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {data && (
        <div className="grid grid-cols-2 gap-4">
          {/* Closure Prediction */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Closure Probability</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {data.closure?.success ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Probability:</span>
                    <span className="text-2xl font-bold">
                      {data.closure.closure_probability}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        data.closure.closure_probability >= 70
                          ? 'bg-red-600'
                          : data.closure.closure_probability >= 50
                            ? 'bg-yellow-500'
                            : 'bg-green-500'
                      }`}
                      style={{
                        width: `${data.closure.closure_probability}%`,
                      }}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    {data.closure.will_close ? (
                      <>
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                        <span className="text-sm font-semibold text-red-600">
                          Road likely to close
                        </span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                        <span className="text-sm font-semibold text-green-600">
                          Road likely to remain open
                        </span>
                      </>
                    )}
                  </div>
                  <div className="bg-gray-100 p-2 rounded text-xs">
                    Risk Level: <span className="font-semibold capitalize">{data.closure.risk_level}</span>
                  </div>
                </>
              ) : (
                <p className="text-sm text-gray-500">Unable to predict closure</p>
              )}
            </CardContent>
          </Card>

          {/* Resource Deployment */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Resource Deployment</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {data.resources?.success ? (
                <>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Officers Needed</p>
                    <p className="text-3xl font-bold text-blue-600">
                      {data.resources.officers_needed}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Barricades Needed</p>
                    <p className="text-3xl font-bold text-orange-600">
                      {data.resources.barricades_needed}
                    </p>
                  </div>
                  <div className="bg-blue-50 p-3 rounded">
                    <p className="text-xs text-blue-700">
                      Total Resources: <span className="font-bold">{data.resources.total_resources}</span>
                    </p>
                  </div>
                </>
              ) : (
                <p className="text-sm text-gray-500">Unable to predict resources</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
