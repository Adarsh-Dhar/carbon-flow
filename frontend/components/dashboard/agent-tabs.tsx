"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Skeleton } from "@/components/ui/skeleton"
import {
  CloudSun,
  FileText,
  TrendingUp,
  Activity,
  BarChart3,
  Play,
  Download,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  Clock,
  RefreshCw,
} from "lucide-react"
import { useAgentAction } from "@/hooks/use-agent-action"
import { runForecastCycle } from "@/lib/api"
import type {
  ForecastLatest,
  AgentHistory,
  AgentHistoryEntry,
  ForecastHistoryEntry,
} from "@/lib/types"
import { TrendsCharts } from "./trends-charts"
import { ActivityLog } from "./activity-log"

interface AgentTabsProps {
  forecast: ForecastLatest | undefined
  history: AgentHistory | undefined
  trendData: ForecastHistoryEntry[] | undefined
  isLoading: boolean
  forecastError?: boolean
  historyError?: boolean
  trendsError?: boolean
}

export function AgentTabs({
  forecast,
  history,
  trendData,
  isLoading,
  forecastError = false,
  historyError = false,
  trendsError = false,
}: AgentTabsProps) {
  const [jsonExpanded, setJsonExpanded] = useState(false)

  const getBadgeClass = (status: AgentHistoryEntry["status"]) => {
    switch (status) {
      case "success":
        return "bg-success/20 text-success"
      case "failure":
        return "bg-destructive/20 text-destructive"
      case "running":
        return "bg-primary/20 text-primary"
      default:
        return "bg-muted text-muted-foreground"
    }
  }

  const forecastAction = useAgentAction({
    actionFn: runForecastCycle,
    queryKeysToInvalidate: ["forecast", "sensors", "status"],
    successMessage: "Forecast cycle completed",
    errorMessage: "Forecast cycle failed",
  })


  return (
    <Tabs defaultValue="forecast" className="mb-6">
      <TabsList className="glass w-full justify-start gap-1 p-1 h-auto flex-wrap">
        <TabsTrigger
          value="forecast"
          className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
        >
          <CloudSun className="h-4 w-4" />
          Forecast
        </TabsTrigger>
        <TabsTrigger
          value="trends"
          className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
        >
          <TrendingUp className="h-4 w-4" />
          Trends
        </TabsTrigger>
        <TabsTrigger
          value="activity"
          className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
        >
          <Activity className="h-4 w-4" />
          Activity Log
        </TabsTrigger>
        <TabsTrigger
          value="visualizations"
          className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
        >
          <BarChart3 className="h-4 w-4" />
          Advanced
        </TabsTrigger>
      </TabsList>

      {/* Forecast Tab */}
      <TabsContent value="forecast" className="mt-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="glass-card p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-semibold text-foreground">Agent 2: Forecast Engine</h3>
                <p className="text-sm text-muted-foreground">AI-powered AQI prediction and analysis</p>
              </div>
              <Badge variant="outline" className="text-success border-success">
                <CheckCircle2 className="h-3 w-3 mr-1" />
                Available
              </Badge>
            </div>
            <Button
              onClick={() => forecastAction.execute()}
              disabled={forecastAction.isLoading}
              className="w-full gap-2"
            >
              {forecastAction.isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Run Forecast Cycle
            </Button>
          </Card>

          <Card className="glass-card p-5">
            <h3 className="font-semibold text-foreground mb-3">Latest Prediction</h3>
            {isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ) : forecast?.prediction && !forecastError ? (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <Badge className="bg-orange text-white">{forecast.prediction.aqi_category}</Badge>
                  <span className="text-sm text-muted-foreground">
                    Confidence: {forecast.prediction.confidence_level}%
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">{forecast.prediction.reasoning}</p>
                <div className="flex flex-wrap gap-2">
                  {forecast.artifacts?.map((artifact, i) => (
                    <Badge key={i} variant="outline" className="text-xs">
                      {artifact}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-destructive font-semibold">ERR</p>
            )}
          </Card>
        </div>

        {/* JSON Inspector */}
        <Collapsible open={jsonExpanded} onOpenChange={setJsonExpanded} className="mt-4">
          <CollapsibleTrigger asChild>
            <Button variant="ghost" className="gap-2 text-muted-foreground">
              {jsonExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              JSON Inspector
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <Card className="glass-card mt-2 p-4">
              <pre className="text-xs text-muted-foreground overflow-auto max-h-64 font-mono">
                {JSON.stringify(forecast, null, 2)}
              </pre>
            </Card>
          </CollapsibleContent>
        </Collapsible>
      </TabsContent>

      {/* Trends Tab */}
      <TabsContent value="trends" className="mt-4">
        <TrendsCharts data={trendData} isLoading={isLoading} hasError={trendsError} />
      </TabsContent>

      {/* Activity Log Tab */}
      <TabsContent value="activity" className="mt-4">
        <ActivityLog history={history} isLoading={isLoading} hasError={historyError} />
      </TabsContent>

      {/* Advanced Visualizations Tab */}
      <TabsContent value="visualizations" className="mt-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="glass-card p-5">
            <h3 className="font-semibold text-foreground mb-2">AQI Heatmap</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Spatiotemporal visualization of AQI distribution across Delhi NCR region.
            </p>
            <div
              className="h-48 rounded-lg bg-secondary/50 flex items-center justify-center mb-4"
              style={{ backgroundImage: `url('/heatmap-visualization-blue-orange.jpg')` }}
            />
            <Button variant="outline" className="w-full gap-2 bg-transparent" disabled>
              <BarChart3 className="h-4 w-4" />
              View Heatmap (Coming Soon)
            </Button>
          </Card>

          <Card className="glass-card p-5">
            <h3 className="font-semibold text-foreground mb-2">Timelapse Animation</h3>
            <p className="text-sm text-muted-foreground mb-4">
              24-hour animated visualization of pollution spread patterns.
            </p>
            <div
              className="h-48 rounded-lg bg-secondary/50 flex items-center justify-center mb-4"
              style={{ backgroundImage: `url('/timelapse-animation-frames-air-pollution.jpg')` }}
            />
            <Button variant="outline" className="w-full gap-2 bg-transparent" disabled>
              <Play className="h-4 w-4" />
              Play Timelapse (Coming Soon)
            </Button>
          </Card>
        </div>
      </TabsContent>
    </Tabs>
  )
}
