import { useEffect, useRef, useCallback } from 'react'

/**
 * Custom React hook for polling API endpoints
 * 
 * @param fetchFn - Function that returns a Promise (the fetch call)
 * @param interval - Polling interval in milliseconds (default: 30000 = 30 seconds)
 * @param enabled - Whether polling is enabled (default: true)
 * @returns Object with manual refresh function
 */
export function usePolling(
  fetchFn: () => void | Promise<void>,
  interval: number = 30000,
  enabled: boolean = true
) {
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const isMountedRef = useRef(true)
  const fetchFnRef = useRef(fetchFn)

  // Keep fetchFn ref up to date
  useEffect(() => {
    fetchFnRef.current = fetchFn
  }, [fetchFn])

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  const executeFetch = useCallback(() => {
    if (isMountedRef.current) {
      fetchFnRef.current()
    }
  }, [])

  useEffect(() => {
    if (!enabled) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    // Initial fetch
    executeFetch()

    // Set up polling interval
    intervalRef.current = setInterval(executeFetch, interval)

    // Cleanup on unmount or when dependencies change
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [executeFetch, interval, enabled])

  return {
    refresh: executeFetch
  }
}

