"use client"

import { useState, useEffect, useMemo } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { MapPin, Flame, Wind, Eye, EyeOff } from "lucide-react"
import { getAQICategory, getAQIColor, AQI_CATEGORIES, type AQICategory } from "@/lib/types"
import type { SensorData, ForecastLatest } from "@/lib/types"
import "leaflet/dist/leaflet.css"

interface SensorMapProps {
  sensors: SensorData | undefined
  forecast: ForecastLatest | undefined
  isLoading: boolean
  hasError?: boolean
}

export function SensorMap({ sensors, forecast, isLoading, hasError = false }: SensorMapProps) {
  const router = useRouter()
  const searchParams = useSearchParams()

  const [showFires, setShowFires] = useState(searchParams.get("fires") !== "false")
  const [showSurgesOnly, setShowSurgesOnly] = useState(searchParams.get("surges") === "true")
  const [categoryFilter, setCategoryFilter] = useState<string>(searchParams.get("category") || "all")
  const [leafletLib, setLeafletLib] = useState<typeof import("react-leaflet") | null>(null)

  useEffect(() => {
    let isMounted = true
    ;(async () => {
      const module = await import("react-leaflet")
      if (isMounted) {
        setLeafletLib(module)
      }
    })()
    return () => {
      isMounted = false
    }
  }, [])

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

  const hasStations = Boolean(filteredStations.length)
  const hasFires = Boolean(sensors?.nasa_data?.length)

  const avgAQI =
    sensors?.cpcb_data?.length && hasStations
      ? Math.round(sensors.cpcb_data.reduce((acc, s) => acc + s.aqi, 0) / sensors.cpcb_data.length)
      : null
  const avgAQIColor = avgAQI !== null ? getAQIColor(avgAQI) : "#94a3b8"

  const windDirection = forecast?.prediction?.data_sources?.avg_wind_direction_24h_deg
  const windSpeed = forecast?.prediction?.data_sources?.avg_wind_speed_24h_kmh
  const delhiCenter: [number, number] = [28.6139, 77.209]

  const stationMarkers = useMemo(
    () =>
      filteredStations.filter(
        (station) =>
          typeof station.lat === "number" &&
          !Number.isNaN(station.lat) &&
          typeof station.lon === "number" &&
          !Number.isNaN(station.lon),
      ),
    [filteredStations],
  )

  const fireMarkers = useMemo(
    () =>
      sensors?.nasa_data?.filter(
        (fire) =>
          typeof fire.lat === "number" &&
          !Number.isNaN(fire.lat) &&
          typeof fire.lon === "number" &&
          !Number.isNaN(fire.lon),
      ) ?? [],
    [sensors?.nasa_data],
  )

  if (!isLoading && (hasError || (!hasStations && !hasFires))) {
    return (
      <Card className="glass-card p-8 mb-6 text-center">
        <h3 className="text-lg font-semibold text-foreground mb-2">Sensor feed error</h3>
        <p className="text-sm text-muted-foreground">{hasError ? "ERR" : "No telemetry available."}</p>
      </Card>
    )
  }

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
      <Card className="glass-card p-0 overflow-hidden relative" style={{ height: 520 }}>
        <div className="absolute inset-0">
          {leafletLib ? (
            <leafletLib.MapContainer
              center={delhiCenter}
              zoom={11}
              scrollWheelZoom
              className="h-full w-full"
              zoomControl={false}
              attributionControl={false}
            >
              <leafletLib.TileLayer
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> & Carto'
              />
              <leafletLib.LayerGroup>
                {stationMarkers.map((station) => {
                  const radius = Math.max(8, Math.min(25, station.aqi / 8))
                  const color = getAQIColor(station.aqi)
                  return (
                    <leafletLib.CircleMarker
                      key={station.station}
                      center={[station.lat, station.lon]}
                      radius={radius}
                      pathOptions={{
                        color,
                        weight: 2,
                        fillColor: color,
                        fillOpacity: 0.35,
                      }}
                    >
                      <leafletLib.Popup>
                        <div className="space-y-1 text-sm">
                          <p className="font-semibold text-foreground">{station.station}</p>
                          <p>
                            AQI: <span className="font-medium">{station.aqi}</span>
                          </p>
                          <p>PM2.5: {station.pm25 ?? "--"} µg/m³</p>
                          <p>PM10: {station.pm10 ?? "--"} µg/m³</p>
                          <p>
                            Updated:{" "}
                            {station.timestamp ? new Date(station.timestamp).toLocaleTimeString() : "N/A"}
                          </p>
                        </div>
                      </leafletLib.Popup>
                    </leafletLib.CircleMarker>
                  )
                })}
              </leafletLib.LayerGroup>

              {showFires && fireMarkers.length > 0 && (
                <leafletLib.LayerGroup>
                  {fireMarkers.map((fire, index) => (
                    <leafletLib.CircleMarker
                      key={`fire-${fire.lat}-${fire.lon}-${index}`}
                      center={[fire.lat, fire.lon]}
                      radius={5}
                      className="pulse-fire"
                      pathOptions={{
                        color: "#ef4444",
                        fillColor: "#ef4444",
                        fillOpacity: 0.9,
                      }}
                    />
                  ))}
                </leafletLib.LayerGroup>
              )}
            </leafletLib.MapContainer>
          ) : (
            <div className="flex h-full w-full items-center justify-center text-muted-foreground">Initializing map...</div>
          )}
        </div>

        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-background/40 to-background/80 z-10" />

        {/* Wind Arrow */}
        {windDirection !== undefined && windSpeed !== undefined && (
          <div
            className="absolute bottom-6 right-6 z-20 flex items-center gap-2 glass rounded-lg px-4 py-2"
            style={{ transform: `rotate(${windDirection}deg)` }}
          >
            <Wind className="h-5 w-5 text-primary" />
            <span className="text-sm font-medium text-foreground">{windSpeed.toFixed(1)} km/h</span>
          </div>
        )}

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
            <span className="font-semibold ml-1" style={{ color: avgAQIColor }}>
              {avgAQI ?? "--"}
            </span>
          </Badge>
        </div>
      </div>
    </div>
  )
}
