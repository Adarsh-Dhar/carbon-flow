'use client'

import { useEffect, useState } from 'react'
import { Card } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import AQIBadge from '@/components/aqi-badge'
import { SensorData, CPCBStation } from '@/types/orchestrator'
import { usePolling } from '@/hooks/use-polling'

function formatTimeAgo(timestamp: string | null): string {
  if (!timestamp) return 'Unknown'
  
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

function getAQICategory(aqi: number): string {
  if (aqi <= 50) return 'Good'
  if (aqi <= 100) return 'Satisfactory'
  if (aqi <= 200) return 'Moderate'
  if (aqi <= 300) return 'Poor'
  if (aqi <= 400) return 'Very Poor'
  return 'Severe'
}

export default function SensorsPage() {
  const [sensorData, setSensorData] = useState<SensorData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSensors = async () => {
    try {
      setError(null)
      const response = await fetch('/api/sensors')
      
      if (!response.ok) {
        if (response.status === 404) {
          setError('No sensor data available')
        } else {
          const data = await response.json()
          setError(data.error || 'Failed to load sensor data')
        }
        setLoading(false)
        return
      }

      const data: SensorData = await response.json()
      setSensorData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sensor data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSensors()
  }, [])

  // Poll for updates every 30 seconds
  usePolling(fetchSensors, 30000)

  if (loading) {
    return (
      <div className="p-8 space-y-8">
        <Card className="bg-slate-800/50 border-slate-700">
          <div className="p-6">
            <div className="h-64 bg-slate-900/50 rounded animate-pulse" />
          </div>
        </Card>
      </div>
    )
  }

  if (error || !sensorData) {
    return (
      <div className="p-8">
        <Card className="bg-slate-800/50 border-slate-700 p-6">
          <div className="text-center text-slate-400">
            <p className="text-lg font-semibold mb-2">Failed to load sensor data</p>
            <p className="text-sm">{error || 'No sensor data available'}</p>
          </div>
        </Card>
      </div>
    )
  }

  const stations: CPCBStation[] = sensorData.cpcb_data || []

  return (
    <div className="p-8 space-y-8">
      <Card className="bg-slate-800/50 border-slate-700">
        <div className="p-6">
          <h2 className="text-slate-50 font-semibold mb-6">CPCB Monitoring Stations</h2>
          <Table>
            <TableHeader>
              <TableRow className="border-slate-700">
                <TableHead className="text-slate-400">Station</TableHead>
                <TableHead className="text-slate-400">AQI</TableHead>
                <TableHead className="text-slate-400">PM2.5</TableHead>
                <TableHead className="text-slate-400">PM10</TableHead>
                <TableHead className="text-slate-400">Status</TableHead>
                <TableHead className="text-slate-400">Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stations.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-slate-400 py-8">
                    No sensor data available
                  </TableCell>
                </TableRow>
              ) : (
                stations.map((station) => (
                  <TableRow key={station.station} className="border-slate-700">
                    <TableCell className="text-slate-300">{station.station}</TableCell>
                    <TableCell>
                      <AQIBadge 
                        aqi={station.aqi} 
                        category={getAQICategory(station.aqi)}
                        size="sm"
                      />
                    </TableCell>
                    <TableCell className="text-slate-300">
                      {station.pm25 !== null ? `${station.pm25.toFixed(1)} µg/m³` : '—'}
                    </TableCell>
                    <TableCell className="text-slate-300">
                      {station.pm10 !== null ? `${station.pm10.toFixed(1)} µg/m³` : '—'}
                    </TableCell>
                    <TableCell>
                      {station.is_hotspot ? (
                        <span className="text-red-400 text-sm font-semibold">🔴 Hotspot</span>
                      ) : (
                        <span className="text-green-400 text-sm font-semibold">✓ Normal</span>
                      )}
                    </TableCell>
                    <TableCell className="text-slate-400 text-sm">
                      {formatTimeAgo(station.timestamp)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  )
}
