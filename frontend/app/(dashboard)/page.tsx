"use client"

import { useEffect, useMemo, useRef } from "react"
import mapboxgl from "mapbox-gl"
import { ArrowUpRight, Check } from "lucide-react"
import { Card, Metric, Text } from "@tremor/react"

import { AgentBadge } from "@/components/AgentBadge"
import { BiometricTicker } from "@/components/BiometricTicker"
import { StatusPill } from "@/components/StatusPill"
import { useMockAgents } from "@/hooks/useMockAgents"
import { useMockVitals } from "@/hooks/useMockVitals"

const zoneGradients: Record<"green" | "yellow" | "red", string> = {
  green: "zone-green-gradient",
  yellow: "zone-yellow-gradient",
  red: "zone-red-gradient",
}

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN

function SensorMap({
  latitude,
  longitude,
  intensity,
}: {
  latitude: number
  longitude: number
  intensity: number
}) {
  const ref = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!MAPBOX_TOKEN || !ref.current) return

    mapboxgl.accessToken = MAPBOX_TOKEN
    const map = new mapboxgl.Map({
      container: ref.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: [longitude, latitude],
      zoom: 11,
    })

    map.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), "top-right")

    map.on("load", () => {
      const features = Array.from({ length: 6 }).map((_, idx) => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [longitude + idx * 0.02, latitude + idx * 0.01],
        },
        properties: {
          aqi: intensity + idx * 8,
        },
      }))

      map.addSource("aqi-hotspots", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features,
        },
      })

      map.addLayer({
        id: "aqi-heat",
        type: "heatmap",
        source: "aqi-hotspots",
        paint: {
          "heatmap-weight": ["interpolate", ["linear"], ["get", "aqi"], 0, 0, 300, 1],
          "heatmap-intensity": 1.2,
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(33,102,172,0)",
            0.2,
            "rgb(103,169,207)",
            0.4,
            "rgb(209,229,240)",
            0.6,
            "rgb(253,219,199)",
            0.8,
            "rgb(239,138,98)",
            1,
            "rgb(178,24,43)",
          ],
          "heatmap-radius": 40,
          "heatmap-opacity": 0.8,
        },
      })

      map.addLayer({
        id: "aqi-circle",
        type: "circle",
        source: "aqi-hotspots",
        paint: {
          "circle-radius": 6,
          "circle-color": [
            "interpolate",
            ["linear"],
            ["get", "aqi"],
            0,
            "#22c55e",
            100,
            "#facc15",
            200,
            "#ef4444",
          ],
          "circle-opacity": 0.9,
        },
      })
    })

    return () => map.remove()
  }, [latitude, longitude, intensity])

  if (!MAPBOX_TOKEN) {
    return (
      <div className="flex h-full min-h-[320px] items-end justify-between rounded-3xl border border-white/10 bg-[url(/heatmap-visualization-blue-orange.jpg)] bg-cover bg-center p-6">
        <div className="rounded-2xl bg-black/60 px-4 py-3 text-sm text-white">
          Add <span className="font-semibold">NEXT_PUBLIC_MAPBOX_TOKEN</span> to view live heatmaps.
        </div>
        <ArrowUpRight className="h-6 w-6 text-white/70" />
      </div>
    )
  }

  return <div ref={ref} className="h-full min-h-[320px] rounded-3xl border border-white/10" />
}

export default function DashboardPage() {
  const { breathability, headline, subcopy, interventions, sensorData } = useMockAgents()
  const vitals = useMockVitals()

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
              latitude={sensorData.air_quality.location.latitude}
              longitude={sensorData.air_quality.location.longitude}
              intensity={sensorData.air_quality.aqi}
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