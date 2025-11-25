"use client"

import { TrendingUp, TrendingDown, Flame, Wheat, Clock } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { getAQICategory, AQI_CATEGORIES } from "@/lib/types"
import type { ForecastLatest, SensorData } from "@/lib/types"

interface KPIGridProps {
  forecast: ForecastLatest | undefined
  sensors: SensorData | undefined
  isLoading: boolean
  hasError?: boolean
}

export function KPIGrid({ forecast, sensors, isLoading, hasError = false }: KPIGridProps) {
  const hasSensorData = Boolean(sensors?.cpcb_data?.length)
  const hasForecastData = Boolean(forecast?.prediction)

  const avgAQI = hasSensorData
    ? Math.round(sensors!.cpcb_data.reduce((acc, s) => acc + s.aqi, 0) / sensors!.cpcb_data.length)
    : null

  const aqiCategory = avgAQI !== null ? getAQICategory(avgAQI) : null
  const aqiConfig = aqiCategory ? AQI_CATEGORIES[aqiCategory] : null

  const fireCount = hasSensorData ? sensors?.nasa_data?.length || 0 : null
  const stubblePercent = hasForecastData ? forecast?.prediction?.data_sources?.stubble_burning_percent ?? 0 : null

  const getStubbleBadge = (percent: number) => {
    if (percent < 15) return { label: "Normal", className: "bg-success/20 text-success" }
    if (percent < 30) return { label: "High", className: "bg-warning/20 text-warning" }
    return { label: "Critical", className: "bg-destructive/20 text-destructive" }
  }

  const stubbleBadge = stubblePercent !== null ? getStubbleBadge(stubblePercent) : null

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="glass-card p-5">
            <Skeleton className="h-4 w-24 mb-3" />
            <Skeleton className="h-8 w-16 mb-2" />
            <Skeleton className="h-3 w-20" />
          </Card>
        ))}
      </div>
    )
  }

  if (!isLoading && (hasError || (!hasSensorData && !hasForecastData))) {
    return (
      <Card className="glass-card p-8 mb-6 text-center">
        <h3 className="text-lg font-semibold text-foreground mb-2">No live KPI data found</h3>
        <p className="text-sm text-muted-foreground">
          The API did not return any forecast or sensor readings. Verify that the agents and FastAPI server are running.
        </p>
      </Card>
    )
  }

  const aqiDisplay = !hasError && avgAQI !== null ? avgAQI : "ERR"
  const fireDisplay = !hasError && fireCount !== null ? fireCount : "ERR"
  const stubbleDisplay =
    !hasError && stubblePercent !== null ? `${stubblePercent.toFixed(1)}%` : hasError ? "ERR" : "Awaiting data"
  const predictionBadge =
    !hasError && forecast?.prediction ? (
      <Badge
        className="text-sm font-semibold"
        style={{
          backgroundColor: AQI_CATEGORIES[forecast.prediction.aqi_category].color,
          color: "#fff",
        }}
      >
        {forecast.prediction.aqi_category}
      </Badge>
    ) : (
      <Badge className="text-sm font-semibold bg-destructive text-white">ERR</Badge>
    )

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* Delhi Avg AQI */}
      <Card
        className="glass-card p-5 relative overflow-hidden"
        style={{ borderLeft: `4px solid ${aqiConfig?.color || "#475569"}` }}
      >
        <div
          className="absolute inset-0 opacity-10"
          style={{ background: `linear-gradient(135deg, ${aqiConfig?.color || "#475569"}40 0%, transparent 60%)` }}
        />
        <div className="relative">
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-1">Delhi Avg AQI</p>
          <div className="flex items-baseline gap-2">
            <span
              className="text-3xl font-bold"
              style={{ color: aqiConfig?.color || (hasError ? "#ef4444" : "#64748b") }}
            >
              {aqiDisplay}
            </span>
            {aqiCategory && !hasError ? (
              <Badge className={`${aqiConfig?.bg} text-white text-xs`}>{aqiCategory}</Badge>
            ) : (
              hasError && <Badge className="bg-destructive text-white text-xs">ERR</Badge>
            )}
          </div>
          <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
            <TrendingUp className="h-3 w-3 text-destructive" />
            <span>{hasError ? "API error" : "Live reading"}</span>
          </div>
        </div>
      </Card>

      {/* Active Farm Fires */}
      <Card className="glass-card p-5">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-1">Active Farm Fires</p>
        {fireCount !== null && !hasError ? (
          <>
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-bold text-orange">{fireCount}</span>
              <Flame className="h-5 w-5 text-orange" />
            </div>
            <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
              <TrendingDown className="h-3 w-3 text-success" />
              <span>Detected via NASA FIRMS</span>
            </div>
          </>
        ) : (
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-bold text-destructive">{fireDisplay}</span>
            <Flame className="h-5 w-5 text-orange" />
          </div>
        )}
      </Card>

      {/* Stubble Contribution */}
      <Card className="glass-card p-5">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-1">Stubble Contribution</p>
        {stubblePercent !== null && stubbleBadge && !hasError ? (
          <>
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-bold text-foreground">{stubblePercent.toFixed(1)}%</span>
              <Badge className={stubbleBadge.className}>{stubbleBadge.label}</Badge>
            </div>
            <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
              <Wheat className="h-3 w-3" />
              <span>of pollution attributed to burning</span>
            </div>
          </>
        ) : (
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-bold text-destructive">{stubbleDisplay}</span>
            <Badge className="bg-destructive/20 text-destructive">ERR</Badge>
          </div>
        )}
      </Card>

      {/* Next 24h Prediction */}
      <Card className="glass-card p-5">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-1">Next 24h Prediction</p>
        <div className="flex items-center justify-between">
          {forecast?.prediction && !hasError ? (
            <>
              <div>
                {predictionBadge}
                <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  <span>ETA: {forecast.prediction.eta_hours || 0}h</span>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted-foreground mb-1">Confidence</p>
                <div className="w-24">
                  <Progress value={forecast.prediction.confidence_level} className="h-2" />
                </div>
                <p className="text-xs font-medium text-foreground mt-1">{forecast.prediction.confidence_level}%</p>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-between w-full">
              {predictionBadge}
              <span className="text-sm text-destructive font-semibold">ERR</span>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
