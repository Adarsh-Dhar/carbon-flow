"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Progress } from "@/components/ui/progress"
import {
  Database,
  CloudSun,
  Shield,
  FileText,
  RefreshCw,
  Clock,
  Bell,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
} from "lucide-react"
import { useRefresh, type RefreshInterval } from "@/hooks/use-refresh"
import type { OrchestratorStatus } from "@/lib/types"

interface RightSidebarProps {
  status: OrchestratorStatus | undefined
  isLoading: boolean
}

const agents = [
  { key: "sensor_ingest", label: "Sensor Ingest", icon: Database },
  { key: "forecast", label: "Forecast", icon: CloudSun },
  { key: "enforcement", label: "Enforcement", icon: Shield },
  { key: "accountability", label: "Accountability", icon: FileText },
] as const

const intervalOptions: { value: RefreshInterval; label: string }[] = [
  { value: 15, label: "15s" },
  { value: 30, label: "30s" },
  { value: 60, label: "1m" },
  { value: 120, label: "2m" },
  { value: 300, label: "5m" },
]

export function RightSidebar({ status, isLoading }: RightSidebarProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [interval, setInterval] = useState<RefreshInterval>(30)

  const { countdown, refresh } = useRefresh(autoRefresh, interval)

  const formatLastRun = (timestamp: string | null) => {
    if (!timestamp) return "Never"
    const date = new Date(timestamp)
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (diff < 60) return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
  }

  if (collapsed) {
    return (
      <div className="w-12 flex flex-col items-center py-4 border-l border-border bg-sidebar">
        <Button variant="ghost" size="icon" onClick={() => setCollapsed(false)} className="mb-4">
          <ChevronLeft className="h-4 w-4" />
        </Button>
        {agents.map((agent) => (
          <div key={agent.key} className="mb-3">
            <agent.icon className="h-4 w-4 text-muted-foreground" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <aside className="w-80 border-l border-border bg-sidebar p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-semibold text-foreground">Control Panel</h2>
        <Button variant="ghost" size="icon" onClick={() => setCollapsed(true)} className="lg:hidden">
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Agent Availability */}
      <div className="mb-6">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Agent Availability
        </h3>
        <div className="space-y-2">
          {agents.map((agent) => {
            const agentStatus = status?.agents?.[agent.key]
            const isAvailable = agentStatus?.status === "available"

            return (
              <Card key={agent.key} className="glass-card p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <agent.icon className="h-4 w-4 text-primary" />
                    <span className="text-sm text-foreground">{agent.label}</span>
                  </div>
                  <Badge
                    variant="outline"
                    className={isAvailable ? "text-success border-success" : "text-muted-foreground"}
                  >
                    {isAvailable ? <CheckCircle2 className="h-3 w-3 mr-1" /> : <XCircle className="h-3 w-3 mr-1" />}
                    {isAvailable ? "Available" : "Unavailable"}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Last run: {formatLastRun(agentStatus?.last_run || null)}
                </p>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Auto-Refresh Controls */}
      <Card className="glass-card p-4 mb-6">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Auto-Refresh</h3>
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-foreground">Enable</span>
          <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} />
        </div>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-sm text-muted-foreground">Interval:</span>
          <Select value={interval.toString()} onValueChange={(v) => setInterval(Number(v) as RefreshInterval)}>
            <SelectTrigger className="w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {intervalOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value.toString()}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {autoRefresh && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Next refresh in:</span>
              <span className="font-mono text-foreground">{countdown}s</span>
            </div>
            <Progress value={(countdown / interval) * 100} className="h-1" />
          </div>
        )}
        <Button variant="outline" size="sm" onClick={refresh} className="w-full mt-3 gap-2 bg-transparent">
          <RefreshCw className="h-3 w-3" />
          Refresh Now
        </Button>
      </Card>

      {/* Data Freshness */}
      <Card className="glass-card p-4 mb-6">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Data Freshness</h3>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Forecast</span>
            <Badge variant="outline" className="text-xs">
              <Clock className="h-3 w-3 mr-1" />
              5m ago
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Sensors</span>
            <Badge variant="outline" className="text-xs">
              <Clock className="h-3 w-3 mr-1" />
              2m ago
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Station Count</span>
            <span className="text-foreground font-medium">42</span>
          </div>
        </div>
      </Card>

      {/* Recent Report */}
      <Card className="glass-card p-4 mb-6">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Latest Report</h3>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">ID</span>
            <span className="font-mono text-foreground text-xs">ACC-2024-1142</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Generated</span>
            <span className="text-foreground">Today, 14:32</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Confidence</span>
            <span className="text-success font-medium">87%</span>
          </div>
        </div>
      </Card>

      {/* Notifications Placeholder */}
      <Card className="glass-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Bell className="h-4 w-4 text-primary" />
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Notifications</h3>
        </div>
        <p className="text-sm text-muted-foreground">Alert notifications will appear here when integrated.</p>
      </Card>
    </aside>
  )
}
