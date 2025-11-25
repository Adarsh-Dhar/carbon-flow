"use client"

import { useState, Suspense } from "react"
import { useQuery } from "@tanstack/react-query"
import { Sidebar } from "@/components/dashboard/sidebar"
import { HeroBar } from "@/components/dashboard/hero-bar"
import { KPIGrid } from "@/components/dashboard/kpi-grid"
import { SensorMap } from "@/components/dashboard/sensor-map"
import { AgentTabs } from "@/components/dashboard/agent-tabs"
import { RightSidebar } from "@/components/dashboard/right-sidebar"
import { EnforcementModal } from "@/components/dashboard/enforcement-modal"
import { getStatus, getForecastLatest, getSensorsLatest, getAgentHistory, getForecastHistory } from "@/lib/api"

// Mock data fallbacks for when API is not available
const mockStatus = {
  status: "operational" as const,
  last_run: new Date().toISOString(),
  cycle_duration_seconds: 127,
  agents: {
    sensor_ingest: { last_run: new Date(Date.now() - 5 * 60000).toISOString(), status: "available" as const },
    forecast: { last_run: new Date(Date.now() - 10 * 60000).toISOString(), status: "available" as const },
    enforcement: { last_run: null, status: "available" as const },
    accountability: { last_run: new Date(Date.now() - 180 * 60000).toISOString(), status: "available" as const },
  },
}

const mockForecast = {
  prediction: {
    aqi_category: "Very Poor" as const,
    confidence_level: 86,
    reasoning:
      "High stubble burning activity detected in Punjab/Haryana with northwesterly winds carrying pollutants towards Delhi NCR. Combined with low wind speeds and temperature inversion, AQI is expected to deteriorate further.",
    data_sources: {
      cpcb_aqi: 312,
      nasa_fire_count: 47,
      stubble_burning_percent: 23.5,
      avg_wind_direction_24h_deg: 315,
      avg_wind_speed_24h_kmh: 8.2,
    },
    timestamp: new Date().toISOString(),
    predicted_aqi: 342,
    eta_hours: 18,
  },
  artifacts: ["aqi_forecast.json", "fire_correlation.png", "wind_analysis.pdf"],
}

const mockSensors = {
  cpcb_data: [
    {
      station: "Anand Vihar",
      aqi: 385,
      pm25: 245,
      pm10: 312,
      lat: 28.6469,
      lon: 77.3164,
      timestamp: new Date().toISOString(),
      category: "Very Poor",
    },
    {
      station: "ITO",
      aqi: 298,
      pm25: 178,
      pm10: 234,
      lat: 28.6289,
      lon: 77.2405,
      timestamp: new Date().toISOString(),
      category: "Poor",
    },
    {
      station: "Punjabi Bagh",
      aqi: 342,
      pm25: 198,
      pm10: 267,
      lat: 28.6683,
      lon: 77.1167,
      timestamp: new Date().toISOString(),
      category: "Very Poor",
    },
    {
      station: "RK Puram",
      aqi: 276,
      pm25: 156,
      pm10: 198,
      lat: 28.5651,
      lon: 77.1767,
      timestamp: new Date().toISOString(),
      category: "Poor",
    },
    {
      station: "Dwarka",
      aqi: 234,
      pm25: 134,
      pm10: 178,
      lat: 28.5921,
      lon: 77.046,
      timestamp: new Date().toISOString(),
      category: "Poor",
    },
    {
      station: "Nehru Nagar",
      aqi: 312,
      pm25: 189,
      pm10: 245,
      lat: 28.5706,
      lon: 77.2507,
      timestamp: new Date().toISOString(),
      category: "Very Poor",
    },
    {
      station: "Shadipur",
      aqi: 289,
      pm25: 167,
      pm10: 212,
      lat: 28.6519,
      lon: 77.1583,
      timestamp: new Date().toISOString(),
      category: "Poor",
    },
    {
      station: "Siri Fort",
      aqi: 256,
      pm25: 145,
      pm10: 189,
      lat: 28.5494,
      lon: 77.2156,
      timestamp: new Date().toISOString(),
      category: "Poor",
    },
  ],
  nasa_data: Array.from({ length: 47 }, (_, i) => ({
    lat: 30.5 + Math.random() * 1.5,
    lon: 74.5 + Math.random() * 2,
    brightness: 300 + Math.random() * 100,
    confidence: 70 + Math.random() * 30,
    timestamp: new Date().toISOString(),
  })),
  dss_data: {
    stubble_burning_percent: 23.5,
    affected_area_km2: 1245,
    timestamp: new Date().toISOString(),
  },
}

function DashboardContent() {
  const [enforcementModalOpen, setEnforcementModalOpen] = useState(false)

  // Queries with fallback to mock data
  const statusQuery = useQuery({
    queryKey: ["status"],
    queryFn: getStatus,
    placeholderData: mockStatus,
    retry: 1,
  })

  const forecastQuery = useQuery({
    queryKey: ["forecast"],
    queryFn: getForecastLatest,
    placeholderData: mockForecast,
    retry: 1,
  })

  const sensorsQuery = useQuery({
    queryKey: ["sensors"],
    queryFn: getSensorsLatest,
    placeholderData: mockSensors,
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

  const isLoading = statusQuery.isLoading || forecastQuery.isLoading || sensorsQuery.isLoading

  return (
    <div className="flex min-h-screen bg-background">
      {/* Left Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 ml-[72px] mr-80 p-6">
        <div className="max-w-[1400px] mx-auto">
          <HeroBar
            status={statusQuery.data}
            isLoading={statusQuery.isLoading}
            onEnforcementClick={() => setEnforcementModalOpen(true)}
          />

          <KPIGrid forecast={forecastQuery.data} sensors={sensorsQuery.data} isLoading={isLoading} />

          <SensorMap sensors={sensorsQuery.data} forecast={forecastQuery.data} isLoading={sensorsQuery.isLoading} />

          <AgentTabs
            forecast={forecastQuery.data}
            history={historyQuery.data}
            trendData={trendsQuery.data}
            isLoading={isLoading}
            onEnforcementClick={() => setEnforcementModalOpen(true)}
          />
        </div>
      </main>

      {/* Right Sidebar */}
      <RightSidebar status={statusQuery.data} isLoading={statusQuery.isLoading} />

      {/* Enforcement Modal */}
      <EnforcementModal
        open={enforcementModalOpen}
        onOpenChange={setEnforcementModalOpen}
        forecast={forecastQuery.data}
      />
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
