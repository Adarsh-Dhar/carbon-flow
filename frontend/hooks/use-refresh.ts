"use client"

import { useEffect, useState, useCallback } from "react"
import { useQueryClient } from "@tanstack/react-query"

export type RefreshInterval = 15 | 30 | 60 | 120 | 300

export function useRefresh(enabled: boolean, interval: RefreshInterval) {
  const queryClient = useQueryClient()
  const [countdown, setCountdown] = useState(interval)

  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["status"] })
    queryClient.invalidateQueries({ queryKey: ["forecast"] })
    queryClient.invalidateQueries({ queryKey: ["sensors"] })
    queryClient.invalidateQueries({ queryKey: ["logs"] })
    queryClient.invalidateQueries({ queryKey: ["agent-history"] })
    setCountdown(interval)
  }, [queryClient, interval])

  useEffect(() => {
    if (!enabled) {
      setCountdown(interval)
      return
    }

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          refresh()
          return interval
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [enabled, interval, refresh])

  return { countdown, refresh }
}
