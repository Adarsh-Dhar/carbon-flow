"use client"

import { useState, useCallback } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

interface UseAgentActionOptions<T> {
  actionFn: () => Promise<T>
  queryKeysToInvalidate?: string[]
  successMessage?: string
  errorMessage?: string
  onSuccess?: (data: T) => void
  onError?: (error: Error) => void
}

export function useAgentAction<T>({
  actionFn,
  queryKeysToInvalidate = [],
  successMessage = "Action completed successfully",
  errorMessage = "Action failed",
  onSuccess,
  onError,
}: UseAgentActionOptions<T>) {
  const queryClient = useQueryClient()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [data, setData] = useState<T | null>(null)

  const execute = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await actionFn()
      setData(result)

      // Invalidate relevant queries
      for (const key of queryKeysToInvalidate) {
        queryClient.invalidateQueries({ queryKey: [key] })
      }

      toast.success(successMessage)
      onSuccess?.(result)
      return result
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Unknown error")
      setError(error)
      toast.error(errorMessage, { description: error.message })
      onError?.(error)
      throw error
    } finally {
      setIsLoading(false)
    }
  }, [actionFn, queryKeysToInvalidate, successMessage, errorMessage, onSuccess, onError, queryClient])

  const reset = useCallback(() => {
    setIsLoading(false)
    setError(null)
    setData(null)
  }, [])

  return { execute, isLoading, error, data, reset }
}
