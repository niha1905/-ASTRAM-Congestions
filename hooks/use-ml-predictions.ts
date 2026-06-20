/**
 * useMLPrediction Hook
 * React hook for making ML predictions from components
 */

'use client'

import { useState, useCallback, useRef } from 'react'
import { mlApiClient } from '@/lib/ml-api-client'

export interface UsePredictionState {
  data: any
  loading: boolean
  error: string | null
}

export function useIncidentVolumePrediction() {
  const [state, setState] = useState<UsePredictionState>({
    data: null,
    loading: false,
    error: null,
  })

  const predict = useCallback(
    async (params: {
      zone: string
      corridor: string
      event_type: string
      hour: number
      weekday: number
      month: number
    }) => {
      setState({ data: null, loading: true, error: null })
      try {
        const result = await mlApiClient.predictIncidentVolume(params)
        setState({ data: result, loading: false, error: null })
        return result
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error'
        setState({ data: null, loading: false, error: errorMsg })
        throw error
      }
    },
    []
  )

  return { ...state, predict }
}

export function useClosurePrediction() {
  const [state, setState] = useState<UsePredictionState>({
    data: null,
    loading: false,
    error: null,
  })

  const predict = useCallback(
    async (params: {
      event_type: string
      zone: string
      corridor: string
      priority: string
      hour: number
      duration_min: number
    }) => {
      setState({ data: null, loading: true, error: null })
      try {
        const result = await mlApiClient.predictClosure(params)
        setState({ data: result, loading: false, error: null })
        return result
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error'
        setState({ data: null, loading: false, error: errorMsg })
        throw error
      }
    },
    []
  )

  return { ...state, predict }
}

export function useResourcePrediction() {
  const [state, setState] = useState<UsePredictionState>({
    data: null,
    loading: false,
    error: null,
  })

  const predict = useCallback(
    async (params: {
      event_type: string
      priority: string
      zone: string
      corridor: string
      hour: number
      closure_prob?: number
    }) => {
      setState({ data: null, loading: true, error: null })
      try {
        const result = await mlApiClient.predictResources(params)
        setState({ data: result, loading: false, error: null })
        return result
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error'
        setState({ data: null, loading: false, error: errorMsg })
        throw error
      }
    },
    []
  )

  return { ...state, predict }
}

export function useHotspotRiskPrediction() {
  const [state, setState] = useState<UsePredictionState>({
    data: null,
    loading: false,
    error: null,
  })

  const predict = useCallback(
    async (params: {
      junction: string
      hour: number
      weekday: number
      event_type: string
    }) => {
      setState({ data: null, loading: true, error: null })
      try {
        const result = await mlApiClient.predictHotspotRisk(params)
        setState({ data: result, loading: false, error: null })
        return result
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error'
        setState({ data: null, loading: false, error: errorMsg })
        throw error
      }
    },
    []
  )

  return { ...state, predict }
}

export function useScenarioPrediction() {
  const [state, setState] = useState<UsePredictionState>({
    data: null,
    loading: false,
    error: null,
  })

  const predict = useCallback(
    async (params: { base_scenario: string; perturbation: string }) => {
      setState({ data: null, loading: true, error: null })
      try {
        const result = await mlApiClient.predictScenario(params)
        setState({ data: result, loading: false, error: null })
        return result
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error'
        setState({ data: null, loading: false, error: errorMsg })
        throw error
      }
    },
    []
  )

  return { ...state, predict }
}

export function useIncidentAnalysis() {
  const [state, setState] = useState<UsePredictionState>({
    data: null,
    loading: false,
    error: null,
  })

  const analyze = useCallback(
    async (incident: {
      event_type: string
      zone: string
      corridor: string
      priority: string
      hour: number
      duration_min: number
    }) => {
      setState({ data: null, loading: true, error: null })
      try {
        const result = await mlApiClient.analyzeIncident(incident)
        setState({ data: result, loading: false, error: null })
        return result
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error'
        setState({ data: null, loading: false, error: errorMsg })
        throw error
      }
    },
    []
  )

  return { ...state, analyze }
}

// Hook for batch predictions
export function useBatchPrediction() {
  const [state, setState] = useState<UsePredictionState>({
    data: null,
    loading: false,
    error: null,
  })

  const predict = useCallback(
    async (requests: Array<{ type: string; params: any }>) => {
      setState({ data: null, loading: true, error: null })
      try {
        const result = await mlApiClient.batchPredict(requests)
        setState({ data: result, loading: false, error: null })
        return result
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error'
        setState({ data: null, loading: false, error: errorMsg })
        throw error
      }
    },
    []
  )

  return { ...state, predict }
}
