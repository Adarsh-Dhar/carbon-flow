"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import mapboxgl from "mapbox-gl"
import { ArrowUpRight, Check, Droplets, Route as RouteIcon, Shield, Wind } from "lucide-react"
import { Card, Metric, Text } from "@tremor/react"

import { AgentBadge } from "@/components/AgentBadge"
import { BiometricTicker } from "@/components/BiometricTicker"
import { StatusPill } from "@/components/StatusPill"
import { useMockAgents } from "@/hooks/useMockAgents"
import { useMockVitals } from "@/hooks/useMockVitals"
import { useRouteIntel } from "@/hooks/useRouteIntel"
import { getPurpleAirSensors } from "@/lib/api"
import type { MeteorologyContext, RouteRecommendation } from "@/lib/types"

const zoneGradients: Record<"green" | "yellow" | "red", string> = {
  green: "zone-green-gradient",
  yellow: "zone-yellow-gradient",
  red: "zone-red-gradient",
}

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN
const SF_ORIGIN: [number, number] = [37.7749, -122.4194]
const SF_DESTINATION: [number, number] = [37.8079, -122.4177]

interface SensorMapProps {
  origin: [number, number]
  destination: [number, number]
  route?: RouteRecommendation
  meteorology?: MeteorologyContext
  isLoading: boolean
  error?: Error | null
}

