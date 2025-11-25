"use client"

import { useState, useEffect } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { MapPin, Flame, Wind, Eye, EyeOff } from "lucide-react"
import { getAQICategory, getAQIColor, AQI_CATEGORIES, type AQICategory } from "@/lib/types"
import type { SensorData, ForecastLatest } from "@/lib/types"

interface SensorMapProps {
  sensors: SensorData | undefined
  forecast: ForecastLatest | undefined
  isLoading: boolean
}

// Simulated map component (Leaflet would be used in production)
export function SensorMap({ sensors, forecast, isLoading }: SensorMapProps) {
  const router = useRouter()
  const searchParams = useSearchParams()

  const [showFires, setShowFires] = useState(searchParams.get("fires") !== "false")
  const [showSurgesOnly, setShowSurgesOnly] = useState(searchParams.get("surges") === "true")
  const [categoryFilter, setCategoryFilter] = useState<string>(searchParams.get("category") || "all")

  // Update URL params when filters change
  useEffect(() => {
    const params = new URLSearchParams()
    if (!showFires) params.set("fires", "false")
    if (showSurgesOnly) params.set("surges", "true")
    if (categoryFilter !== "all") params.set("category", categoryFilter)

    const newUrl = params.toString() ? `?${params.toString()}` : "/"
    router.replace(newUrl, { scroll: false })
  }, [showFires, showSurgesOnly, categoryFilter, router])

  const filteredStations =
    sensors?.cpcb_data?.filter((station) => {
      if (categoryFilter !== "all" && getAQICategory(station.aqi) !== categoryFilter) {
        return false
      }
      if (showSurgesOnly && station.aqi < 300) {
        return false
      }
      return true
    }) || []

  const avgAQI = sensors?.cpcb_data?.length
    ? Math.round(sensors.cpcb_data.reduce((acc, s) => acc + s.aqi, 0) / sensors.cpcb_data.length)
    : 0

  const windDirection = forecast?.prediction?.data_sources?.avg_wind_direction_24h_deg || 0
  const windSpeed = forecast?.prediction?.data_sources?.avg_wind_speed_24h_kmh || 0

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-foreground">Sensor Intelligence</h2>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <Button
            variant={showFires ? "default" : "outline"}
            size="sm"
            onClick={() => setShowFires(!showFires)}
            className="gap-2"
          >
            <Flame className="h-4 w-4" />
            NASA Fires
          </Button>
          <Button
            variant={showSurgesOnly ? "default" : "outline"}
            size="sm"
            onClick={() => setShowSurgesOnly(!showSurgesOnly)}
            className="gap-2"
          >
            {showSurgesOnly ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
            Surges Only
          </Button>
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="AQI Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {(Object.keys(AQI_CATEGORIES) as AQICategory[]).map((cat) => (
                <SelectItem key={cat} value={cat}>
                  {cat}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Map Container */}
      <Card className="glass-card p-0 overflow-hidden relative" style={{ height: 600 }}>
        {/* Simulated Map Background */}
        <div
          className="absolute inset-0 bg-cover bg-center opacity-40"
          style={{
            backgroundImage: `url('/delhi-satellite-map-dark.jpg')`,
            filter: "saturate(0.5) brightness(0.6)",
          }}
        />

        {/* Map Overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/30 to-background/60" />

        {/* Station Markers */}
        <div className="absolute inset-0 p-8">
          {filteredStations.map((station, index) => {
            const size = Math.max(20, Math.min(50, station.aqi / 10))
            const color = getAQIColor(station.aqi)
            // Distribute stations visually
            const left = 15 + (index % 5) * 18 + Math.random() * 5
            const top = 15 + Math.floor(index / 5) * 20 + Math.random() * 5

            return (
              <div
                key={station.station}
                className="absolute group cursor-pointer transition-transform hover:scale-110 z-10"
                style={{
                  left: `${left}%`,
                  top: `${top}%`,
                  transform: "translate(-50%, -50%)",
                }}
              >
                <div
                  className="rounded-full flex items-center justify-center shadow-lg"
                  style={{
                    width: size,
                    height: size,
                    backgroundColor: `${color}40`,
                    border: `2px solid ${color}`,
                    boxShadow: `0 0 20px ${color}40`,
                  }}
                >
                  <span className="text-xs font-bold text-white">{station.aqi}</span>
                </div>

                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity z-20">
                  <Card className="glass p-3 min-w-[180px]">
                    <p className="font-semibold text-sm text-foreground mb-1">{station.station}</p>
                    <div className="space-y-1 text-xs text-muted-foreground">
                      <p>
                        AQI: <span className="text-foreground font-medium">{station.aqi}</span>
                      </p>
                      <p>
                        PM2.5: <span className="text-foreground">{station.pm25} µg/m³</span>
                      </p>
                      <p>
                        PM10: <span className="text-foreground">{station.pm10} µg/m³</span>
                      </p>
                      <p>Updated: {new Date(station.timestamp).toLocaleTimeString()}</p>
                    </div>
                  </Card>
                </div>
              </div>
            )
          })}

          {/* Fire Hotspots */}
          {showFires &&
            sensors?.nasa_data?.map((fire, index) => {
              const left = 60 + (index % 4) * 8 + Math.random() * 3
              const top = 10 + Math.floor(index / 4) * 15 + Math.random() * 5

              return (
                <div
                  key={`fire-${index}`}
                  className="absolute pulse-fire z-5"
                  style={{
                    left: `${left}%`,
                    top: `${top}%`,
                    transform: "translate(-50%, -50%)",
                  }}
                >
                  <div className="w-3 h-3 rounded-full bg-red-500 shadow-lg shadow-red-500/50" />
                </div>
              )
            })}

          {/* Wind Arrow */}
          <div
            className="absolute bottom-6 right-6 flex items-center gap-2 glass rounded-lg px-4 py-2"
            style={{ transform: `rotate(${windDirection}deg)` }}
          >
            <Wind className="h-5 w-5 text-primary" />
            <span className="text-sm font-medium text-foreground">{windSpeed.toFixed(1)} km/h</span>
          </div>
        </div>

        {/* Legend */}
        <Card className="absolute top-4 left-4 glass p-4 z-20">
          <p className="text-xs font-semibold text-foreground mb-3 uppercase tracking-wider">AQI Legend</p>
          <div className="space-y-2">
            {(Object.entries(AQI_CATEGORIES) as [AQICategory, (typeof AQI_CATEGORIES)[AQICategory]][]).map(
              ([category, config]) => (
                <div key={category} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: config.color }} />
                  <span className="text-xs text-muted-foreground">{category}</span>
                  <span className="text-xs text-muted-foreground/60">
                    ({config.min}-{config.max})
                  </span>
                </div>
              ),
            )}
          </div>
          <div className="border-t border-border mt-3 pt-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500 pulse-fire" />
              <span className="text-xs text-muted-foreground">Fire Hotspot</span>
            </div>
          </div>
        </Card>
      </Card>

      {/* Stats Footer */}
      <div className="flex items-center gap-6 mt-4">
        <div className="flex items-center gap-2">
          <MapPin className="h-4 w-4 text-primary" />
          <span className="text-sm text-muted-foreground">AQI Stations:</span>
          <span className="text-sm font-semibold text-foreground">{filteredStations.length}</span>
        </div>
        <div className="flex items-center gap-2">
          <Flame className="h-4 w-4 text-orange" />
          <span className="text-sm text-muted-foreground">Active Fires:</span>
          <span className="text-sm font-semibold text-foreground">{sensors?.nasa_data?.length || 0}</span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            Avg AQI:{" "}
            <span className="font-semibold ml-1" style={{ color: getAQIColor(avgAQI) }}>
              {avgAQI}
            </span>
          </Badge>
        </div>
      </div>
    </div>
  )
}
