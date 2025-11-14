'use client'

import { useEffect, useState } from 'react'
import { Card } from '@/components/ui/card'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { ForecastData } from '@/types/orchestrator'
import { usePolling } from '@/hooks/use-polling'

export default function ForecastPage() {
  const [forecast, setForecast] = useState<ForecastData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchForecast = async () => {
    try {
      setError(null)
      const response = await fetch('/api/forecast')
      
      if (!response.ok) {
        if (response.status === 404) {
          setError('No forecast data available')
        } else {
          const data = await response.json()
          setError(data.error || 'Failed to load forecast')
        }
        setLoading(false)
        return
      }

      const data: ForecastData = await response.json()
      setForecast(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load forecast')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchForecast()
  }, [])

  // Poll for updates every 30 seconds
  usePolling(fetchForecast, 30000)

  // Generate forecast chart data (simplified - using current and predicted values)
  const forecastData = forecast ? [
    { time: '00:00', aqi: forecast.data_sources.cpcb_aqi || 0, confidence: forecast.confidence_level },
    { time: '04:00', aqi: (forecast.data_sources.cpcb_aqi || 0) * 1.1, confidence: forecast.confidence_level },
    { time: '08:00', aqi: (forecast.data_sources.cpcb_aqi || 0) * 1.2, confidence: forecast.confidence_level },
    { time: '12:00', aqi: forecast.prediction.threshold, confidence: forecast.confidence_level },
    { time: '16:00', aqi: forecast.prediction.threshold * 0.95, confidence: forecast.confidence_level },
    { time: '20:00', aqi: (forecast.data_sources.cpcb_aqi || 0) * 1.1, confidence: forecast.confidence_level },
    { time: '24:00', aqi: (forecast.data_sources.cpcb_aqi || 0) * 0.9, confidence: forecast.confidence_level },
  ] : []

  if (loading) {
    return (
      <div className="p-8 space-y-8">
        <Card className="bg-slate-800/50 border-slate-700 p-6">
          <div className="h-64 bg-slate-900/50 rounded animate-pulse" />
        </Card>
        <Card className="bg-slate-800/50 border-slate-700 p-6">
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-8 bg-slate-900/50 rounded animate-pulse" />
            ))}
          </div>
        </Card>
      </div>
    )
  }

  if (error || !forecast) {
    return (
      <div className="p-8">
        <Card className="bg-slate-800/50 border-slate-700 p-6">
          <div className="text-center text-slate-400">
            <p className="text-lg font-semibold mb-2">Failed to load forecast</p>
            <p className="text-sm">{error || 'No forecast data available'}</p>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-8">
      <Card className="bg-slate-800/50 border-slate-700 p-6">
        <h2 className="text-slate-50 font-semibold mb-6">24-Hour AQI Forecast</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={forecastData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" stroke="#64748b" />
            <YAxis stroke="#64748b" />
            <Tooltip 
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Line 
              type="monotone" 
              dataKey="aqi" 
              stroke="#0ea5e9" 
              strokeWidth={2}
              dot={{ fill: '#0ea5e9', r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <Card className="bg-slate-800/50 border-slate-700 p-6">
        <h3 className="text-slate-50 font-semibold mb-4">Forecast Details</h3>
        <div className="space-y-3">
          <div className="flex justify-between items-center pb-3 border-b border-slate-700">
            <span className="text-slate-400">Peak AQI Expected</span>
            <span className="text-slate-50 font-semibold">
              {forecast.prediction.threshold} ({forecast.prediction.estimated_hours_to_threshold}h)
            </span>
          </div>
          <div className="flex justify-between items-center pb-3 border-b border-slate-700">
            <span className="text-slate-400">Forecast Confidence</span>
            <span className="text-slate-50 font-semibold">{forecast.confidence_level.toFixed(0)}%</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Last Updated</span>
            <span className="text-slate-50 font-semibold">
              {forecast.timestamp ? new Date(forecast.timestamp).toLocaleString() : 'Unknown'}
            </span>
          </div>
        </div>
      </Card>
    </div>
  )
}