function SensorMap({ origin, destination, route, meteorology, isLoading, error }: SensorMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const markersRef = useRef<{ start?: mapboxgl.Marker; end?: mapboxgl.Marker }>({})
  const [mapReady, setMapReady] = useState(false)
  const [purpleAirData, setPurpleAirData] = useState<GeoJSON.FeatureCollection | null>(null)

  useEffect(() => {
    if (!MAPBOX_TOKEN || mapRef.current || !containerRef.current) return
    mapboxgl.accessToken = MAPBOX_TOKEN
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: [origin[1], origin[0]],
      zoom: 12,
    })
    map.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), "top-right")
    map.on("load", () => {
      setMapReady(true)
      if (!map.getSource("aqi-hotspots")) {
        map.addSource("aqi-hotspots", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        })
        map.addLayer({
          id: "aqi-heat",
          type: "heatmap",
          source: "aqi-hotspots",
          paint: {
            "heatmap-weight": [
              "interpolate",
              ["linear"],
              ["get", "aqi"],
              0,
              0,
              50,
              0.2,
              100,
              0.5,
              150,
              0.8,
              200,
              1,
            ],
            "heatmap-intensity": 1.1,
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0,
              "rgba(33,102,172,0)",
              0.2,
              "rgb(56,189,248)",
              0.4,
              "rgb(129,140,248)",
              0.6,
              "rgb(249,115,22)",
              0.8,
              "rgb(244,63,94)",
              1,
              "rgb(234,88,12)",
            ],
            "heatmap-radius": 45,
            "heatmap-opacity": 0.75,
          },
        })
      }
    })
    mapRef.current = map
    return () => map.remove()
  }, [])

  // Fetch PurpleAir sensor data
  useEffect(() => {
    getPurpleAirSensors()
      .then((data) => {
        setPurpleAirData(data)
      })
      .catch((err) => {
        console.error("Failed to fetch PurpleAir sensors:", err)
      })
  }, [])

  useEffect(() => {
    if (!mapRef.current) return
    mapRef.current.flyTo({ center: [origin[1], origin[0]], zoom: 12, essential: false })
  }, [origin])

  useEffect(() => {
    if (!mapReady || !mapRef.current || !route) return
    const map = mapRef.current

    // Validate route data structure
    if (!route.cleanest_route || !route.fastest_route) {
      console.warn("Route data missing cleanest_route or fastest_route")
      return
    }

    if (!route.cleanest_route.geometry || !route.fastest_route.geometry) {
      console.warn("Route geometry missing")
      return
    }

    if (route.cleanest_route.geometry.type !== "LineString" || route.fastest_route.geometry.type !== "LineString") {
      console.warn("Route geometry type is not LineString")
      return
    }

    // Validate coordinates format [lon, lat]
    const validateCoordinates = (coords: [number, number][]): boolean => {
      if (!Array.isArray(coords) || coords.length === 0) return false
      return coords.every(
        (coord) =>
          Array.isArray(coord) &&
          coord.length === 2 &&
          typeof coord[0] === "number" &&
          typeof coord[1] === "number" &&
          coord[0] >= -180 &&
          coord[0] <= 180 &&
          coord[1] >= -90 &&
          coord[1] <= 90
      )
    }

    const cleanestCoords = route.cleanest_route.geometry.coordinates as [number, number][]
    const fastestCoords = route.fastest_route.geometry.coordinates as [number, number][]

    if (!validateCoordinates(cleanestCoords) || !validateCoordinates(fastestCoords)) {
      console.warn("Invalid route coordinates format")
      return
    }

    // Clean up existing route layers and sources
    try {
      if (map.getLayer("clean-route-line")) {
        map.removeLayer("clean-route-line")
      }
      if (map.getSource("clean-route")) {
        map.removeSource("clean-route")
      }
      if (map.getLayer("fast-route-line")) {
        map.removeLayer("fast-route-line")
      }
      if (map.getSource("fast-route")) {
        map.removeSource("fast-route")
      }
    } catch (error) {
      console.warn("Error cleaning up existing route layers:", error)
    }

    // Helper function to add or update route line
    const upsertLine = (
      sourceId: string,
      layerId: string,
      data: RouteRecommendation["cleanest_route"],
      paint: mapboxgl.LinePaint,
    ) => {
      try {
        // Add source
        map.addSource(sourceId, {
          type: "geojson",
          data: data as GeoJSON.Feature,
        })

        // Add layer - without beforeLayerId, it will be added on top of all layers
        // This ensures routes are visible above the heatmap
        map.addLayer({
          id: layerId,
          type: "line",
          source: sourceId,
          layout: { "line-cap": "round", "line-join": "round" },
          paint,
        })

        console.log(`Route layer ${layerId} added successfully`)
      } catch (error) {
        console.error(`Error adding route layer ${layerId}:`, error)
      }
    }

    // Add cleanest route (green, solid line) - rendered first so fastest route appears on top
    upsertLine("clean-route", "clean-route-line", route.cleanest_route, {
      "line-color": "#10b981",
      "line-width": 6,
      "line-opacity": 0.95,
      "line-blur": 0.5,
    })

    // Add fastest route (orange, dashed line) - rendered second so it appears on top
    upsertLine("fast-route", "fast-route-line", route.fastest_route, {
      "line-color": "#f97316",
      "line-width": 4,
      "line-opacity": 0.9,
      "line-dasharray": [1.5, 1.2],
    })

    // Update markers
    try {
      if (markersRef.current.start) markersRef.current.start.remove()
      if (markersRef.current.end) markersRef.current.end.remove()

      markersRef.current.start = new mapboxgl.Marker({ color: "#22d3ee" })
        .setLngLat([origin[1], origin[0]]) // Convert [lat, lon] to [lon, lat]
        .setPopup(new mapboxgl.Popup({ closeButton: false }).setText("Origin"))
        .addTo(map)

      markersRef.current.end = new mapboxgl.Marker({ color: "#f97316" })
        .setLngLat([destination[1], destination[0]]) // Convert [lat, lon] to [lon, lat]
        .setPopup(new mapboxgl.Popup({ closeButton: false }).setText("Destination"))
        .addTo(map)
    } catch (error) {
      console.error("Error updating markers:", error)
    }
  }, [mapReady, route, origin, destination])

  // Update heatmap with real PurpleAir sensor data
  useEffect(() => {
    if (!mapReady || !mapRef.current || !purpleAirData) return
    const map = mapRef.current

    const heatSource = map.getSource("aqi-hotspots") as mapboxgl.GeoJSONSource | undefined
    if (heatSource && purpleAirData.features.length > 0) {
      // Use real PurpleAir sensor data
      heatSource.setData(purpleAirData)
    }
  }, [mapReady, purpleAirData])

  if (!MAPBOX_TOKEN) {
    return (
      <div className="flex h-full min-h-[360px] items-end justify-between rounded-3xl border border-white/10 bg-[url(/heatmap-visualization-blue-orange.jpg)] bg-cover bg-center p-6">
        <div className="rounded-2xl bg-black/60 px-4 py-3 text-sm text-white">
          Add <span className="font-semibold">NEXT_PUBLIC_MAPBOX_TOKEN</span> to render live routes.
        </div>
        <ArrowUpRight className="h-6 w-6 text-white/70" />
      </div>
    )
  }

  const healthDelta = route ? (route.health_delta * 100).toFixed(1) : "--"
  const wind = meteorology?.wind
  const pollenRisk = meteorology?.adjustments?.pollen_risk ?? (route?.adjustments.pollen_penalty ? "High" : "Low")

  return (
    <div className="relative min-h-[360px] overflow-hidden rounded-3xl border border-white/10 bg-black/30">
      <div ref={containerRef} className="h-full min-h-[360px] w-full" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-black/20 to-black/70" />

      {isLoading && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/30 backdrop-blur-sm text-sm text-white/90">
          <div className="rounded-2xl border border-white/10 bg-black/60 px-6 py-3 shadow-lg">
            Computing cleaner path...
          </div>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="rounded-2xl border border-red-500/50 bg-red-950/60 px-6 py-3 text-sm text-red-200 shadow-lg">
            <p className="font-semibold">Failed to load route</p>
            <p className="mt-1 text-xs text-red-300/80">{error.message}</p>
          </div>
        </div>
      )}

      {route && (
        <>
          <div className="absolute top-4 left-4 z-10 max-w-md rounded-2xl border border-white/10 bg-black/60 p-4 text-white shadow-2xl backdrop-blur">
            <p className="text-xs uppercase tracking-[0.4em] text-white/50">Respiratory savings</p>
            <h3 className="mt-1 text-3xl font-semibold">{healthDelta}% cleaner</h3>
            <p className="mt-2 text-sm text-white/80">{route.explanation}</p>
          </div>

          <div className="absolute top-4 right-4 z-10 flex flex-col gap-3">
            <div
              className="flex items-center gap-3 rounded-2xl border border-white/10 bg-black/60 px-4 py-3 text-white shadow-lg"
              style={{ transform: `rotate(${wind?.direction_deg ?? 0}deg)` }}
            >
              <Wind className="h-5 w-5 text-cyan-300" />
              <div className="text-xs leading-tight">
                <p className="text-white/60">Wind Breaker</p>
                <p className="text-sm font-semibold">{wind ? `${wind.speed_kmh?.toFixed(1)} km/h` : "--"}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-black/60 px-4 py-3 text-white shadow-lg">
              <Droplets className="h-5 w-5 text-sky-300" />
              <div className="text-xs leading-tight">
                <p className="text-white/60">Fog Guard</p>
                <p className="text-sm font-semibold">{route.adjustments.fog_guard ? "Active" : "Standby"}</p>
              </div>
            </div>
          </div>

          <div className="absolute bottom-4 left-4 right-4 z-10 grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-black/60 p-4 text-white">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-white/50">
                <RouteIcon className="h-4 w-4 text-emerald-300" />
                Clean Path
              </div>
              <p className="mt-2 text-2xl font-semibold">
                {route.stats.cleanest_minutes ? `${route.stats.cleanest_minutes.toFixed(1)} min` : "--"}
              </p>
              <p className="text-sm text-white/70">Avg AQI {route.stats.cleanest_aqi.toFixed(0)}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/40 p-4 text-white">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-white/50">
                <RouteIcon className="h-4 w-4 text-orange-300" />
                Fast Path
              </div>
              <p className="mt-2 text-2xl font-semibold">
                {route.stats.fastest_minutes ? `${route.stats.fastest_minutes.toFixed(1)} min` : "--"}
              </p>
              <p className="text-sm text-white/70">Avg AQI {route.stats.fastest_aqi.toFixed(0)}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/60 p-4 text-white">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-white/50">
                <Shield className="h-4 w-4 text-rose-300" />
                Calendar Sentry
              </div>
              <p className="mt-2 text-2xl font-semibold">{pollenRisk.toString()}</p>
              <p className="text-sm text-white/70">
                {route.adjustments.pollen_penalty ? "Pollen detour in effect" : "No pollen detour"}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const { breathability, headline, subcopy, interventions, sensorData } = useMockAgents()
  const vitals = useMockVitals()
  const { data: routeIntel, isLoading: routeLoading, error: routeError } = useRouteIntel({
    start: SF_ORIGIN,
    end: SF_DESTINATION,
  })

  const gradient = useMemo(() => zoneGradients[breathability.sentiment], [breathability.sentiment])

  return (
    <div className="min-h-screen bg-[#020618] text-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10">
        <section className={`relative overflow-hidden rounded-[32px] p-8 shadow-[0_40px_120px_rgba(0,0,0,0.45)] ${gradient}`}>
          <div className="calm-grid absolute inset-0"></div>
          <div className="relative z-10 flex flex-col gap-6">
            <AgentBadge agent="Sentry" />
            <div className="flex flex-wrap items-end justify-between gap-6">
              <div>
                <p className="text-xs uppercase tracking-[0.5em] text-white/70">Breathability</p>
                <h1 className="text-4xl font-semibold">{headline}</h1>
                <p className="mt-2 max-w-3xl text-lg text-white/80">{subcopy}</p>
              </div>
              <StatusPill
                label={`Risk score ${(breathability.risk_score * 100).toFixed(0)}%`}
                tone={breathability.sentiment}
              />
            </div>
            <BiometricTicker metrics={vitals} />
            <div className="flex flex-wrap gap-3">
              {interventions.map((intervention) => (
                <div key={intervention.id} className="flex min-w-[180px] flex-1 items-center gap-3 rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10">
                    <Check className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold">{intervention.label}</p>
                    <p className="text-xs text-white/70">
                      {intervention.status} • {intervention.since}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
          <div className="space-y-6">
            <SensorMap
              origin={routeIntel?.origin ?? SF_ORIGIN}
              destination={routeIntel?.destination ?? SF_DESTINATION}
              route={routeIntel?.route}
              meteorology={routeIntel?.meteorology}
              isLoading={routeLoading}
              error={routeError}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <Card className="bg-slate-900/60 text-left text-white">
                <Text className="text-xs uppercase tracking-[0.4em] text-slate-400">AQI (PM2.5)</Text>
                <Metric className="mt-1 text-4xl">{sensorData.air_quality.aqi}</Metric>
                <Text className="mt-2 text-sm text-slate-300">{sensorData.air_quality.category}</Text>
              </Card>
              <Card className="bg-slate-900/60 text-left text-white">
                <Text className="text-xs uppercase tracking-[0.4em] text-slate-400">Pollen Risk</Text>
                <Metric className="mt-1 text-4xl">{sensorData.pollen.overall_risk}</Metric>
                <Text className="mt-2 text-sm text-slate-300">
                  Grass {sensorData.pollen.grass_pollen} • Tree {sensorData.pollen.tree_pollen}
                </Text>
              </Card>
              <Card className="bg-slate-900/60 text-left text-white sm:col-span-2">
                <Text className="text-xs uppercase tracking-[0.4em] text-slate-400">Agentic reroute</Text>
                <Metric className="mt-1 text-2xl">
                  {routeIntel?.route?.explanation ?? "Cartographer is computing the cleanest corridor…"}
                </Metric>
                <div className="mt-4 flex flex-wrap gap-2 text-xs">
                  <span
                    className={`rounded-full border px-3 py-1 ${
                      routeIntel?.route?.adjustments?.wind_bias ? "border-emerald-400 text-emerald-200" : "border-white/10 text-white/60"
                    }`}
                  >
                    Wind Breaker {routeIntel?.route?.adjustments?.wind_bias ? "On" : "Idle"}
                  </span>
                  <span
                    className={`rounded-full border px-3 py-1 ${
                      routeIntel?.route?.adjustments?.fog_guard ? "border-sky-400 text-sky-200" : "border-white/10 text-white/60"
                    }`}
                  >
                    Fog Guard {routeIntel?.route?.adjustments?.fog_guard ? "Active" : "Standby"}
                  </span>
                  <span
                    className={`rounded-full border px-3 py-1 ${
                      routeIntel?.route?.adjustments?.pollen_penalty ? "border-rose-400 text-rose-200" : "border-white/10 text-white/60"
                    }`}
                  >
                    Calendar Sentry {routeIntel?.route?.adjustments?.pollen_penalty ? "Rescheduling" : "Monitoring"}
                  </span>
                </div>
              </Card>
            </div>
          </div>

          <Card className="rounded-3xl border-white/5 bg-slate-950/80 text-white shadow-2xl">
            <Text className="text-xs uppercase tracking-[0.6em] text-slate-400">Clinical Playbook</Text>
            <h3 className="mt-3 text-2xl font-semibold">{breathability.recommendations.zone_description}</h3>
            <ul className="mt-4 space-y-3 text-sm text-slate-200">
              {breathability.recommendations.actions.map((action) => (
                <li key={action} className="flex items-start gap-2">
                  <span className="mt-1 h-2 w-2 rounded-full bg-emerald-400" />
                  {action}
                </li>
              ))}
            </ul>
            <div className="mt-6 rounded-2xl border border-white/10 bg-slate-900/40 p-4 text-xs uppercase tracking-[0.3em] text-slate-400">
              Monitoring
              <ul className="mt-3 list-disc space-y-1 pl-5 normal-case tracking-normal text-sm text-slate-200">
                {breathability.recommendations.monitoring.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </Card>
        </section>
      </div>
    </div>
  )
}