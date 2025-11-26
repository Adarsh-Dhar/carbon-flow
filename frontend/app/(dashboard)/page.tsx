"use client"

import { useState, Suspense } from "react"
import { useQuery } from "@tanstack/react-query"
import { Sidebar } from "@/components/dashboard/sidebar"
import { HeroBar } from "@/components/dashboard/hero-bar"
import { KPIGrid } from "@/components/dashboard/kpi-grid"
import { SensorMap } from "@/components/dashboard/sensor-map"
import { AgentTabs } from "@/components/dashboard/agent-tabs"
import { RightSidebar } from "@/components/dashboard/right-sidebar"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { getStatus, getForecastLatest, getSensorsLatest, getAgentHistory, getForecastHistory } from "@/lib/api"

function DashboardContent() {

  // Queries hit live API and surface empty states if unavailable
  const statusQuery = useQuery({
    queryKey: ["status"],
    queryFn: getStatus,
    retry: 1,
  })

  const forecastQuery = useQuery({
    queryKey: ["forecast"],
    queryFn: getForecastLatest,
    retry: 1,
  })

  const sensorsQuery = useQuery({
    queryKey: ["sensors"],
    queryFn: getSensorsLatest,
    retry: 1,
  })

  const historyQuery = useQuery({
    queryKey: ["agent-history"],
    queryFn: getAgentHistory,
    retry: 1,
  })

  const trendsQuery = useQuery({
    queryKey: ["forecast-history"],
    queryFn: () => getForecastHistory(7),
    retry: 1,
  })

  const statusError = statusQuery.isError || (!statusQuery.isLoading && !statusQuery.data)
  const forecastError = forecastQuery.isError || (!forecastQuery.isLoading && !forecastQuery.data)
  const sensorsError = sensorsQuery.isError || (!sensorsQuery.isLoading && !sensorsQuery.data)
  const historyError = historyQuery.isError
  const trendsError = trendsQuery.isError

  const isLoading = statusQuery.isLoading || forecastQuery.isLoading || sensorsQuery.isLoading
  const showGlobalError = statusError || forecastError || sensorsError

  return (
    <div className="flex min-h-screen bg-background">
      {/* Left Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 ml-[72px] mr-80 p-6">
        <div className="max-w-[1400px] mx-auto">
          {showGlobalError && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>
                Live data could not be loaded from the API ({process.env.NEXT_PUBLIC_API_BASE_URL || "unknown host"}).
                Check that the FastAPI server is running and reachable, then refresh.
              </AlertDescription>
            </Alert>
          )}
          <HeroBar
            status={statusQuery.data}
            isLoading={statusQuery.isLoading}
            hasError={statusError}
          />

          <KPIGrid
            forecast={forecastQuery.data}
            sensors={sensorsQuery.data}
            isLoading={isLoading}
            hasError={forecastError || sensorsError}
          />

          <SensorMap
            sensors={sensorsQuery.data}
            forecast={forecastQuery.data}
            isLoading={sensorsQuery.isLoading}
            hasError={sensorsError}
          />

          <AgentTabs
            forecast={forecastQuery.data}
            history={historyQuery.data}
            trendData={trendsQuery.data}
            isLoading={isLoading}
            forecastError={forecastError}
            historyError={historyError}
            trendsError={trendsError}
          />
        </div>
      </main>

      {/* Right Sidebar */}
      <RightSidebar status={statusQuery.data} isLoading={statusQuery.isLoading} hasError={statusError} />
    </div>
  )
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen bg-background">Loading...</div>}>
      <DashboardContent />
    </Suspense>
  )
}
