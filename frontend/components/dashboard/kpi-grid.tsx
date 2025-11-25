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
}

export function KPIGrid({ forecast, sensors, isLoading }: KPIGridProps) {
  const avgAQI = sensors?.cpcb_data?.length
    ? Math.round(sensors.cpcb_data.reduce((acc, s) => acc + s.aqi, 0) / sensors.cpcb_data.length)
    : 0

  const aqiCategory = getAQICategory(avgAQI)
  const aqiConfig = AQI_CATEGORIES[aqiCategory]

  const fireCount = sensors?.nasa_data?.length || 0
  const stubblePercent = forecast?.prediction?.data_sources?.stubble_burning_percent || 0

  const getStubbleBadge = (percent: number) => {
    if (percent < 15) return { label: "Normal", className: "bg-success/20 text-success" }
    if (percent < 30) return { label: "High", className: "bg-warning/20 text-warning" }
    return { label: "Critical", className: "bg-destructive/20 text-destructive" }
  }

  const stubbleBadge = getStubbleBadge(stubblePercent)

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

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* Delhi Avg AQI */}
      <Card className="glass-card p-5 relative overflow-hidden" style={{ borderLeft: `4px solid ${aqiConfig.color}` }}>
        <div
          className="absolute inset-0 opacity-10"
          style={{ background: `linear-gradient(135deg, ${aqiConfig.color}40 0%, transparent 60%)` }}
        />
        <div className="relative">
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-1">Delhi Avg AQI</p>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold" style={{ color: aqiConfig.color }}>
              {avgAQI}
            </span>
            <Badge className={`${aqiConfig.bg} text-white text-xs`}>{aqiCategory}</Badge>
          </div>
          <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
            <TrendingUp className="h-3 w-3 text-destructive" />
            <span>+12 from yesterday</span>
          </div>
        </div>
      </Card>

      {/* Active Farm Fires */}
      <Card className="glass-card p-5">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-1">Active Farm Fires</p>
        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-bold text-orange">{fireCount}</span>
          <Flame className="h-5 w-5 text-orange" />
        </div>
        <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
          <TrendingDown className="h-3 w-3 text-success" />
          <span>-8 from rolling avg</span>
        </div>
      </Card>

      {/* Stubble Contribution */}
      <Card className="glass-card p-5">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-1">Stubble Contribution</p>
        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-bold text-foreground">{stubblePercent.toFixed(1)}%</span>
          <Badge className={stubbleBadge.className}>{stubbleBadge.label}</Badge>
        </div>
        <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
          <Wheat className="h-3 w-3" />
          <span>of pollution attributed to burning</span>
        </div>
      </Card>

      {/* Next 24h Prediction */}
      <Card className="glass-card p-5">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-1">Next 24h Prediction</p>
        <div className="flex items-center justify-between">
          <div>
            <Badge
              className="text-sm font-semibold"
              style={{
                backgroundColor: forecast?.prediction
                  ? AQI_CATEGORIES[forecast.prediction.aqi_category].color
                  : "#64748b",
                color: "#fff",
              }}
            >
              {forecast?.prediction?.aqi_category || "Unknown"}
            </Badge>
            <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>ETA: {forecast?.prediction?.eta_hours || 0}h</span>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground mb-1">Confidence</p>
            <div className="w-24">
              <Progress value={forecast?.prediction?.confidence_level || 0} className="h-2" />
            </div>
            <p className="text-xs font-medium text-foreground mt-1">{forecast?.prediction?.confidence_level || 0}%</p>
          </div>
        </div>
      </Card>
    </div>
  )
}
