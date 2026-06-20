'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'
import { mlApiClient } from '@/lib/ml-api-client'

export function MLHealthCheck() {
  const [health, setHealth] = useState<any>(null)
  const [models, setModels] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const healthData = await mlApiClient.getHealth()
        const modelsData = await mlApiClient.getModelsStatus()

        setHealth(healthData)
        setModels(modelsData)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to check health')
        setHealth(null)
        setModels(null)
      } finally {
        setLoading(false)
      }
    }

    checkHealth()
    // Recheck every 30 seconds
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Checking ML backend...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          ML Backend Unavailable: {error}
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          ML Backend Status
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div>
          <p className="text-gray-600">Service Status</p>
          <p className="font-semibold">{health?.status || 'Unknown'}</p>
        </div>
        {models && (
          <div>
            <p className="text-gray-600">Models Loaded</p>
            <p className="font-semibold">{models.count || 0}</p>
            {models.models && models.models.length > 0 && (
              <div className="mt-2 space-y-1">
                {models.models.map((model: string) => (
                  <div key={model} className="flex items-center gap-2 text-xs">
                    <CheckCircle2 className="h-3 w-3 text-green-600" />
                    <span>{model}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
