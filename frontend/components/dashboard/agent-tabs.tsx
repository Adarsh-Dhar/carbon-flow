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
  Shield,
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
import { runForecastCycle, runAccountability, downloadAccountabilityPDF } from "@/lib/api"
import type {
  ForecastLatest,
  AgentHistory,
  AgentHistoryEntry,
  ForecastHistoryEntry,
  AccountabilityReport,
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
  onEnforcementClick: () => void
}

export function AgentTabs({
  forecast,
  history,
  trendData,
  isLoading,
  forecastError = false,
  historyError = false,
  trendsError = false,
  onEnforcementClick,
}: AgentTabsProps) {
  const [jsonExpanded, setJsonExpanded] = useState(false)
  const [accountabilityReport, setAccountabilityReport] = useState<AccountabilityReport | null>(null)

  const enforcementHistory = history?.enforcement ?? []

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

  const accountabilityAction = useAgentAction({
    actionFn: runAccountability,
    queryKeysToInvalidate: ["status"],
    successMessage: "Accountability report generated",
    errorMessage: "Failed to generate report",
    onSuccess: (data) => setAccountabilityReport(data),
  })

  const handleDownloadPDF = async () => {
    try {
      const blob = await downloadAccountabilityPDF()
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `accountability-report-${new Date().toISOString().split("T")[0]}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error("Failed to download PDF:", error)
    }
  }

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
          value="enforcement"
          className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
        >
          <Shield className="h-4 w-4" />
          Enforcement
        </TabsTrigger>
        <TabsTrigger
          value="accountability"
          className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
        >
          <FileText className="h-4 w-4" />
          Accountability
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

      {/* Enforcement Tab */}
      <TabsContent value="enforcement" className="mt-4">
        <Alert className="mb-4 border-orange bg-orange/10">
          <AlertTriangle className="h-4 w-4 text-orange" />
          <AlertDescription className="text-orange">
            Autonomous enforcement actions require explicit authorization. Review the forecast reasoning before
            proceeding.
          </AlertDescription>
        </Alert>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="glass-card p-5">
            <h3 className="font-semibold text-foreground mb-3">Forecast Reasoning</h3>
            <p className="text-sm text-muted-foreground mb-4">
              {forecast?.prediction?.reasoning || "No forecast reasoning available. Run a forecast cycle first."}
            </p>
            <Button
              onClick={onEnforcementClick}
              variant="destructive"
              className="w-full gap-2 bg-orange hover:bg-orange/90"
            >
              <Shield className="h-4 w-4" />
              Authorize Autonomous Enforcement
            </Button>
          </Card>

          <Card className="glass-card p-5">
            <h3 className="font-semibold text-foreground mb-3">Action Log</h3>
            <div className="space-y-3">
              {historyError ? (
                <p className="text-sm text-destructive font-semibold">ERR</p>
              ) : enforcementHistory.length === 0 ? (
                <p className="text-sm text-muted-foreground">No enforcement activity recorded yet.</p>
              ) : (
                enforcementHistory.map((entry, idx) => (
                  <div
                    key={`${entry.timestamp}-${idx}`}
                    className="flex items-center justify-between py-2 border-b border-border last:border-0"
                  >
                    <div>
                      <p className="text-sm text-foreground capitalize">{entry.status}</p>
                      <p className="text-xs text-muted-foreground">{entry.message}</p>
                    </div>
                    <Badge className={getBadgeClass(entry.status)}>
                      <Clock className="h-3 w-3 mr-1" />
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </Badge>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      </TabsContent>

      {/* Accountability Tab */}
      <TabsContent value="accountability" className="mt-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="glass-card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-foreground">Generate Report</h3>
              <Badge variant="outline" className="text-success border-success">
                Ready
              </Badge>
            </div>
            <Button
              onClick={() => accountabilityAction.execute()}
              disabled={accountabilityAction.isLoading}
              className="w-full gap-2 mb-3"
            >
              {accountabilityAction.isLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <FileText className="h-4 w-4" />
              )}
              Run Accountability Analysis
            </Button>
            {accountabilityReport && (
              <Button variant="outline" onClick={handleDownloadPDF} className="w-full gap-2 bg-transparent">
                <Download className="h-4 w-4" />
                Download PDF
              </Button>
            )}
          </Card>

          {accountabilityReport && (
            <>
              <Card className="glass-card p-5">
                <h3 className="font-semibold text-foreground mb-2">Executive Summary</h3>
                <p className="text-sm text-muted-foreground mb-3">{accountabilityReport.executive_summary}</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Report ID</span>
                    <span className="font-mono text-foreground">{accountabilityReport.id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Generated</span>
                    <span className="text-foreground">
                      {new Date(accountabilityReport.generated_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Confidence</span>
                    <span className="text-foreground">{accountabilityReport.confidence_percent}%</span>
                  </div>
                </div>
              </Card>

              <Card className="glass-card p-5">
                <h3 className="font-semibold text-foreground mb-3">Fire Correlation</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Fire Count</span>
                    <span className="text-orange font-semibold">
                      {accountabilityReport.fire_correlation.fire_count}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Correlation Strength</span>
                    <span className="text-foreground">
                      {(accountabilityReport.fire_correlation.correlation_strength * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Primary Source</span>
                    <span className="text-foreground">
                      {accountabilityReport.fire_correlation.primary_source_direction}
                    </span>
                  </div>
                </div>
              </Card>
            </>
          )}
        </div>
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
