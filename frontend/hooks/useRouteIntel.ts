"use client"

import { useEffect, useState } from "react"

import { getRouteIntelligence } from "@/lib/api"
import type { RouteIntelligence } from "@/lib/types"

interface UseRouteIntelOptions {
  start: [number, number]
  end: [number, number]
  sensitivity?: string
}

export function useRouteIntel({ start, end, sensitivity = "asthma" }: UseRouteIntelOptions) {
  const [data, setData] = useState<RouteIntelligence | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)
    getRouteIntelligence({ start, end, sensitivity })
      .then((payload) => {
        if (!cancelled) {
          setData(payload)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error("Failed to fetch route intelligence"))
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [start[0], start[1], end[0], end[1], sensitivity])

  return { data, isLoading, error }
}
