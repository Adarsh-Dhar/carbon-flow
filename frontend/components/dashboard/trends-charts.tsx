"use client"

import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"
import type { ForecastHistoryEntry } from "@/lib/types"

interface TrendsChartsProps {
  data: ForecastHistoryEntry[] | undefined
  isLoading: boolean
  hasError?: boolean
}

export function TrendsCharts({ data, isLoading, hasError = false }: TrendsChartsProps) {
  const chartData = data ?? []

  const formattedData = chartData.map((d) => ({
    ...d,
    date: new Date(d.timestamp).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }),
  }))

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <Card key={i} className="glass-card p-5">
            <Skeleton className="h-4 w-24 mb-4" />
            <Skeleton className="h-48 w-full" />
          </Card>
        ))}
      </div>
    )
  }

  if (hasError) {
    return (
      <Card className="glass-card p-8 text-center">
        <h3 className="text-lg font-semibold text-foreground mb-2">Trend history unavailable</h3>
        <p className="text-sm text-destructive font-semibold">ERR</p>
      </Card>
    )
  }

  if (!isLoading && chartData.length === 0) {
    return (
      <Card className="glass-card p-8 text-center">
        <h3 className="text-lg font-semibold text-foreground mb-2">No trend data available</h3>
        <p className="text-sm text-muted-foreground">
          Historical forecasts are required to render these charts. Once the forecast agent runs multiple cycles, trends
          will appear automatically.
        </p>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* AQI Trend */}
      <Card className="glass-card p-5">
        <h3 className="font-semibold text-foreground mb-4">AQI Trend (7 Days)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={formattedData}>
            <defs>
              <linearGradient id="aqiGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 10 }} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} domain={[0, 500]} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                color: "#f8fafc",
              }}
            />
            <ReferenceLine
              y={200}
              stroke="#eab308"
              strokeDasharray="5 5"
              label={{ value: "Moderate", fill: "#eab308", fontSize: 10 }}
            />
            <ReferenceLine
              y={300}
              stroke="#ef4444"
              strokeDasharray="5 5"
              label={{ value: "Poor", fill: "#ef4444", fontSize: 10 }}
            />
            <Area type="monotone" dataKey="aqi" stroke="#f97316" fill="url(#aqiGradient)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      {/* Fire Count Trend */}
      <Card className="glass-card p-5">
        <h3 className="font-semibold text-foreground mb-4">Fire Count (7 Days)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={formattedData}>
            <defs>
              <linearGradient id="fireGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 10 }} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                color: "#f8fafc",
              }}
            />
            <ReferenceLine y={50} stroke="#eab308" strokeDasharray="5 5" />
            <Area type="monotone" dataKey="fire_count" stroke="#ef4444" fill="url(#fireGradient)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      {/* Stubble Percentage Trend */}
      <Card className="glass-card p-5">
        <h3 className="font-semibold text-foreground mb-4">Stubble % (7 Days)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={formattedData}>
            <defs>
              <linearGradient id="stubbleGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 10 }} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} domain={[0, 50]} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                color: "#f8fafc",
              }}
            />
            <ReferenceLine
              y={15}
              stroke="#eab308"
              strokeDasharray="5 5"
              label={{ value: "High", fill: "#eab308", fontSize: 10 }}
            />
            <ReferenceLine
              y={30}
              stroke="#ef4444"
              strokeDasharray="5 5"
              label={{ value: "Critical", fill: "#ef4444", fontSize: 10 }}
            />
            <Area
              type="monotone"
              dataKey="stubble_percent"
              stroke="#22c55e"
              fill="url(#stubbleGradient)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card>
    </div>
  )
}
