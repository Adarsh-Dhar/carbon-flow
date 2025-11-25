"use client"

import { Play, Shield, FileText, RefreshCw, Clock, Timer } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useAgentAction } from "@/hooks/use-agent-action"
import { runForecastCycle, runAccountability } from "@/lib/api"
import type { OrchestratorStatus } from "@/lib/types"

interface HeroBarProps {
  status: OrchestratorStatus | undefined
  isLoading: boolean
  hasError?: boolean
  onEnforcementClick: () => void
}

export function HeroBar({ status, isLoading, hasError = false, onEnforcementClick }: HeroBarProps) {
  const forecastAction = useAgentAction({
    actionFn: runForecastCycle,
    queryKeysToInvalidate: ["forecast", "sensors", "status"],
    successMessage: "Forecast cycle started",
    errorMessage: "Failed to start forecast cycle",
  })

  const accountabilityAction = useAgentAction({
    actionFn: runAccountability,
    queryKeysToInvalidate: ["status"],
    successMessage: "Accountability report generated",
    errorMessage: "Failed to generate report",
  })

  const statusColor = {
    operational: "bg-success text-success-foreground",
    idle: "bg-warning text-warning-foreground",
    inactive: "bg-muted text-muted-foreground",
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }

  const formatLastRun = (timestamp: string | undefined) => {
    if (!timestamp) return "Never"
    const date = new Date(timestamp)
    return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
  }

  return (
    <div className="glass-card rounded-2xl p-6 mb-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        {/* Title Section */}
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">CarbonFlow</h1>
            <p className="text-muted-foreground text-sm">Autonomous Air Quality Governance</p>
          </div>
          <Badge
            className={`${
              hasError
                ? "bg-destructive text-destructive-foreground"
                : status
                  ? statusColor[status.status]
                  : "bg-muted text-muted-foreground"
            } uppercase text-xs font-semibold px-3 py-1`}
          >
            {hasError ? "ERR" : isLoading ? "Loading..." : status?.status || "Unknown"}
          </Badge>
        </div>

        {/* Quick Stats */}
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>Last cycle: </span>
            <span className="text-foreground font-medium">
              {hasError ? "ERR" : isLoading ? "..." : formatLastRun(status?.last_run)}
            </span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Timer className="h-4 w-4" />
            <span>Duration: </span>
            <span className="text-foreground font-medium">
              {hasError ? "ERR" : isLoading ? "..." : formatDuration(status?.cycle_duration_seconds || 0)}
            </span>
          </div>
        </div>

        {/* CTA Buttons */}
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => forecastAction.execute()}
            disabled={forecastAction.isLoading || hasError}
            className="gap-2"
          >
            {forecastAction.isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Run Forecast
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onEnforcementClick}
            className="gap-2 border-orange text-orange hover:bg-orange/10 bg-transparent"
          >
            <Shield className="h-4 w-4" />
            Authorize Enforcement
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => accountabilityAction.execute()}
            disabled={accountabilityAction.isLoading || hasError}
            className="gap-2"
          >
            {accountabilityAction.isLoading ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <FileText className="h-4 w-4" />
            )}
            Generate Report
          </Button>
        </div>
      </div>
    </div>
  )
}
