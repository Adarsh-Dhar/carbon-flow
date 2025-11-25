"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { CheckCircle2, XCircle, Clock, Loader2, Database, CloudSun, Shield, FileText } from "lucide-react"
import type { AgentHistory, AgentHistoryEntry } from "@/lib/types"

interface ActivityLogProps {
  history: AgentHistory | undefined
  isLoading: boolean
}

const agentIcons = {
  sensor_ingest: Database,
  forecast: CloudSun,
  enforcement: Shield,
  accountability: FileText,
}

const agentLabels = {
  sensor_ingest: "Sensor Ingest",
  forecast: "Forecast",
  enforcement: "Enforcement",
  accountability: "Accountability",
}

const statusConfig = {
  success: { icon: CheckCircle2, className: "text-success", badge: "bg-success/20 text-success" },
  failure: { icon: XCircle, className: "text-destructive", badge: "bg-destructive/20 text-destructive" },
  running: { icon: Loader2, className: "text-primary animate-spin", badge: "bg-primary/20 text-primary" },
  pending: { icon: Clock, className: "text-muted-foreground", badge: "bg-muted text-muted-foreground" },
}

// Mock data for demonstration
const mockHistory: AgentHistory = {
  sensor_ingest: [
    {
      timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
      status: "success",
      message: "Ingested 42 CPCB stations",
    },
    {
      timestamp: new Date(Date.now() - 35 * 60000).toISOString(),
      status: "success",
      message: "NASA FIRMS data updated",
    },
  ],
  forecast: [
    {
      timestamp: new Date(Date.now() - 10 * 60000).toISOString(),
      status: "success",
      message: "Predicted: Very Poor (86% confidence)",
    },
    {
      timestamp: new Date(Date.now() - 70 * 60000).toISOString(),
      status: "success",
      message: "Predicted: Poor (92% confidence)",
    },
  ],
  enforcement: [
    {
      timestamp: new Date(Date.now() - 120 * 60000).toISOString(),
      status: "pending",
      message: "Awaiting authorization",
    },
  ],
  accountability: [
    {
      timestamp: new Date(Date.now() - 180 * 60000).toISOString(),
      status: "success",
      message: "Report #ACC-2024-1142 generated",
    },
  ],
}

export function ActivityLog({ history, isLoading }: ActivityLogProps) {
  const data = history || mockHistory

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="glass-card p-4">
            <Skeleton className="h-4 w-32 mb-3" />
            <div className="space-y-2">
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-3/4" />
            </div>
          </Card>
        ))}
      </div>
    )
  }

  const allEntries: { agent: keyof AgentHistory; entry: AgentHistoryEntry }[] = []

  Object.entries(data).forEach(([agent, entries]) => {
    entries.forEach((entry) => {
      allEntries.push({ agent: agent as keyof AgentHistory, entry })
    })
  })

  // Sort by timestamp descending
  allEntries.sort((a, b) => new Date(b.entry.timestamp).getTime() - new Date(a.entry.timestamp).getTime())

  if (allEntries.length === 0) {
    return (
      <Card className="glass-card p-8 text-center">
        <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <h3 className="font-semibold text-foreground mb-2">No Activity Yet</h3>
        <p className="text-sm text-muted-foreground">Agent activity will appear here once cycles start running.</p>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      {allEntries.map((item, index) => {
        const Icon = agentIcons[item.agent]
        const StatusIcon = statusConfig[item.entry.status].icon
        const statusClass = statusConfig[item.entry.status]

        return (
          <Card key={index} className="glass-card p-4">
            <div className="flex items-start gap-4">
              {/* Timeline connector */}
              <div className="flex flex-col items-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                {index < allEntries.length - 1 && <div className="w-px h-8 bg-border mt-2" />}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-foreground">{agentLabels[item.agent]}</span>
                  <Badge className={statusClass.badge}>
                    <StatusIcon className={`h-3 w-3 mr-1 ${statusClass.className}`} />
                    {item.entry.status}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">{item.entry.message}</p>
                <p className="text-xs text-muted-foreground/60 mt-1">
                  {new Date(item.entry.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
          </Card>
        )
      })}
    </div>
  )
}
