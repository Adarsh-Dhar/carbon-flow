'use client'

import { useEffect, useState } from 'react'
import { Card } from '@/components/ui/card'
import { CheckCircle, AlertCircle, Clock, RefreshCw } from 'lucide-react'
import { OrchestratorState, LogEntry, AgentHistory } from '@/types/orchestrator'
import { usePolling } from '@/hooks/use-polling'

function formatTimeAgo(timestamp: string | null): string {
  if (!timestamp) return 'Never'
  
  try {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} min ago`
    
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  } catch {
    return 'Unknown'
  }
}

function formatTimestamp(timestamp: string | null): string {
  if (!timestamp) return '—'
  try {
    return new Date(timestamp).toLocaleString()
  } catch {
    return '—'
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'operational':
      return 'text-green-400'
    case 'idle':
      return 'text-yellow-400'
    case 'inactive':
      return 'text-red-400'
    default:
      return 'text-slate-400'
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'operational':
      return <CheckCircle className="w-5 h-5 text-green-400" />
    case 'idle':
      return <Clock className="w-5 h-5 text-yellow-400" />
    case 'inactive':
      return <AlertCircle className="w-5 h-5 text-red-400" />
    default:
      return <AlertCircle className="w-5 h-5 text-slate-400" />
  }
}

export default function StatusPage() {
  const [status, setStatus] = useState<OrchestratorState | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [agentHistory, setAgentHistory] = useState<AgentHistory | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = async () => {
    try {
      const response = await fetch('/api/status')
      if (response.ok) {
        const data: OrchestratorState = await response.json()
        setStatus(data)
      }
    } catch (err) {
      console.error('Failed to fetch status:', err)
    }
  }

  const fetchLogs = async () => {
    try {
      const response = await fetch('/api/logs?limit=20')
      if (response.ok) {
        const data = await response.json()
        setLogs(data.logs || [])
      }
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    }
  }

  const fetchAgentHistory = async () => {
    try {
      const API_SERVER_URL = process.env.NEXT_PUBLIC_API_SERVER_URL || 'http://localhost:8000'
      const response = await fetch(`${API_SERVER_URL}/api/agents/history`)
      if (response.ok) {
        const data: AgentHistory = await response.json()
        setAgentHistory(data)
      }
    } catch (err) {
      console.error('Failed to fetch agent history:', err)
    }
  }

  const fetchAll = async () => {
    setError(null)
    try {
      await Promise.all([fetchStatus(), fetchLogs(), fetchAgentHistory()])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load status')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
  }, [])

  // Poll for updates every 30 seconds
  usePolling(fetchAll, 30000)

  if (loading) {
    return (
      <div className="p-8 space-y-8">
        <Card className="bg-slate-800/50 border-slate-700 p-6">
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 bg-slate-900/50 rounded animate-pulse" />
            ))}
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-8">
      <Card className="bg-slate-800/50 border-slate-700 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-slate-50 font-semibold">System Status</h2>
          <button
            onClick={fetchAll}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-300 hover:text-slate-50 bg-slate-700/50 hover:bg-slate-700 rounded transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-4 border-b border-slate-700">
            <div className="flex items-center gap-3">
              {status ? getStatusIcon(status.status) : <AlertCircle className="w-5 h-5 text-slate-400" />}
              <div>
                <p className="text-slate-50 font-medium">Orchestrator</p>
                <p className="text-slate-400 text-sm">
                  {status?.last_cycle_timestamp 
                    ? `Last cycle: ${formatTimeAgo(status.last_cycle_timestamp)}`
                    : 'No cycle data'}
                </p>
              </div>
            </div>
            <span className={`text-sm font-semibold ${status ? getStatusColor(status.status) : 'text-slate-400'}`}>
              {status?.status ? status.status.charAt(0).toUpperCase() + status.status.slice(1) : 'Unknown'}
            </span>
          </div>

          <div className="flex items-center justify-between pb-4 border-b border-slate-700">
            <div className="flex items-center gap-3">
              {status?.last_ingestion_timestamp ? (
                <CheckCircle className="w-5 h-5 text-green-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-slate-400" />
              )}
              <div>
                <p className="text-slate-50 font-medium">Sensor Ingest Agent</p>
                <p className="text-slate-400 text-sm">
                  {formatTimeAgo(status?.last_ingestion_timestamp || null)}
                </p>
              </div>
            </div>
            <span className={`text-sm font-semibold ${status?.last_ingestion_timestamp ? 'text-green-400' : 'text-slate-400'}`}>
              {status?.last_ingestion_timestamp ? 'Active' : 'Inactive'}
            </span>
          </div>

          <div className="flex items-center justify-between pb-4 border-b border-slate-700">
            <div className="flex items-center gap-3">
              {status?.last_forecast_timestamp ? (
                <CheckCircle className="w-5 h-5 text-green-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-slate-400" />
              )}
              <div>
                <p className="text-slate-50 font-medium">Forecast Agent</p>
                <p className="text-slate-400 text-sm">
                  {formatTimeAgo(status?.last_forecast_timestamp || null)}
                </p>
              </div>
            </div>
            <span className={`text-sm font-semibold ${status?.last_forecast_timestamp ? 'text-green-400' : 'text-slate-400'}`}>
              {status?.last_forecast_timestamp ? 'Active' : 'Inactive'}
            </span>
          </div>

          {status?.cycle_duration_seconds && (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-blue-400" />
                <div>
                  <p className="text-slate-50 font-medium">Last Cycle Duration</p>
                  <p className="text-slate-400 text-sm">
                    {status.cycle_duration_seconds.toFixed(1)} seconds
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </Card>

      {agentHistory && (
        <Card className="bg-slate-800/50 border-slate-700 p-6">
          <h3 className="text-slate-50 font-semibold mb-6">Agent Execution History</h3>
          <div className="space-y-6">
            {Object.entries(agentHistory).map(([agentName, history]) => (
              history.length > 0 && (
                <div key={agentName} className="pb-4 border-b border-slate-700 last:border-0 last:pb-0">
                  <h4 className="text-slate-300 font-medium mb-3 capitalize">
                    {agentName.replace('_', ' ')}
                  </h4>
                  <div className="space-y-2 text-sm">
                    {history.slice(0, 5).map((entry, idx) => (
                      <div key={idx} className="flex gap-3">
                        <span className="text-slate-500 flex-shrink-0 min-w-[80px]">
                          {formatTimestamp(entry.timestamp).split(',')[1]?.trim() || '—'}
                        </span>
                        <span className={`flex-shrink-0 min-w-[80px] ${
                          entry.status === 'success' ? 'text-green-400' :
                          entry.status === 'failed' ? 'text-red-400' :
                          'text-yellow-400'
                        }`}>
                          {entry.status}
                        </span>
                        <span className="text-slate-300 flex-1 truncate">
                          {entry.message}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )
            ))}
          </div>
        </Card>
      )}

      <Card className="bg-slate-800/50 border-slate-700 p-6">
        <h3 className="text-slate-50 font-semibold mb-6">Recent Events</h3>
        <div className="space-y-3 text-sm">
          {logs.length === 0 ? (
            <div className="text-center text-slate-400 py-4">No log entries available</div>
          ) : (
            logs.slice(0, 10).map((log, idx) => (
              <div key={idx} className="flex gap-3 pb-3 border-b border-slate-700 last:border-0 last:pb-0">
                <span className="text-slate-500 flex-shrink-0 min-w-[100px]">
                  {formatTimestamp(log.timestamp).split(',')[1]?.trim() || log.timestamp}
                </span>
                <span className={`flex-shrink-0 min-w-[60px] ${
                  log.level === 'ERROR' ? 'text-red-400' :
                  log.level === 'WARNING' ? 'text-yellow-400' :
                  'text-slate-400'
                }`}>
                  [{log.level}]
                </span>
                <span className="text-slate-300 flex-1">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  )
}
