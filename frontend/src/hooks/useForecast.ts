/**
 * Forecast API Hooks
 */

import { useState, useCallback } from 'react'
import { graphqlRequest, MUTATIONS, PredictionResult, DecompositionResult } from '@/lib/graphql'

interface UsePredictReturn {
  result: PredictionResult | null
  loading: boolean
  error: string | null
  predict: (
    modelId: string,
    inputData: Record<string, unknown>,
    options?: { includeContributions?: boolean; includeConfidenceIntervals?: boolean }
  ) => Promise<PredictionResult | null>
  reset: () => void
}

interface PredictResponse {
  predict: PredictionResult
}

export function usePredict(): UsePredictReturn {
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const predict = useCallback(async (
    modelId: string,
    inputData: Record<string, unknown>,
    options: { includeContributions?: boolean; includeConfidenceIntervals?: boolean } = {}
  ): Promise<PredictionResult | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<PredictResponse>(
        MUTATIONS.PREDICT,
        {
          input: {
            modelId,
            inputData,
            includeContributions: options.includeContributions ?? true,
            includeConfidenceIntervals: options.includeConfidenceIntervals ?? true,
          }
        }
      )
      setResult(data.predict)
      return data.predict
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate prediction')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return { result, loading, error, predict, reset }
}

interface UseDecomposeReturn {
  result: DecompositionResult | null
  loading: boolean
  error: string | null
  decompose: (modelId: string, startDate?: string, endDate?: string) => Promise<DecompositionResult | null>
  reset: () => void
}

interface DecomposeResponse {
  decomposeContributions: DecompositionResult
}

export function useDecompose(): UseDecomposeReturn {
  const [result, setResult] = useState<DecompositionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const decompose = useCallback(async (
    modelId: string,
    startDate?: string,
    endDate?: string
  ): Promise<DecompositionResult | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<DecomposeResponse>(
        MUTATIONS.DECOMPOSE_CONTRIBUTIONS,
        {
          input: {
            modelId,
            startDate,
            endDate,
          }
        }
      )
      setResult(data.decomposeContributions)
      return data.decomposeContributions
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to decompose contributions')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return { result, loading, error, decompose, reset }
}
