'use client'

import { useEffect, useState } from 'react'
import AQIBadge from '@/components/aqi-badge'
import MetricCard from '@/components/metric-card'
import ConfidenceMeter from '@/components/confidence-meter'
import DataSourceStatus from '@/components/data-source-status'
import { Card } from '@/components/ui/card'
import { TrendingUp, Wind, Flame, Leaf } from 'lucide-react'

interface ForecastData {
  prediction: {
    aqi_category: string
    threshold: number
    estimated_hours_to_threshold: number
  }
  confidence_level: number
  reasoning: string
  timestamp: string
  data_sources?: {
    cpcb_aqi?: number
    nasa_fire_count?: number
    avg_wind_speed_24h_kmh?: number
    stubble_burning_percent?: number
  }
}

export default function DashboardOverview() {
  const [forecast, setForecast] = useState<ForecastData | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedReasoning, setExpandedReasoning] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/api/forecast')
        const data = await response.json()
        setForecast(data)
      } catch (error) {
        console.error('Failed to fetch forecast:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="p-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 bg-slate-800/50 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (!forecast) {
    return <div className="p-8 text-slate-400">Failed to load forecast data</div>
  }

  // Safely extract data_sources with fallback
  const dataSources = forecast.data_sources || {}

  return (
    <div className="p-8 space-y-8">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-slate-800/50 to-blue-900/20 border border-slate-700 rounded-lg p-8 mb-8">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-slate-400 text-sm font-semibold mb-2">CURRENT AIR QUALITY</h2>
            <div className="flex items-baseline gap-4 mb-4">
              <div className="text-5xl font-bold text-slate-50">
                {dataSources.cpcb_aqi ?? 'N/A'}
              </div>
              <AQIBadge 
                aqi={dataSources.cpcb_aqi ?? 0} 
                category={forecast.prediction?.aqi_category || 'Unknown'}
                size="lg"
              />
            </div>
            <p className="text-slate-300">
              24-hour forecast: <span className="font-semibold">{forecast.prediction?.aqi_category || 'Unknown'}</span>
            </p>
          </div>
          <div className="text-right">
            <TrendingUp className="w-12 h-12 text-blue-400 mb-2 ml-auto" />
            <p className="text-slate-400 text-sm">Confidence: <span className="font-semibold text-slate-300">{forecast.confidence_level ?? 0}%</span></p>
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Current AQI"
          value={dataSources.cpcb_aqi ?? '—'}
          unit="µg/m³"
          icon={<TrendingUp className="w-5 h-5" />}
        />
        <MetricCard
          title="Fire Count"
          value={dataSources.nasa_fire_count ?? 0}
          trend="stable"
          description="NASA FIRMS detection"
        />
        <MetricCard
          title="Wind Speed"
          value={dataSources.avg_wind_speed_24h_kmh ?? '—'}
          unit="km/h"
          icon={<Wind className="w-5 h-5" />}
          description="24h average"
        />
        <MetricCard
          title="Stubble Burning"
          value={dataSources.stubble_burning_percent ?? 0}
          unit="%"
          icon={<Flame className="w-5 h-5" />}
          description="DSS attribution"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Prediction Card */}
        <div className="lg:col-span-2">
          <Card className="bg-slate-800/50 border-slate-700 p-6">
            <h3 className="text-slate-50 font-semibold mb-4 flex items-center gap-2">
              <Leaf className="w-5 h-5 text-blue-400" />
              24-Hour Forecast
            </h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-slate-400 text-sm mb-1">Predicted Category</p>
                  <AQIBadge 
                    aqi={forecast.prediction?.threshold ?? 0} 
                    category={forecast.prediction?.aqi_category || 'Unknown'}
                    size="md"
                  />
                </div>
                <div>
                  <p className="text-slate-400 text-sm mb-1">Hours to Threshold</p>
                  <p className="text-2xl font-bold text-slate-50">
                    {forecast.prediction?.estimated_hours_to_threshold ?? 0}h
                  </p>
                </div>
              </div>

              {/* Expandable Reasoning */}
              <div className="border-t border-slate-700 pt-4">
                <button
                  onClick={() => setExpandedReasoning(!expandedReasoning)}
                  className="flex items-center justify-between w-full hover:opacity-80 transition-opacity"
                >
                  <p className="text-slate-400 text-sm font-medium">Reasoning & Logic</p>
                  <span className="text-slate-500">{expandedReasoning ? '−' : '+'}</span>
                </button>
                {expandedReasoning && (
                  <p className="mt-3 text-slate-300 text-sm leading-relaxed bg-slate-900/50 p-3 rounded">
                    {forecast.reasoning || 'No reasoning available'}
                  </p>
                )}
              </div>
            </div>
          </Card>
        </div>

        {/* Confidence Meter */}
        <div className="flex flex-col items-center justify-center">
          <ConfidenceMeter value={forecast.confidence_level ?? 0} label="Prediction Confidence" />
        </div>
      </div>

      {/* Data Sources Status */}
      <DataSourceStatus 
        sources={[
          { name: 'CPCB Sensors', active: true, lastUpdate: 'Updated now' },
          { name: 'NASA FIRMS', active: true, lastUpdate: 'Updated 15 min ago' },
          { name: 'DSS Attribution', active: true, lastUpdate: 'Updated 1 hour ago' },
          { name: 'Meteorological', active: true, lastUpdate: 'Updated 30 min ago' },
        ]}
      />
    </div>
  )
}
