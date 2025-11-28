"use client"

import { useEffect, useState } from "react"

import type { BiometricMetric } from "@/lib/mockData"
import { mockBiometrics } from "@/lib/mockData"

export function useMockVitals(pollInterval = 5000) {
  const [metrics, setMetrics] = useState<BiometricMetric[]>(mockBiometrics)

  useEffect(() => {
    const timer = setInterval(() => {
      setMetrics((current) =>
        current.map((metric) => {
          const drift = metric.trend
          const jitter = Number((Math.random() * 1.5).toFixed(1))
          const direction = Math.random() > 0.5 ? 1 : -1
          return {
            ...metric,
            value: Math.max(0, Math.round(metric.value + direction * jitter + drift * 0.05)),
          }
        }),
      )
    }, pollInterval)

    return () => clearInterval(timer)
  }, [pollInterval])

  return metrics
}

